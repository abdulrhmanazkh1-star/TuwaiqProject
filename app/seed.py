"""Seed the verified-listed-company catalogue."""

from sqlalchemy import or_

from app.models import (
    AIEvaluationResult,
    Analysis,
    BusinessAlert,
    BusinessRelationship,
    Company,
    CompanyFinancial,
    CompanySource,
    CompatibilityScore,
    KPIActual,
    KPITarget,
    Milestone,
    Recommendation,
    RelationshipObjective,
    TechnicalMonitoringEvent,
    db,
)

EXCHANGE_DIRECTORY = "https://www.saudiexchange.sa/wps/portal/saudiexchange/trading/participants-directory/issuer-directory?locale=en"

# Issuer names and symbols are listed on the Saudi Exchange Main Market.
# No financial figures are seeded: reports must be imported from official filings.
COMPANIES = [
    ("7010", "شركة الاتصالات السعودية", "Saudi Telecom Company (stc)", "اتصالات", "اتصالات متكاملة", "تشغيل شبكات الاتصالات وتقديم خدمات الهاتف والإنترنت وحلول الأعمال والاتصالات الرقمية.", "اتصالات ثابتة ومتنقلة، إنترنت، بيانات، خدمات رقمية للأعمال"),
    ("7020", "شركة اتحاد اتصالات", "Etihad Etisalat Company (Mobily)", "اتصالات", "اتصالات متكاملة", "مشغل اتصالات سعودي يقدم خدمات الهاتف المتنقل والثابت والإنترنت وحلول قطاع الأعمال.", "اتصالات متنقلة وثابتة، إنترنت، بيانات، حلول أعمال"),
    ("7030", "شركة الاتصالات المتنقلة السعودية", "Mobile Telecommunications Company Saudi Arabia (Zain KSA)", "اتصالات", "اتصالات متكاملة", "مشغل اتصالات سعودي يقدم خدمات الهاتف المتنقل والإنترنت والحلول الرقمية.", "اتصالات متنقلة، إنترنت، خدمات رقمية وحلول أعمال"),
    ("7202", "الشركة العربية لخدمات الإنترنت والاتصالات", "Arabian Internet and Communications Services Company (solutions by stc)", "اتصالات", "خدمات تقنية واتصالات", "شركة مدرجة تقدم خدمات تقنية المعلومات والاتصالات والخدمات الرقمية للمنشآت.", "خدمات تقنية المعلومات، الاتصالات، الأمن السيبراني، الخدمات الرقمية"),
    ("2222", "شركة الزيت العربية السعودية", "Saudi Arabian Oil Company (Saudi Aramco)", "طاقة", "النفط والغاز", "شركة طاقة متكاملة تعمل في استكشاف وإنتاج النفط والغاز والتكرير والبتروكيماويات.", "النفط والغاز، التكرير، المنتجات الكيميائية والطاقة"),
    ("5110", "الشركة السعودية للكهرباء", "Saudi Electricity Company", "طاقة", "مرافق كهربائية", "شركة مرافق كهربائية تعمل في توليد الكهرباء ونقلها وتوزيعها داخل المملكة.", "توليد الكهرباء، نقلها، توزيعها وخدمات الطاقة"),
    ("2082", "شركة أكوا باور", "ACWA Power Company", "طاقة", "مرافق وطاقة متجددة", "شركة تعمل في تطوير وتشغيل محطات توليد الكهرباء وتحلية المياه ومشروعات الطاقة المتجددة.", "توليد الكهرباء، الطاقة المتجددة، تحلية المياه"),
    ("2381", "شركة الحفر العربية", "Arabian Drilling Company", "طاقة", "حفر آبار النفط والغاز", "شركة تقدم خدمات حفر الآبار البرية والبحرية لقطاع النفط والغاز.", "منصات الحفر البرية والبحرية، خدمات حفر الآبار"),
    ("2382", "شركة أديس القابضة", "ADES Holding Company", "طاقة", "حفر آبار النفط والغاز", "شركة تقدم خدمات الحفر البري والبحري لقطاع النفط والغاز.", "حفر بري وبحري، خدمات آبار النفط والغاز"),
    ("2380", "شركة رابغ للتكرير والبتروكيماويات", "Rabigh Refining and Petrochemical Company (Petro Rabigh)", "طاقة", "تكرير وبتروكيماويات", "شركة مجمع متكامل للتكرير وإنتاج البتروكيماويات في مدينة رابغ.", "تكرير النفط، المنتجات البتروكيماوية"),
    ("2223", "شركة أرامكو السعودية لزيوت الأساس", "Luberef (Saudi Aramco Base Oil Company)", "طاقة", "زيوت الأساس", "شركة متخصصة في إنتاج زيوت الأساس والمنتجات المرتبطة بها.", "زيوت الأساس، زيوت التشحيم والمنتجات المرتبطة"),
    ("2010", "الشركة السعودية للصناعات الأساسية", "Saudi Basic Industries Corporation (SABIC)", "بتروكيماويات", "كيماويات متنوعة", "شركة صناعات كيميائية ومواد تعمل في إنتاج الكيماويات والبوليمرات والمواد المتخصصة.", "كيماويات، بوليمرات، مواد متخصصة"),
    ("2020", "شركة الأسمدة العربية السعودية", "SABIC Agri-Nutrients Company", "بتروكيماويات", "أسمدة وكيماويات زراعية", "شركة تنتج الأسمدة والمنتجات الكيميائية الزراعية والمنتجات المرتبطة بها.", "أسمدة، أمونيا، يوريا ومنتجات زراعية كيميائية"),
    ("2060", "شركة التصنيع الوطنية", "National Industrialization Company (Tasnee)", "بتروكيماويات", "بتروكيماويات وصناعات", "شركة صناعية سعودية تعمل في البتروكيماويات والكيماويات ومنتجات صناعية أخرى.", "بتروكيماويات، كيماويات، منتجات صناعية"),
    ("2310", "شركة الصحراء العالمية للبتروكيماويات", "Sahara International Petrochemical Company (Sipchem)", "بتروكيماويات", "كيماويات وبتروكيماويات", "شركة تعمل في إنتاج وتسويق منتجات البتروكيماويات والكيماويات.", "ميثانول، كيماويات، منتجات بتروكيماوية"),
    ("2290", "شركة ينبع الوطنية للبتروكيماويات", "Yanbu National Petrochemical Company (Yansab)", "بتروكيماويات", "بتروكيماويات", "شركة صناعية تنتج مجموعة من المنتجات البتروكيماوية في ينبع الصناعية.", "إيثيلين، بولي إيثيلين، جلايكول ومنتجات بتروكيماوية"),
    ("2350", "شركة كيان السعودية للبتروكيماويات", "Saudi Kayan Petrochemical Company", "بتروكيماويات", "بتروكيماويات", "شركة بتروكيماويات تنتج مواد كيميائية وبوليمرات ومنتجات صناعية.", "بتروكيماويات، بوليمرات، منتجات كيميائية"),
    ("2330", "شركة المتقدمة للبتروكيماويات", "Advanced Petrochemical Company", "بتروكيماويات", "بتروكيماويات", "شركة صناعية متخصصة في إنتاج البولي بروبيلين ومنتجات بتروكيماوية مرتبطة.", "بولي بروبيلين ومنتجات بتروكيماوية"),
    ("2001", "شركة كيمائيات الميثانول", "Methanol Chemicals Company (Chemanol)", "بتروكيماويات", "كيماويات أساسية", "شركة تنتج الميثانول ومشتقاته ومنتجات كيميائية صناعية.", "ميثانول، مشتقات الميثانول، كيماويات صناعية"),
    ("1010", "بنك الرياض", "Riyad Bank", "مصارف", "مصرف تجاري", "بنك سعودي مدرج يقدم خدمات مصرفية للأفراد والشركات.", "خدمات مصرفية للأفراد والشركات، تمويل، خدمات استثمارية"),
    ("1020", "بنك الجزيرة", "Bank Aljazira", "مصارف", "مصرف تجاري", "بنك سعودي مدرج يقدم خدمات مصرفية وتمويلية للأفراد والشركات.", "خدمات مصرفية، تمويل، خدمات استثمارية"),
    ("1030", "البنك السعودي للاستثمار", "The Saudi Investment Bank", "مصارف", "مصرف تجاري", "بنك سعودي مدرج يقدم خدمات مصرفية للأفراد والشركات والمؤسسات.", "خدمات مصرفية، تمويل، خدمات مؤسسات"),
    ("1050", "البنك السعودي الفرنسي", "Banque Saudi Fransi", "مصارف", "مصرف تجاري", "بنك سعودي مدرج يقدم منتجات مصرفية وتمويلية وخدمات استثمارية.", "خدمات مصرفية، تمويل، خدمات استثمارية"),
    ("1060", "البنك السعودي الأول", "Saudi Awwal Bank (SAB)", "مصارف", "مصرف تجاري", "بنك سعودي مدرج يقدم الخدمات المصرفية للأفراد والمنشآت والمؤسسات.", "خدمات مصرفية، تمويل، خدمات للشركات"),
    ("1080", "البنك العربي الوطني", "Arab National Bank", "مصارف", "مصرف تجاري", "بنك سعودي مدرج يقدم خدمات مصرفية للأفراد والشركات والمؤسسات.", "خدمات مصرفية، تمويل، خدمات استثمارية"),
    ("1120", "مصرف الراجحي", "Al Rajhi Bank", "مصارف", "مصرف إسلامي", "مصرف سعودي مدرج يقدم خدمات مصرفية وتمويلية متوافقة مع أحكام الشريعة.", "خدمات مصرفية وتمويلية، للأفراد والشركات"),
    ("1140", "بنك البلاد", "Bank Albilad", "مصارف", "مصرف إسلامي", "مصرف سعودي مدرج يقدم خدمات مصرفية وتمويلية متوافقة مع أحكام الشريعة.", "خدمات مصرفية وتمويلية، للأفراد والشركات"),
]


