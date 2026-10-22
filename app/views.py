from __future__ import annotations

import json
import time
from datetime import datetime

from flask import (
    Blueprint,
    Response,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy.exc import SQLAlchemyError

from app.ai_engine import analyze_with_ai, llm_configured
from app.auth import roles_required
from app.models import (
    Analysis,
    Company,
    CompatibilityScore,
    Recommendation,
    db,
)
from app.monitoring import dashboard_metrics, record_event
from app.scoring import SCORING_VERSION, analyze_pair, rank_candidates

bp = Blueprint("main", __name__)

ANALYSIS_LABELS = {
    "partnership": "شراكة استراتيجية",
    "equity_investment": "استثمار قائم",
    "joint_venture": "مشروع مشترك",
}

CRITERION_LABELS = {
    "business_complementarity": "تكامل الأنشطة التجارية",
    "product_compatibility": "توافق المنتجات والخدمات",
    "partnership_opportunity": "فرص التعاون",
    "strategic_alignment": "المواءمة الاستراتيجية",
    "financial_capacity": "القدرة المالية",
    "operational_fit": "التوافق التشغيلي",
    "risk_control": "إدارة المخاطر",
    "industry_relationship": "الارتباط بين القطاعات",
    "resource_complementarity": "تكامل الموارد",
    "operational_capability": "القدرات التشغيلية",
    "business_opportunity": "الفرصة التجارية",
    "project_feasibility": "جدوى المشروع",
    "implementation_risk": "مخاطر التنفيذ",
    "mutual_benefit": "المنفعة المتبادلة",
}

STATUS_LABELS = {
    "draft": "مسودة",
    "approved": "معتمدة",
    "signed": "موقّعة",
    "active": "نشطة",
    "completed": "مكتملة",
    "failed": "تعذّر إكمالها",
    "On Track": "على المسار الصحيح",
    "Needs Attention": "تحتاج إلى متابعة",
    "Off Track": "متأخرة عن الهدف",
    "Insufficient Data": "بيانات غير كافية",
    "pending": "قيد الانتظار",
    "delayed": "متأخرة عن موعدها",
}


def score_class(score):
    if score is None:
        return "score-low"
    if score >= 60:
        return "score-high"
    if score >= 40:
        return "score-mid"
    return "score-low"


def analysis_status_text(analysis):
    if analysis.status == "failed":
        return "تعذّر إكمال التحليل حالياً. تحقق من البيانات وحاول مرة أخرى لاحقاً."
    if analysis.mode == "demo_rules":
        return f"اكتمل التحليل باستخدام قواعد التقييم التجريبية خلال {analysis.latency_ms} ملي ثانية."
    if analysis.mode == "hybrid":
        return f"اكتمل التحليل بمساعدة الذكاء الاصطناعي خلال {analysis.latency_ms} ملي ثانية."
    return f"اكتمل التحليل خلال {analysis.latency_ms} ملي ثانية."


@bp.app_context_processor
def inject_globals():
    return {
        "llm_mode": "llm" if llm_configured() else "demo",
        "analysis_labels": ANALYSIS_LABELS,
        "criterion_labels": CRITERION_LABELS,
        "status_labels": STATUS_LABELS,
        "score_class": score_class,
        "analysis_status_text": analysis_status_text,
        "scoring_version": SCORING_VERSION,
    }


@bp.route("/")
def home():
    companies = Company.query.order_by(Company.sector, Company.official_name).all()
    metrics = dashboard_metrics() if g.logged_in_user.role == "admin" else None
    return render_template("home.html", companies=companies, metrics=metrics)


@bp.route("/compare", methods=["GET", "POST"])
def compare():
    companies = Company.query.order_by(Company.official_name).all()
    if request.method == "POST":
        a_id = request.form.get("company_a")
        b_id = request.form.get("company_b")
        analysis_type = request.form.get("analysis_type", "partnership")
        simulate = request.form.get("simulate")
        if analysis_type not in ("partnership", "joint_venture"):
            flash("نوع التحليل غير متاح. اختر شراكة استراتيجية أو مشروعاً مشتركاً.", "err")
            return redirect(url_for("main.compare"))
        return _run_comparison(a_id, b_id, analysis_type, simulate)
    return render_template("compare.html", companies=companies)


@bp.route("/analysis/<int:analysis_id>")
def analysis_detail(analysis_id):
    analysis = Analysis.query.get_or_404(analysis_id)
    if analysis.analysis_type == "equity_investment":
        abort(404)
    report = json.loads(analysis.report_json or "{}")
    return render_template("analysis.html", analysis=analysis, report=report)


@bp.route("/discover", methods=["GET", "POST"])
def discover():
    companies = Company.query.order_by(Company.official_name).all()
    if request.method == "POST":
        a_id = request.form.get("company_a")
        analysis_type = request.form.get("analysis_type", "partnership")
        if analysis_type not in ("partnership", "joint_venture"):
            flash("نوع التحليل غير متاح. اختر شراكة استراتيجية أو مشروعاً مشتركاً.", "err")
            return redirect(url_for("main.discover"))
        return _run_discovery(a_id, analysis_type)
    return render_template("discover.html", companies=companies)


@bp.route("/investment", methods=["GET", "POST"])
def removed_investment_analysis():
    flash("تحليل الاستثمار غير متاح حالياً. يمكنك مقارنة الشركات أو استكشاف فرص التعاون.", "ok")
    return redirect(url_for("main.compare"))


@bp.route("/system")
@roles_required("admin")
def system_monitor():
    metrics = dashboard_metrics()
    return render_template("system.html", metrics=metrics)


@bp.route("/system/simulate", methods=["POST"])
@roles_required("admin")
def simulate():
    kind = request.form.get("kind")
    if kind == "ai_timeout":
        companies = Company.query.limit(2).all()
        _run_comparison(str(companies[0].id), str(companies[1].id), "partnership", "timeout")
        flash("تم محاكاة انتهاء مهلة واجهة الذكاء الاصطناعي.", "ok")
        return redirect(url_for("main.system_monitor"))
    if kind == "missing_company":
        record_event("validation_failure", False, error_code="missing_company", details="simulated")
        flash("سُجّل فشل تحقق: شركة ناقصة.", "ok")
        return redirect(url_for("main.system_monitor"))
    if kind == "delayed_analysis":
        t0 = time.time()
        time.sleep(1.2)
        record_event("ai_analysis", True, latency_ms=int((time.time() - t0) * 1000), details="simulated delay")
        flash("سُجّل تحليل متأخر لأغراض المراقبة.", "ok")
        return redirect(url_for("main.system_monitor"))
    return redirect(url_for("main.system_monitor"))


@bp.route("/reports")
def reports():
    analyses = Analysis.query.filter(Analysis.analysis_type.in_(("partnership", "joint_venture"))).order_by(Analysis.created_at.desc()).limit(20).all()
    return render_template("reports.html", analyses=analyses)


@bp.route("/reports/analysis/<int:analysis_id>.json")
def analysis_json(analysis_id):
    analysis = Analysis.query.get_or_404(analysis_id)
    return Response(analysis.report_json or "{}", mimetype="application/json")


def _run_comparison(a_id, b_id, analysis_type, simulate=None):
    t0 = time.time()
    try:
        if not a_id or not b_id or a_id == b_id:
            record_event("validation_failure", False, error_code="invalid_pair", details="same or missing company")
            flash("اختر شركتين مختلفتين.", "err")
            return redirect(url_for("main.compare"))
        company_a = Company.query.get(int(a_id))
        company_b = Company.query.get(int(b_id))
        if not company_a or not company_b:
            record_event("validation_failure", False, error_code="missing_company", details=f"{a_id},{b_id}")
            flash("بيانات الشركة غير موجودة في السجل المحلي.", "err")
            return redirect(url_for("main.compare"))
        score_payload = analyze_pair(company_a, company_b, analysis_type)
        narrative, mode, tok_in, tok_out = analyze_with_ai(
            company_a, company_b, analysis_type, score_payload, simulate_timeout=(simulate == "timeout")
        )
        latency = int((time.time() - t0) * 1000)
        report = {
            "scores": score_payload,
            "narrative": narrative,
            "facts_only_financials": True,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }
        analysis = Analysis(
            company_a_id=company_a.id,
            company_b_id=company_b.id,
            analysis_type=analysis_type,
            direction="a_to_b",
            status="completed",
            scoring_version=SCORING_VERSION,
            mode=mode,
            latency_ms=latency,
            report_json=json.dumps(report, ensure_ascii=False),
        )
        db.session.add(analysis)
        db.session.flush()
        for c in score_payload["criteria"]:
            db.session.add(
                CompatibilityScore(
                    analysis_id=analysis.id,
                    criterion=c["criterion"],
                    score=c["score"],
                    weight=c["weight"],
                    confidence=c["confidence"],
                    explanation=c["explanation"],
                    evidence=c.get("evidence"),
                )
            )
        db.session.commit()
        record_event(
            "ai_analysis",
            True,
            latency_ms=latency,
            tokens_in=tok_in,
            tokens_out=tok_out,
            details=f"analysis_id={analysis.id};mode={mode}",
        )
        return redirect(url_for("main.analysis_detail", analysis_id=analysis.id))
    except Exception as exc:
        db.session.rollback()
        latency = int((time.time() - t0) * 1000)
        response_status = getattr(getattr(exc, "response", None), "status_code", None)
        if response_status in (429, 503):
            error_code = f"gemini_{response_status}"
            user_error = "خدمة Gemini مشغولة أو غير متاحة مؤقتاً. انتظر قليلًا ثم أعد التحليل."
        elif response_status in (401, 403):
            error_code = "gemini_auth"
            user_error = "تعذر التحقق من مفتاح Gemini. راجع المفتاح وإعدادات الخدمة."
        elif isinstance(exc, TimeoutError) or "timeout" in str(exc).lower():
            error_code = "timeout"
            user_error = "استغرق الاتصال بخدمة الذكاء الاصطناعي وقتاً طويلاً. أعد المحاولة بعد قليل."
        else:
            error_code = "ai_error"
            user_error = "تعذر إكمال التحليل بسبب مشكلة مؤقتة في خدمة الذكاء الاصطناعي. أعد المحاولة بعد قليل."
        failed = Analysis(
            company_a_id=int(a_id) if a_id else 1,
            company_b_id=int(b_id) if b_id else None,
            analysis_type=analysis_type,
            status="failed",
            scoring_version=SCORING_VERSION,
            mode="error",
            latency_ms=latency,
            error_message=str(exc)[:500],
            report_json="{}",
        )
        try:
            db.session.add(failed)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
        record_event("ai_analysis", False, latency_ms=latency, error_code=error_code, details=str(exc)[:400])
        flash(user_error, "err")
        return redirect(url_for("main.compare"))


def _run_discovery(a_id, analysis_type):
    t0 = time.time()
    company_a = Company.query.get(int(a_id)) if a_id else None
    if not company_a:
        record_event("validation_failure", False, error_code="missing_company", details="discovery")
        flash("اختر شركة من السجل المحلي.", "err")
        return redirect(url_for("main.discover"))
    candidates = Company.query.filter(Company.id != company_a.id).all()
    ranked = rank_candidates(company_a, candidates, analysis_type)
    top = ranked[:5]
    latency = int((time.time() - t0) * 1000)
    analysis = Analysis(
        company_a_id=company_a.id,
        company_b_id=None,
        analysis_type=analysis_type,
        status="completed",
        scoring_version=SCORING_VERSION,
        mode="demo_rules" if not llm_configured() else "hybrid",
        latency_ms=latency,
        report_json=json.dumps({"discovery": True, "count_ranked": len(ranked)}, ensure_ascii=False),
    )
    db.session.add(analysis)
    db.session.flush()
    recs = []
    for i, (score, coverage, cand, payload) in enumerate(top, start=1):
        why = payload["recommendation"] + " " + "؛ ".join(payload.get("strengths") or [])
        risks = "؛ ".join((payload.get("risks") or []) + (payload.get("missing_information") or []))
        rec = Recommendation(
            analysis_id=analysis.id,
            candidate_company_id=cand.id,
            rank=i,
            overall_score=score,
            confidence=payload["confidence"],
            why=why,
            risks=risks,
            limitations="الترتيب داخل السجل المحلي المُتحقق فقط، وليس كل شركات تداول.",
        )
        db.session.add(rec)
        recs.append((rec, cand, payload))
    db.session.commit()
    record_event("discovery", True, latency_ms=latency, details=f"analysis_id={analysis.id}")
    return render_template(
        "discover_results.html",
        company_a=company_a,
        analysis=analysis,
        ranked=recs,
        analysis_type=analysis_type,
    )
