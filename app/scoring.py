"""Deterministic compatibility scoring. Versioned and documented.

Numerical scores come only from these formulas. The LLM may explain, not invent numbers.
"""

from __future__ import annotations

from datetime import date

SCORING_VERSION = "cm-score-v1"

PARTNERSHIP_WEIGHTS = {
    "business_complementarity": 0.25,
    "product_compatibility": 0.15,
    "partnership_opportunity": 0.15,
    "strategic_alignment": 0.15,
    "financial_capacity": 0.15,
    "operational_fit": 0.10,
    "risk_control": 0.05,
}

JV_WEIGHTS = {
    "resource_complementarity": 0.20,
    "operational_capability": 0.15,
    "business_opportunity": 0.15,
    "financial_capacity": 0.15,
    "project_feasibility": 0.15,
    "implementation_risk": 0.10,
    "mutual_benefit": 0.10,
}

COMPLEMENTARY_PAIRS = {
    frozenset({"طاقة", "بتروكيماويات"}): 90,
    frozenset({"اتصالات", "مصارف"}): 82,
    frozenset({"اتصالات", "طاقة"}): 72,
    frozenset({"بتروكيماويات", "مصارف"}): 64,
    frozenset({"مصارف", "طاقة"}): 66,
}

SAME_SECTOR_COMPLEMENT = 62
UNRELATED_COMPLEMENT = 55


def clamp(value: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, value))


def latest_financials(company, year=None):
    rows = sorted(company.financials, key=lambda f: f.period_year)
    if not rows:
        return None, None
    if year:
        current = next((r for r in rows if r.period_year == year), rows[-1])
    else:
        current = rows[-1]
    previous = next((r for r in reversed(rows[:-1]) if r.company_id == current.company_id), None)
    if len(rows) >= 2:
        previous = rows[-2]
    else:
        previous = None
    return current, previous


def complementarity_score(sector_a, sector_b):
    if sector_a == sector_b:
        return SAME_SECTOR_COMPLEMENT, 0.85, "الشركتان في القطاع نفسه؛ التشابه يسهل المقارنة، مع ضرورة فحص التداخل والمنافسة."
    pair = frozenset({sector_a, sector_b})
    mapped = COMPLEMENTARY_PAIRS.get(pair)
    if mapped:
        return mapped, 0.65, "تقدير أولي لعلاقة القطاعين؛ يلزم التحقق من فرص التعاون الفعلية."
    return UNRELATED_COMPLEMENT, 0.45, "لا توجد علاقة قطاعية محددة في قواعد التوافق؛ الدرجة افتراضية ومحافظة."


def product_overlap_score(products_a: str, products_b: str):
    tokens_a = {t.strip() for t in (products_a or "").replace("،", ",").split(",") if t.strip()}
    tokens_b = {t.strip() for t in (products_b or "").replace("،", ",").split(",") if t.strip()}
    if not tokens_a or not tokens_b:
        return None, 0.0, "وصف المنتجات غير مكتمل."
    overlap = tokens_a & tokens_b
    if overlap:
        return 45, 0.7, "يوجد تداخل منتجات؛ قد يظهر تعارض أو حاجة لتوزيع أدوار."
    return 78, 0.7, "المنتجات مختلفة، ما يدعم تكامل العرض دون تداخل مباشر."


def financial_capacity_score(fin_a, fin_b):
    if not fin_a or not fin_b:
        return None, 0.0, "بيانات مالية ناقصة لطرف أو للطرفين."
    revenues = [x for x in (fin_a.revenue, fin_b.revenue) if x is not None]
    if len(revenues) < 2:
        return None, 0.2, "الإيرادات غير مكتملة."
    scale = min(revenues) / max(revenues)
    # Similar scale is easier to partner with; extreme mismatch lowers capacity fit.
    score = clamp(50 + scale * 45)
    return score, 0.75, "المقارنة تعتمد على حجم الإيرادات النسبي للطرفين."


