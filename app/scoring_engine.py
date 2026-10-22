"""Deterministic company compatibility scoring, version cm-score-v2.

Scores use only stored company profiles and verified financial records. Sector
relations are a limited signal; profile terms and a reusable capability taxonomy
drive most company-specific differences. Equal evidence can produce real ties.
"""
from __future__ import annotations

import re
import unicodedata

SCORING_VERSION = "cm-score-v2"

PARTNERSHIP_WEIGHTS = {
    "business_complementarity": 0.20,
    "product_compatibility": 0.17,
    "partnership_opportunity": 0.15,
    "strategic_alignment": 0.14,
    "operational_fit": 0.10,
    "industry_relationship": 0.09,
    "risk_control": 0.10,
    "financial_capacity": 0.05,
}
JV_WEIGHTS = {
    "resource_complementarity": 0.20,
    "operational_capability": 0.15,
    "business_opportunity": 0.15,
    "strategic_alignment": 0.12,
    "industry_relationship": 0.10,
    "project_feasibility": 0.13,
    "implementation_risk": 0.10,
    "financial_capacity": 0.05,
}

STOPWORDS = {
    "في", "من", "على", "الى", "عن", "مع", "هذا", "هذه", "التي", "الذي", "كما", "بين",
    "شركة", "الشركة", "السعودية", "السعودي", "مدرجة", "تعمل", "يعمل", "تقدم", "يقدم",
    "تقديم", "خدمات", "خدمة", "منتجات", "المنتجات", "حلول", "قطاع", "قطاعات", "المملكة",
    "the", "and", "for", "with", "from", "company", "services", "service", "provides",
    "providing", "products", "solutions", "saudi", "arabia", "based", "in", "of", "to",
}

# Generic, extensible business capability groups; no company names or symbols.
CAPABILITY_TAXONOMY = {
    "connectivity": ("اتصالات", "اتصال", "شبكات", "شبكة", "انترنت", "بيانات", "هاتف", "telecom", "network", "internet", "mobile"),
    "digital_technology": ("رقمية", "رقمي", "تقنية", "برمجيات", "سحابية", "سحابي", "سيبراني", "digital", "software", "cloud", "technology", "cybersecurity"),
    "banking": ("مصرفية", "مصرف", "مصارف", "بنك", "البنوك", "banking", "bank", "مدفوعات", "payments"),
    "financing": ("تمويل", "تمويلية", "ائتمان", "قروض", "financing", "finance", "credit", "loans"),
    "investment": ("استثمار", "استثمارية", "استثمارات", "إدارة الأصول", "investment", "asset management"),
    "enterprise": ("المؤسسات", "منشآت", "أعمال", "الشركات", "enterprise", "corporate", "business", "b2b"),
    "energy_oil_gas": ("طاقة", "نفط", "غاز", "بترول", "oil", "gas", "energy", "petroleum"),
    "electricity": ("كهرباء", "توليد الكهرباء", "نقل الكهرباء", "power generation", "electricity", "power grid"),
    "renewables": ("متجددة", "شمسية", "رياح", "renewable", "solar", "wind"),
    "drilling": ("حفر", "آبار", "منصات الحفر", "drilling", "rigs", "well services"),
    "refining": ("تكرير", "المصافي", "مصفاة", "refining", "refinery"),
    "petrochemicals": ("بتروكيماويات", "بتروكيميائية", "كيماويات", "كيميائية", "chemicals", "petrochemical"),
    "polymers_materials": ("بوليمرات", "بوليمر", "بلاستيك", "مواد متخصصة", "polymers", "plastics", "materials"),
    "agriculture_fertilizers": ("أسمدة", "اسمدة", "أمونيا", "يوريا", "زراعية", "agriculture", "fertilizer", "ammonia", "urea"),
    "water": ("تحلية", "مياه", "water", "desalination"),
    "manufacturing": ("تصنيع", "صناعية", "صناعي", "مصانع", "industrial", "manufacturing", "production"),
    "retail_consumer": ("أفراد", "تجزئة", "استهلاكية", "مستهلكين", "retail", "consumer", "individuals"),
}
CAPABILITY_LABELS = {
    "connectivity": "الاتصال والشبكات", "digital_technology": "التقنية والخدمات الرقمية",
    "banking": "الخدمات المصرفية والمدفوعات", "financing": "التمويل", "investment": "الاستثمار",
    "enterprise": "خدمات المنشآت", "energy_oil_gas": "الطاقة والنفط والغاز",
    "electricity": "الكهرباء والمرافق", "renewables": "الطاقة المتجددة", "drilling": "الحفر والآبار",
    "refining": "التكرير", "petrochemicals": "الكيماويات والبتروكيماويات",
    "polymers_materials": "المواد والبوليمرات", "agriculture_fertilizers": "الأسمدة والزراعة",
    "water": "المياه والتحلية", "manufacturing": "التصنيع", "retail_consumer": "خدمات الأفراد والمستهلكين",
}
CAPABILITY_SYNERGIES = {
    frozenset(("connectivity", "banking")): 0.85,
    frozenset(("connectivity", "digital_technology")): 0.90,
    frozenset(("digital_technology", "banking")): 0.85,
    frozenset(("digital_technology", "enterprise")): 0.70,
    frozenset(("energy_oil_gas", "petrochemicals")): 0.90,
    frozenset(("energy_oil_gas", "electricity")): 0.75,
    frozenset(("energy_oil_gas", "drilling")): 0.90,
    frozenset(("energy_oil_gas", "renewables")): 0.65,
    frozenset(("renewables", "electricity")): 0.90,
    frozenset(("renewables", "water")): 0.70,
    frozenset(("refining", "petrochemicals")): 0.85,
    frozenset(("petrochemicals", "agriculture_fertilizers")): 0.80,
    frozenset(("petrochemicals", "polymers_materials")): 0.85,
    frozenset(("polymers_materials", "manufacturing")): 0.80,
    frozenset(("financing", "enterprise")): 0.60,
    frozenset(("banking", "enterprise")): 0.65,
}
SECTOR_VALUE_CHAINS = {
    frozenset(("طاقة", "بتروكيماويات")), frozenset(("طاقة", "مصارف")),
    frozenset(("اتصالات", "مصارف")), frozenset(("اتصالات", "طاقة")),
}


