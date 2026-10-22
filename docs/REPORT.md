# Project 1 report — مِشراك (CompatibilityMatch AI)

**Course:** AI Product Development and Monitoring  
**Product:** مِشراك — منصة توافق الشركات واكتشاف فرص الشراكة
**Date:** 22 October 2026

## 1. Problem and users

Saudi corporate strategy and finance teams need an early way to compare potential partners, investors, and joint ventures. Their work continues after approval: teams need to compare agreed objectives with actual performance. Public company disclosures generally do not expose private partnership KPIs.

## 2. Product

The Flask MVP supports deterministic company comparison for strategic partnerships and joint ventures, smart discovery from a local catalogue, a post-decision KPI monitor, and a separate technical system monitor. Role-based access supports regular users and administrators. Its user journey is Discover → Analyze → Evaluate → Decide → Monitor → Improve.

## 3. Data and provenance

- The database contains **27 actual Saudi Exchange Main Market listed issuers/securities**: 4 telecommunications, 7 energy/utilities/oil-services, 8 petrochemical, and 8 banking.
- Names and trading symbols are referenced to the [Saudi Exchange Issuer Directory](https://www.saudiexchange.sa/wps/portal/saudiexchange/trading/participants-directory/issuer-directory?locale=en). The app links this source from the company register.
- Short activity summaries and sector groupings are curated for the MVP. There is no live exchange synchronization.
- No company financial statements or current market valuation are fabricated. Financial analysis criteria are unavailable until a verified source and fiscal period are imported.
- One explicitly simulated stc–Al Rajhi Bank example has six months of fictional KPI values. It does not represent an actual relationship between those issuers. Its 650,000 SAR actual against a 1,000,000 SAR target demonstrates 65% achievement.

## 4. AI and development tools

Python, Flask, SQLAlchemy, SQLite, Jinja2, HTML/CSS/JavaScript, Chart.js, pytest, and Cursor-assisted vibe coding. If configured, an OpenAI-compatible LLM API creates structured Arabic explanations from supplied company and score data. Without credentials, deterministic rules produce labeled Demo Mode text. The deterministic Python scoring engine always owns numeric results.

AI-assisted work included initial scaffolding, templates, and documentation. Product requirements, company sourcing policy, deterministic formulas, data labels, and scenario values were checked and corrected in the implementation. Live LLM generation was not evaluated without an API key.

## 5. Scoring and evaluation

Two documented weight sets cover partnership and joint venture. Version `cm-score-v2` normalizes Arabic and English activity descriptions, extracts capabilities with a reusable taxonomy, and scores capability complementarities, text overlap, industry relationships, operational fit, and risks. Financial capacity is scored only from verified, non-synthetic financial rows. Missing criteria are omitted from the weighted average, lowering evidence coverage. Identical available evidence can produce genuine ties; no score is randomized or adjusted by company name or symbol. These heuristic scores are not validated empirical predictions.

Automated tests cover scoring, absent financials, all 702 ordered pairs across the 27-company catalogue for both supported relationship types, every company as a discovery starting point, ranking/comparison consistency, new-company eligibility, KPI direction, alerts, delayed milestones, monitoring events, Demo Mode, and API timeout simulation. Human factual support review template: `docs/AI_EVALUATION.md`.

**Executed 22 October 2026:** `pytest -q -p no:cacheprovider` → **26 passed**. Existing SQLAlchemy deprecation warnings remain and do not fail the suite. Automated tests validate deterministic scoring and API handling; they do not establish real-world predictive accuracy. No live Gemini benchmark or human factual-claim review is claimed.

## 6. Business monitoring

Users create a relationship record, objectives, targets, milestones, and actual measurements. Higher-is-better, lower-is-better, and range KPIs are evaluated separately. Alerts report the measured deviation and ask management to investigate; they do not infer a cause. Manual entry and CSV import are available. The simulated relationship provides a safe presentation example.

For equity-investment records, ROI is calculated only when a positive cost basis and a recorded current investment value exist. Entered dividends and realized exit proceeds are included; otherwise the dashboard says which inputs are missing.

## 7. Technical monitoring

Application requests and validation errors are written to `technical_monitoring_events`; the System Monitoring Dashboard aggregates persisted events, latency, errors, AI failures, tokens/cost when available, KPI failures, and data freshness. Startup does not insert fake system telemetry. Simulation controls create explicit test events.

## 8. Architecture and diagrams

Single-process Flask app and SQLite database. Business records and technical telemetry use separate models, pages, and calculations. See `docs/ARCHITECTURE.md` and Mermaid diagrams in `docs/DIAGRAMS.md`.

## 9. Limitations

- No automatic Tadawul feed, price feed, or public-filings synchronization.
- No financial ratios or investment valuation until official financial data is loaded.
- Heuristic compatibility scores require domain validation and human review. On the current catalogue snapshot, among 351 unordered company pairs the partnership scorecard yielded 104 distinct rounded scores, while the joint-venture scorecard yielded 105. Repeated summaries still create genuine ties.
- The taxonomy and compatibility rules are heuristic and need review by subject-matter experts.
- Company activity summaries are concise curated records rather than complete official filings.
- The system still lacks automatic issuer-data synchronization and verified financial statements.
- LLM factual quality requires human review and a configured API key.

Future work: validated financial imports, stronger issuer-specific sources, an audited review dataset, and tested decision thresholds.