def criterion(name, score, weight, confidence, explanation, evidence=""):
    return {
        "criterion": name,
        "score": None if score is None else round(float(score), 2),
        "weight": weight,
        "confidence": round(float(confidence), 2),
        "explanation": explanation,
        "evidence": evidence,
    }


def weighted_overall(criteria: list[dict]) -> tuple[float | None, float]:
    usable = [c for c in criteria if c["score"] is not None]
    if not usable:
        return None, 0.0
    weight_sum = sum(c["weight"] for c in usable)
    if weight_sum == 0:
        return None, 0.0
    overall = sum(c["score"] * c["weight"] for c in usable) / weight_sum
    confidence = sum(c["confidence"] * c["weight"] for c in usable) / weight_sum
    # Penalize missing criteria
    coverage = weight_sum / sum(c["weight"] for c in criteria)
    confidence *= coverage
    return round(overall, 2), round(confidence, 2)


def score_partnership(company_a, company_b) -> dict:
    fin_a, prev_a = latest_financials(company_a)
    fin_b, prev_b = latest_financials(company_b)
    comp, conf, why = complementarity_score(company_a.sector, company_b.sector)
    prod, pconf, pwhy = product_overlap_score(company_a.products_services, company_b.products_services)
    cap, cconf, cwhy = financial_capacity_score(fin_a, fin_b)
    opportunity = None if comp is None else clamp(comp - 5)
    alignment = None if comp is None else clamp((comp + (prod or 60)) / 2)
    operational = 70 if company_a.sector != company_b.sector else 58
    risk = 40 if company_a.sector == company_b.sector else 78
    criteria = [
        criterion("business_complementarity", comp, PARTNERSHIP_WEIGHTS["business_complementarity"], conf, why),
        criterion("product_compatibility", prod, PARTNERSHIP_WEIGHTS["product_compatibility"], pconf, pwhy),
        criterion("partnership_opportunity", opportunity, PARTNERSHIP_WEIGHTS["partnership_opportunity"], conf, "فرصة الشراكة مشتقة من درجة التكامل القطاعية."),
        criterion("strategic_alignment", alignment, PARTNERSHIP_WEIGHTS["strategic_alignment"], 0.7, "المواءمة مزيج من التكامل وتوافق المنتجات."),
        criterion("financial_capacity", cap, PARTNERSHIP_WEIGHTS["financial_capacity"], cconf, cwhy),
        criterion("operational_fit", operational, PARTNERSHIP_WEIGHTS["operational_fit"], 0.6, "تقدير تشغيلي محافظ من اختلاف/تشابه القطاع."),
        criterion("risk_control", risk, PARTNERSHIP_WEIGHTS["risk_control"], 0.65, "ارتفاع المخاطر عند التنافس داخل نفس القطاع."),
    ]
    overall, confidence = weighted_overall(criteria)
    return {
        "analysis_type": "partnership",
        "scoring_version": SCORING_VERSION,
        "overall_score": overall,
        "confidence": confidence,
        "criteria": criteria,
        "limitations": _limitations(fin_a, fin_b, company_a, company_b),
    }