def _clear_old_demo_catalogue():
    """One-time migration from the original all-fictional seed database."""
    demo_ids = [row[0] for row in db.session.query(Company.id).filter(Company.symbol.like("DEMO.%")).all()]
    if not demo_ids:
        return
    rel_ids = [r.id for r in BusinessRelationship.query.filter(
        or_(BusinessRelationship.company_a_id.in_(demo_ids), BusinessRelationship.company_b_id.in_(demo_ids))
    ).all()]
    analysis_ids = [a.id for a in Analysis.query.filter(
        or_(Analysis.company_a_id.in_(demo_ids), Analysis.company_b_id.in_(demo_ids))
    ).all()]
    target_ids = [row[0] for row in db.session.query(KPITarget.id).filter(KPITarget.relationship_id.in_(rel_ids)).all()] if rel_ids else []
    if target_ids:
        KPIActual.query.filter(KPIActual.target_id.in_(target_ids)).delete(synchronize_session=False)
    if rel_ids:
        BusinessAlert.query.filter(BusinessAlert.relationship_id.in_(rel_ids)).delete(synchronize_session=False)
        RelationshipObjective.query.filter(RelationshipObjective.relationship_id.in_(rel_ids)).delete(synchronize_session=False)
        Milestone.query.filter(Milestone.relationship_id.in_(rel_ids)).delete(synchronize_session=False)
        KPITarget.query.filter(KPITarget.relationship_id.in_(rel_ids)).delete(synchronize_session=False)
        BusinessRelationship.query.filter(BusinessRelationship.id.in_(rel_ids)).delete(synchronize_session=False)
    if analysis_ids:
        AIEvaluationResult.query.filter(AIEvaluationResult.analysis_id.in_(analysis_ids)).delete(synchronize_session=False)
        CompatibilityScore.query.filter(CompatibilityScore.analysis_id.in_(analysis_ids)).delete(synchronize_session=False)
        Recommendation.query.filter(Recommendation.analysis_id.in_(analysis_ids)).delete(synchronize_session=False)
        Analysis.query.filter(Analysis.id.in_(analysis_ids)).delete(synchronize_session=False)
    CompanyFinancial.query.filter(CompanyFinancial.company_id.in_(demo_ids)).delete(synchronize_session=False)
    CompanySource.query.filter(CompanySource.company_id.in_(demo_ids)).delete(synchronize_session=False)
    Company.query.filter(Company.id.in_(demo_ids)).delete(synchronize_session=False)
    # Remove only seeded demo telemetry, preserving events recorded by the user.
    TechnicalMonitoringEvent.query.filter_by(details="seed-demo-event").delete(synchronize_session=False)
    db.session.commit()


