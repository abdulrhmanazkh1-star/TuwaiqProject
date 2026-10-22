"""LLM integration with a clearly labeled deterministic Demo Mode."""

from __future__ import annotations

import json
import random
import re
import time
from flask import current_app
import requests


def llm_configured() -> bool:
    return bool(current_app.config.get("LLM_API_KEY"))


def analyze_with_ai(company_a, company_b, analysis_type: str, score_payload: dict, simulate_timeout=False):
    if simulate_timeout:
        raise TimeoutError("Simulated AI API timeout")
    if not llm_configured():
        return _demo_narrative(company_a, company_b, analysis_type, score_payload), "demo_rules", 0, 0
    system = (
        "You are a Saudi business-partnership analyst. Use ONLY supplied facts. "
        "Never invent financial numbers. Distinguish facts from interpretation. "
        "Return valid JSON with keys: opportunities (list of strings), risks (list), "
        "collaborations (list), evidence_summary (string), caveats (list). Arabic language."
    )
    user = json.dumps(
        {
            "analysis_type": analysis_type,
            "company_a": _company_fact_card(company_a),
            "company_b": _company_fact_card(company_b) if company_b else None,
            "deterministic_scores": score_payload,
            "rules": [
                "Do not recommend buying shares from compatibility alone.",
                "Do not promise returns.",
                "If a field is missing, say it is unavailable.",
            ],
        },
        ensure_ascii=False,
    )
    payload = {
        "model": current_app.config["LLM_MODEL"],
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
    }
    body = _post_chat_completion(payload)
    content = body["choices"][0]["message"]["content"]
    usage = body.get("usage") or {}
    parsed = _parse_json(content)
    return parsed, "llm", int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0)


def _post_chat_completion(payload):
    """Retry transient Gemini/API failures with bounded exponential backoff."""
    headers = {
        "Authorization": f"Bearer {current_app.config['LLM_API_KEY']}",
        "Content-Type": "application/json",
    }
    url = f"{current_app.config['LLM_BASE_URL']}/chat/completions"
    attempts = max(1, int(current_app.config.get("LLM_RETRY_ATTEMPTS", 3)))
    retryable_statuses = {408, 429, 500, 502, 503, 504}

    for attempt in range(attempts):
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=current_app.config.get("LLM_TIMEOUT_SECONDS", 25),
            )
        except (requests.Timeout, requests.ConnectionError):
            if attempt + 1 >= attempts:
                raise
            time.sleep(min(2**attempt + random.uniform(0, 0.25), 8))
            continue

        if response.status_code in retryable_statuses and attempt + 1 < attempts:
            retry_after = response.headers.get("Retry-After")
            try:
                delay = min(max(float(retry_after), 0), 8) if retry_after else 2**attempt
            except (TypeError, ValueError):
                delay = 2**attempt
            time.sleep(delay + random.uniform(0, 0.25))
            continue

        response.raise_for_status()
        return response.json()

    raise RuntimeError("تعذر إكمال طلب Gemini بعد محاولات الإعادة")


def _company_fact_card(company):
    fins = [
        {
            "year": f.period_year,
            "revenue": f.revenue,
            "net_income": f.net_income,
            "total_assets": f.total_assets,
            "total_liabilities": f.total_liabilities,
            "is_synthetic": f.is_synthetic,
        }
        for f in sorted(company.financials, key=lambda x: x.period_year)
    ]
    return {
        "name": company.official_name,
        "symbol": company.symbol,
        "sector": company.sector,
        "description": company.description,
        "products_services": company.products_services,
        "is_synthetic": company.is_synthetic,
        "financials": fins,
        "sources": [{"title": s.title, "url": s.url} for s in company.sources],
    }


def _parse_json(content: str) -> dict:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.S)
        if not match:
            raise ValueError("Malformed AI JSON")
        return json.loads(match.group(0))


def _demo_narrative(company_a, company_b, analysis_type, score_payload):
    overall = score_payload.get("overall_score")
    limitations = score_payload.get("limitations") or []
    b_name = company_b.official_name if company_b else "—"
    opportunities = score_payload.get("strengths") or [
        f"لم تظهر قدرات متكاملة محددة بين {company_a.official_name} و{b_name} في البيانات المسجلة."
    ]
    risks = score_payload.get("risks") or ["لا تكفي البيانات الحالية لتحديد مخاطر العلاقة."]
    return {
        "opportunities": opportunities,
        "risks": risks,
        "collaborations": [
            f"نوع العلاقة المقترحة للدرس: {analysis_type} بدرجة إجمالية {overall} (صيغة {score_payload.get('scoring_version')})."
        ],
        "evidence_summary": f"تم اشتقاق الشرح من وصف الأنشطة والقدرات المسجلة. تغطية المعلومات المستخدمة {round((score_payload.get('evidence_coverage') or 0) * 100)}٪. النص حتمي ولا يمثل استدلال نموذج لغوي حي.",
        "caveats": limitations,
        "demo_mode": True,
        "facts_vs_interpretation": {
            "facts": ["الأسماء، القطاعات، والأرقام المالية المخزّنة في قاعدة البيانات المحلية."],
            "interpretation": ["فرص التعاون والمخاطر السردية في وضع التجربة."],
        },
    }