def clamp(value: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, value))


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", (value or "").lower())
    text = re.sub(r"[ً-ْـ]", "", text)
    return text.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه"}))


NORMALIZED_STOPWORDS = {normalize_text(word) for word in STOPWORDS}


def extract_tokens(value: str) -> set[str]:
    tokens = set()
    for raw in re.findall(r"[\u0621-\u064a\u0660-\u0669a-z0-9]+", normalize_text(value)):
        if raw in NORMALIZED_STOPWORDS:
            continue
        token = raw
        for prefix in ("وال", "بال", "لل", "ال", "و"):
            if token.startswith(prefix) and len(token) - len(prefix) >= 3:
                token = token[len(prefix):]
                break
        if len(token) > 4 and token.endswith("s"):
            token = token[:-1]
        if len(token) > 2 and token not in NORMALIZED_STOPWORDS:
            tokens.add(token)
    return tokens


def company_profile(company) -> str:
    return " ".join(str(getattr(company, key, "") or "") for key in (
        "official_name", "official_name_en", "sector", "subsector", "description", "products_services"
    ))


def company_activity_text(company) -> str:
    return " ".join(str(getattr(company, key, "") or "") for key in (
        "subsector", "description", "products_services"
    ))


def extract_capabilities(company) -> set[str]:
    text = normalize_text(company_activity_text(company))
    return {cap for cap, terms in CAPABILITY_TAXONOMY.items() if any(normalize_text(term) in text for term in terms)}


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def _pair_features(company_a, company_b):
    tokens_a = extract_tokens(company_activity_text(company_a))
    tokens_b = extract_tokens(company_activity_text(company_b))
    caps_a, caps_b = extract_capabilities(company_a), extract_capabilities(company_b)
    cap_union = caps_a | caps_b
    shared_cap_ratio = len(caps_a & caps_b) / len(cap_union) if cap_union else 0.0
    synergies = []
    for cap_a in caps_a:
        for cap_b in caps_b:
            value = CAPABILITY_SYNERGIES.get(frozenset((cap_a, cap_b)))
            if value:
                synergies.append((value, cap_a, cap_b))
    synergies.sort(key=lambda row: (-row[0], row[1], row[2]))
    denominator = max(1, min(len(caps_a), len(caps_b)))
    synergy_strength = min(1.0, sum(item[0] for item in synergies) / denominator)
    sector_a, sector_b = getattr(company_a, "sector", "") or "", getattr(company_b, "sector", "") or ""
    if sector_a and sector_a == sector_b:
        industry, industry_conf = 58.0, 0.80
        industry_text = "القطاع واحد؛ يوجد قرب في النشاط مع احتمال منافسة مباشرة."
    elif frozenset((sector_a, sector_b)) in SECTOR_VALUE_CHAINS:
        industry, industry_conf = 78.0, 0.65
        industry_text = "يوجد ارتباط عام بين القطاعين في سلسلة القيمة."
    elif caps_a and caps_b:
        industry, industry_conf = 55.0, 0.45
        industry_text = "لا توجد علاقة قطاعية محددة؛ لم يُعامل ذلك كعامل سلبي."
    else:
        industry, industry_conf = 50.0, 0.20
        industry_text = "بيانات القطاع أو النشاط لا تكفي لتحديد العلاقة."
    profile_pair_available = bool(tokens_a and tokens_b)
    return {
        "tokens_a": tokens_a, "tokens_b": tokens_b, "caps_a": caps_a, "caps_b": caps_b,
        "token_similarity": _jaccard(tokens_a, tokens_b), "profile_pair_available": profile_pair_available,
        "shared_cap_ratio": shared_cap_ratio,
        "synergies": synergies, "synergy_strength": synergy_strength,
        "industry": industry, "industry_conf": industry_conf, "industry_text": industry_text,
        "profiles_complete": all((
            getattr(company_a, "description", None), getattr(company_b, "description", None),
            getattr(company_a, "products_services", None), getattr(company_b, "products_services", None),
        )),
    }