def seed_if_empty():
    _clear_old_demo_catalogue()
    for symbol, name_ar, name_en, sector, subsector, description, products in COMPANIES:
        company = Company.query.filter_by(symbol=symbol).first()
        if company is None:
            company = Company(
                identifier=f"TADAWUL-{symbol}",
                official_name=name_ar,
                official_name_en=name_en,
                symbol=symbol,
                sector=sector,
                subsector=subsector,
                description=description,
                products_services=products,
                is_synthetic=False,
                source_url=EXCHANGE_DIRECTORY,
                data_publication_date=None,
            )
            db.session.add(company)
            db.session.flush()
            db.session.add(CompanySource(
                company_id=company.id,
                title="دليل المُصدرين — تداول السعودية",
                url=EXCHANGE_DIRECTORY,
                published_at=None,
                notes="مرجع لإثبات وجود المصدر/الشركة المدرجة ورمزها. وصف الأنشطة مختصر للتعريف؛ البيانات المالية غير مستوردة.",
            ))
        else:
            # Refresh the curated issuer identity while preserving user-created records.
            company.identifier = f"TADAWUL-{symbol}"
            company.official_name = name_ar
            company.official_name_en = name_en
            company.sector = sector
            company.subsector = subsector
            company.description = description
            company.products_services = products
            company.is_synthetic = False
            company.source_url = EXCHANGE_DIRECTORY
            company.data_publication_date = None
            CompanyFinancial.query.filter_by(company_id=company.id).delete(synchronize_session=False)
            if not CompanySource.query.filter_by(company_id=company.id).first():
                db.session.add(CompanySource(company_id=company.id, title="دليل المُصدرين — تداول السعودية", url=EXCHANGE_DIRECTORY, published_at=None, notes="البيانات المالية غير مستوردة."))
    db.session.commit()
