# Project 1 report — مِشراك (CompatibilityMatch AI)

**Course:** AI Product Development and Monitoring  
**Product:** مِشراك — Saudi Business Partnership & Investment Intelligence
**Date:** 21 October 2026

## 1. Problem and users

Saudi corporate strategy and finance teams need an early way to compare potential partners, investors, and joint ventures. Their work continues after approval: teams need to compare agreed objectives with actual performance. Public company disclosures generally do not expose private partnership KPIs.

## 2. Product

The Flask MVP supports company comparison across three relationship types, smart discovery from a local catalogue, a post-decision KPI monitor, and a separate technical system monitor. Its user journey is Discover → Analyze → Evaluate → Decide → Monitor → Improve.

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

Three documented weight sets cover partnership, directional equity investment (A considers investing in B), and joint venture. Missing inputs are not fabricated; unavailable criteria are excluded and reduce confidence. Sector/product compatibility values are heuristic screening signals, not validated empirical predictions. The product does not advise buying shares or promise returns.

Automated tests cover scoring, absent financials, investment direction, discovery, KPI direction, alerts, delayed milestones, monitoring events, Demo Mode, and API timeout simulation. Human factual support review template: `docs/AI_EVALUATION.md`.

**Executed 21 October 2026:** `pytest -q` → **21 passed**. Pytest also reported SQLAlchemy deprecation warnings for legacy `Query.get()` and `datetime.utcnow()` calls; these do not fail the tests. Live LLM output was not evaluated because no API key is configured.

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
- Heuristic compatibility scores require domain validation and human review.
- No user authentication or role-based access; this is a local academic MVP.
- LLM factual quality requires human review and a configured API key.

Future work: validated financial imports, stronger issuer-specific sources, an audited review dataset, authenticated access, and tested decision thresholds.