def _synergy_labels(features) -> list[str]:
    return [f"{CAPABILITY_LABELS[left]} مع {CAPABILITY_LABELS[right]}" for _, left, right in features["synergies"]]


def _profile_overlap(features):
    if not features["profile_pair_available"]:
        return None, "وصف النشاط والمنتجات غير متاح للطرفين؛ لم يُعامل النقص كعامل سلبي.", ""
    shared = sorted(features["tokens_a"] & features["tokens_b"])
    score = clamp(55 + features["token_similarity"] * 45)
    evidence = "الكلمات المشتركة: " + ("، ".join(shared[:8]) if shared else "لا توجد كلمات مشتركة واضحة.")
    explanation = f"التشابه النصي بين أوصاف النشاط والمنتجات {features['token_similarity']:.0%}؛ قد يرفع التوافق التشغيلي ويزيد احتمال المنافسة."
    return score, explanation, evidence


def latest_financials(company, year=None):
    # Synthetic/demo financial rows are not evidence for a real issuer.
    if getattr(company, "is_synthetic", False):
        return None, None
    rows = sorted((f for f in getattr(company, "financials", []) if not getattr(f, "is_synthetic", True)), key=lambda f: f.period_year)
    if not rows:
        return None, None
    current = next((r for r in rows if r.period_year == year), rows[-1]) if year else rows[-1]
    previous = next((r for r in reversed(rows) if r.period_year < current.period_year), None)
    return current, previous


def financial_capacity_score(fin_a, fin_b):
    if not fin_a or not fin_b:
        return None, 0.0, "لا تتوفر بيانات مالية موثقة للطرفين."
    revenues = (getattr(fin_a, "revenue", None), getattr(fin_b, "revenue", None))
    if any(value is None or value <= 0 for value in revenues):
        return None, 0.0, "الإيرادات الموثقة غير مكتملة أو غير صالحة للمقارنة."
    scale_fit = min(revenues) / max(revenues)
    signals = [scale_fit]
    for financial in (fin_a, fin_b):
        assets = getattr(financial, "total_assets", None)
        liabilities = getattr(financial, "total_liabilities", None)
        if assets and liabilities is not None and assets > 0:
            signals.append(clamp(1 - liabilities / assets))
        ca, cl = getattr(financial, "current_assets", None), getattr(financial, "current_liabilities", None)
        if ca is not None and cl is not None and ca >= 0 and cl > 0:
            signals.append(clamp(min(ca / cl, 2) / 2))
    score = clamp(45 + (sum(signals) / len(signals)) * 55)
    return round(score, 2), 0.85, "حُسبت من الإيرادات والنسب المتاحة في القوائم الموثقة فقط."