def score_joint_venture(company_a, company_b) -> dict:
    fin_a, _ = latest_financials(company_a)
    fin_b, _ = latest_financials(company_b)
    comp, conf, why = complementarity_score(company_a.sector, company_b.sector)
    cap, cconf, cwhy = financial_capacity_score(fin_a, fin_b)
    operational = 74 if company_a.sector != company_b.sector else 60
    opportunity = None if comp is None else clamp(comp - 3)
    feasibility = None
    if cap is not None and comp is not None:
        feasibility = round((cap + comp) / 2, 2)
    impl_risk = 75 if company_a.sector != company_b.sector else 52
    mutual = None if comp is None else clamp(comp - 8)
    criteria = [
        criterion("resource_complementarity", comp, JV_WEIGHTS["resource_complementarity"], conf, why),
        criterion("operational_capability", operational, JV_WEIGHTS["operational_capability"], 0.6, "تقدير تشغيلي من اختلاف الأنشطة."),
        criterion("business_opportunity", opportunity, JV_WEIGHTS["business_opportunity"], conf, "فرصة المشروع المشترك مشتقة من التكامل."),
        criterion("financial_capacity", cap, JV_WEIGHTS["financial_capacity"], cconf, cwhy),
        criterion("project_feasibility", feasibility, JV_WEIGHTS["project_feasibility"], 0.65 if feasibility else 0.0, "متوسط التكامل والقدرة المالية."),
        criterion("implementation_risk", impl_risk, JV_WEIGHTS["implementation_risk"], 0.55, "درجة أعلى تعني مخاطر تنفيذ أقل في هذا المعيار."),
        criterion("mutual_benefit", mutual, JV_WEIGHTS["mutual_benefit"], 0.6, "منفعة متبادلة تقديرية من التكامل، ليست ضمان عائد."),
    ]
    overall, confidence = weighted_overall(criteria)
    return {
        "analysis_type": "joint_venture",
        "scoring_version": SCORING_VERSION,
        "overall_score": overall,
        "confidence": confidence,
        "criteria": criteria,
        "limitations": _limitations(fin_a, fin_b, company_a, company_b),
    }


def analyze_pair(company_a, company_b, analysis_type: str) -> dict:
    if analysis_type == "joint_venture":
        return score_joint_venture(company_a, company_b)
    if analysis_type == "partnership":
        return score_partnership(company_a, company_b)
    raise ValueError("نوع التحليل غير مدعوم")


def _limitations(fin_a, fin_b, company_a, company_b):
    notes = []
    if company_a.is_synthetic or company_b.is_synthetic:
        notes.append("سجل الشركات تجريبي/مُحاكى ولا يمثل إفصاحاً رسمياً لتداول.")
    if not fin_a or not fin_b:
        notes.append("بيانات مالية ناقصة؛ انخفضت درجة الثقة وأُعيد توزيع الأوزان على المعايير المتوفرة.")
    notes.append("الدرجات قرار مساند فقط وليست استشارة استثمارية أو ضمان عوائد.")
    return notes


def kpi_achievement(target_value, actual_value, direction, range_min=None, range_max=None):
    if actual_value is None or target_value is None:
        return None, None, "Insufficient Data"
    if direction == "range":
        if range_min is None or range_max is None:
            return None, None, "Insufficient Data"
        if range_min <= actual_value <= range_max:
            mid = (range_min + range_max) / 2
            variance = actual_value - mid
            return 100.0, variance, "On Track"
        if actual_value < range_min:
            variance = actual_value - range_min
            pct = (actual_value / range_min) * 100 if range_min else None
            return pct, variance, _status_from_pct((pct or 0) / 100)
        variance = actual_value - range_max
        over = (range_max / actual_value) * 100 if actual_value else 0
        return over, variance, _status_from_pct(over / 100)
    if direction == "lower_better":
        if actual_value <= 0 and target_value <= 0:
            return 100.0, 0.0, "On Track"
        if actual_value <= 0:
            return None, actual_value - target_value, "Insufficient Data"
        pct = (target_value / actual_value) * 100
        variance = actual_value - target_value
        return round(pct, 2), round(variance, 2), _status_from_pct(pct / 100)
    # higher_better
    if target_value == 0:
        return None, actual_value, "Insufficient Data"
    pct = (actual_value / target_value) * 100
    variance = actual_value - target_value
    return round(pct, 2), round(variance, 2), _status_from_pct(pct / 100)


def _status_from_pct(ratio, on_track=0.90, needs=0.70):
    if ratio >= on_track:
        return "On Track"
    if ratio >= needs:
        return "Needs Attention"
    return "Off Track"


def milestone_status(due_date, completed_at, today=None):
    today = today or date.today()
    if completed_at:
        return "completed"
    if due_date < today:
        return "delayed"
    return "pending"