def criterion(name, score, weight, confidence, explanation, evidence=""):
    return {
        "criterion": name, "score": None if score is None else round(float(score), 2),
        "weight": weight, "confidence": round(float(confidence), 2),
        "explanation": explanation, "evidence": evidence,
    }


def weighted_overall(criteria: list[dict]) -> tuple[float | None, float]:
    usable = [item for item in criteria if item["score"] is not None]
    if not usable:
        return None, 0.0
    available_weight = sum(item["weight"] for item in usable)
    total_weight = sum(item["weight"] for item in criteria)
    if not available_weight or not total_weight:
        return None, 0.0
    score = sum(item["score"] * item["weight"] for item in usable) / available_weight
    evidence_coverage = available_weight / total_weight
    confidence = sum(item["confidence"] * item["weight"] for item in usable) / available_weight * evidence_coverage
    return round(clamp(score), 2), round(clamp(confidence), 2)


def _build_common(a, b):
    features = _pair_features(a, b)
    text_fit, text_explanation, text_evidence = _profile_overlap(features)
    synergies = _synergy_labels(features)
    synergy_signal = features["synergy_strength"]
    text_similarity = features["token_similarity"]
    cap_overlap = features["shared_cap_ratio"]
    text_difference = (1 - text_similarity) if features["profile_pair_available"] else 0.5
    complementarity = clamp(42 + 48 * synergy_signal + 10 * text_difference) if features["caps_a"] and features["caps_b"] else None
    opportunity = clamp(40 + 50 * synergy_signal + 10 * (1 - cap_overlap)) if features["caps_a"] and features["caps_b"] else None
    alignment = clamp(42 + 28 * features["industry"] / 100 + 20 * text_difference + 10 * synergy_signal) if features["profile_pair_available"] else None
    operational = clamp(45 + 25 * cap_overlap + 20 * (text_similarity if features["profile_pair_available"] else 0) + 10 * synergy_signal) if features["profile_pair_available"] else None
    same_sector = bool(getattr(a, "sector", "") and getattr(a, "sector", "") == getattr(b, "sector", ""))
    risk_control = clamp(100 - (25 * same_sector + 35 * (text_similarity if features["profile_pair_available"] else 0) + 25 * cap_overlap - 15 * synergy_signal)) if getattr(a, "sector", None) or features["profile_pair_available"] else None
    cap_names_a = sorted(CAPABILITY_LABELS[c] for c in features["caps_a"])
    cap_names_b = sorted(CAPABILITY_LABELS[c] for c in features["caps_b"])
    strengths = [f"تكامل محتمل في: {label}" for label in synergies[:4]]
    if not strengths and cap_names_a and cap_names_b:
        strengths.append("لكل شركة قدرات مسجلة مختلفة: " + "، ".join((cap_names_a + cap_names_b)[:5]))
    risks = []
    if same_sector:
        risks.append("العمل في القطاع نفسه قد يعني منافسة مباشرة أو تداخل أدوار.")
    if text_similarity >= 0.25:
        risks.append("تشابه الأوصاف مرتفع نسبياً؛ يلزم التحقق من التداخل التجاري.")
    if not risks:
        risks.append("لم يُستدل على تعارض محدد من البيانات المتاحة؛ يلزم فحص السوق والعقود.")
    missing = []
    if not getattr(a, "description", None) or not getattr(b, "description", None):
        missing.append("وصف نشاط إحدى الشركتين ناقص.")
    if not getattr(a, "products_services", None) or not getattr(b, "products_services", None):
        missing.append("بيانات المنتجات أو الخدمات ناقصة.")
    if not getattr(a, "sources", None) or not getattr(b, "sources", None):
        missing.append("بعض بيانات النشاط لا تحتوي مرجع مصدر مباشر.")
    return features, text_fit, text_explanation, text_evidence, complementarity, opportunity, alignment, operational, risk_control, strengths, risks, missing


def _limitations(fin_a, fin_b, company_a, company_b, missing=None):
    notes = list(missing or [])
    if getattr(company_a, "is_synthetic", False) or getattr(company_b, "is_synthetic", False):
        notes.append("أحد سجلي الشركتين تجريبي ولا يمثل إفصاحاً رسمياً.")
    if not fin_a or not fin_b:
        notes.append("البيانات المالية الموثقة غير متاحة؛ لا تُعامل كإشارة سلبية وتُستبعد من الدرجة.")
    notes.append("النتيجة تقدير أولي من بيانات المنصة وليست توصية استثمارية أو ضماناً للنتائج.")
    return notes


def _coverage(criteria):
    total = sum(item["weight"] for item in criteria)
    available = sum(item["weight"] for item in criteria if item["score"] is not None)
    return round(available / total, 2) if total else 0.0


def _result(analysis_type, criteria, common, fin_a, fin_b, a, b):
    overall, confidence = weighted_overall(criteria)
    (_, _, _, _, _, _, _, _, _, strengths, risks, missing) = common
    missing = list(missing)
    if not fin_a or not fin_b:
        missing.append("البيانات المالية الموثقة للطرفين غير متاحة.")
    evidence_coverage = _coverage(criteria)
    if overall is None:
        recommendation = "المعلومات المتاحة لا تكفي لحساب توافق أولي موثوق."
    elif overall >= 75:
        recommendation = "توجد مؤشرات أولية واعدة تستحق مراجعة فرص التعاون والتحقق منها."
    elif overall >= 60:
        recommendation = "توجد نقاط تكامل محتملة؛ يلزم جمع معلومات تشغيلية ومالية إضافية."
    else:
        recommendation = "التوافق الظاهر محدود وفق البيانات الحالية؛ راجع المعايير والأدلة قبل الاستبعاد."
    return {
        "analysis_type": analysis_type, "scoring_version": SCORING_VERSION,
        "overall_score": overall, "confidence": confidence,
        "evidence_coverage": evidence_coverage, "criteria": criteria,
        "strengths": strengths, "risks": risks, "missing_information": missing,
        "recommendation": recommendation,
        "limitations": _limitations(fin_a, fin_b, a, b, missing),
    }


def score_partnership(company_a, company_b) -> dict:
    common = _build_common(company_a, company_b)
    features, product, product_why, product_evidence, complement, opportunity, alignment, operational, risk, strengths, risks, missing = common
    fin_a, _ = latest_financials(company_a)
    fin_b, _ = latest_financials(company_b)
    financial, financial_conf, financial_why = financial_capacity_score(fin_a, fin_b)
    sector_evidence = f"{getattr(company_a, 'sector', 'غير محدد')} ↔ {getattr(company_b, 'sector', 'غير محدد')}"
    synergies = _synergy_labels(features)
    synergy_evidence = "؛ ".join(synergies) if synergies else "لم تُكتشف علاقة تكامل ضمن التصنيف الحالي."
    criteria = [
        criterion("business_complementarity", complement, PARTNERSHIP_WEIGHTS["business_complementarity"], 0.65 if features["caps_a"] and features["caps_b"] else 0.25, "توافق الأنشطة مشتق من القدرات المتكاملة المسجلة والتشابه النصي.", synergy_evidence),
        criterion("product_compatibility", product, PARTNERSHIP_WEIGHTS["product_compatibility"], 0.65 if features["profiles_complete"] else 0.25, product_why, product_evidence),
        criterion("partnership_opportunity", opportunity, PARTNERSHIP_WEIGHTS["partnership_opportunity"], 0.55 if features["synergies"] else 0.3, "فرص أولية من أزواج القدرات التي قد تتكامل؛ تحتاج تحققاً تجارياً.", synergy_evidence),
        criterion("strategic_alignment", alignment, PARTNERSHIP_WEIGHTS["strategic_alignment"], 0.45, "مواءمة مبدئية من علاقة القطاع والتشابه والتكامل المسجل.", sector_evidence),
        criterion("operational_fit", operational, PARTNERSHIP_WEIGHTS["operational_fit"], 0.5, "تقارب تشغيلي نصي وقدرات مشتركة؛ لا تتوفر بيانات إجراءات داخلية.", product_evidence),
        criterion("industry_relationship", features["industry"], PARTNERSHIP_WEIGHTS["industry_relationship"], features["industry_conf"], features["industry_text"], sector_evidence),
        criterion("risk_control", risk, PARTNERSHIP_WEIGHTS["risk_control"], 0.5, "درجة أعلى تعني مؤشرات تعارض أقل؛ مبنية على القطاع وتشابه الأنشطة.", "؛ ".join(risks)),
        criterion("financial_capacity", financial, PARTNERSHIP_WEIGHTS["financial_capacity"], financial_conf, financial_why),
    ]
    return _result("partnership", criteria, common, fin_a, fin_b, company_a, company_b)


def score_joint_venture(company_a, company_b) -> dict:
    common = _build_common(company_a, company_b)
    features, product, product_why, product_evidence, complement, opportunity, alignment, operational, risk, strengths, risks, missing = common
    fin_a, _ = latest_financials(company_a)
    fin_b, _ = latest_financials(company_b)
    financial, financial_conf, financial_why = financial_capacity_score(fin_a, fin_b)
    feasibility = (financial * 0.55 + complement * 0.45) if financial is not None else None
    sector_evidence = f"{getattr(company_a, 'sector', 'غير محدد')} ↔ {getattr(company_b, 'sector', 'غير محدد')}"
    synergy_evidence = "؛ ".join(_synergy_labels(features)) or "لم تُكتشف علاقة تكامل ضمن التصنيف الحالي."
    criteria = [
        criterion("resource_complementarity", complement, JV_WEIGHTS["resource_complementarity"], 0.65 if features["caps_a"] and features["caps_b"] else 0.25, "تكامل الموارد الممكن استنتاجه من القدرات المسجلة.", synergy_evidence),
        criterion("operational_capability", operational, JV_WEIGHTS["operational_capability"], 0.5, "قدرة تشغيلية تقريبية من الأوصاف والقدرات؛ لا تتوفر بيانات موارد المشروع الفعلية.", product_evidence),
        criterion("business_opportunity", opportunity, JV_WEIGHTS["business_opportunity"], 0.55 if features["synergies"] else 0.3, "فرصة أولية مبنية على تكامل القدرات المحدد.", synergy_evidence),
        criterion("strategic_alignment", alignment, JV_WEIGHTS["strategic_alignment"], 0.45, "مواءمة مبدئية من علاقة القطاع والتشابه والتكامل المسجل.", sector_evidence),
        criterion("industry_relationship", features["industry"], JV_WEIGHTS["industry_relationship"], features["industry_conf"], features["industry_text"], sector_evidence),
        criterion("project_feasibility", feasibility, JV_WEIGHTS["project_feasibility"], 0.65 if feasibility is not None else 0, "تقدير مشروط بتوفر بيانات مالية موثقة وجدوى المشروع؛ لا تُفترض ميزانية أو عوائد." if feasibility is not None else "غير متاح: لم تتوفر بيانات مالية موثقة للطرفين."),
        criterion("implementation_risk", risk, JV_WEIGHTS["implementation_risk"], 0.5, "درجة أعلى تعني مخاطر تعارض أقل حسب تشابه الأوصاف والقطاعات.", "؛ ".join(risks)),
        criterion("financial_capacity", financial, JV_WEIGHTS["financial_capacity"], financial_conf, financial_why),
    ]
    return _result("joint_venture", criteria, common, fin_a, fin_b, company_a, company_b)


def analyze_pair(company_a, company_b, analysis_type: str) -> dict:
    if company_a is None or company_b is None or getattr(company_a, "id", None) == getattr(company_b, "id", object()):
        raise ValueError("اختر شركتين مختلفتين للتحليل")
    if analysis_type == "joint_venture":
        return score_joint_venture(company_a, company_b)
    if analysis_type == "partnership":
        return score_partnership(company_a, company_b)
    raise ValueError("نوع التحليل غير مدعوم")


def rank_candidates(company, candidates, analysis_type: str):
    """Rank every eligible candidate; ties are stable by company symbol/name."""
    ranked = []
    for candidate in candidates:
        if getattr(candidate, "id", None) == getattr(company, "id", object()):
            continue
        payload = analyze_pair(company, candidate, analysis_type)
        ranked.append((payload["overall_score"], payload["evidence_coverage"], candidate, payload))
    ranked.sort(key=lambda row: (-(row[0] if row[0] is not None else -1), -(row[1] or 0), getattr(row[2], "symbol", "") or getattr(row[2], "official_name", "")))
    return ranked
