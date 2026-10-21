# Architecture and data provenance

CompatibilityMatch AI runs as one Flask application with SQLAlchemy and SQLite.

## Components

- **UI:** Arabic RTL Jinja2 pages with Chart.js.
- **HTTP:** routes in `app/views.py`.
- **Scoring:** deterministic formulas and documented weights in `app/scoring.py` (`cm-score-v1`).
- **AI narrative:** `app/ai_engine.py`, OpenAI-compatible API or labeled deterministic Demo Mode.
- **Business KPI calculations:** `app/kpis.py`.
- **Technical telemetry:** `app/monitoring.py` writes application events and calculates dashboard metrics.
- **Persistence:** relational SQLAlchemy models in `app/models.py`.

## Company catalogue

The seed contains 27 companies and securities on the Saudi Exchange Main Market: 4 telecommunications, 7 energy/utilities/oil services, 8 petrochemical, and 8 banking issuers. Official exchange issuer directory: [Saudi Exchange Issuer Directory](https://www.saudiexchange.sa/wps/portal/saudiexchange/trading/participants-directory/issuer-directory?locale=en). Example exchange company profiles: [stc (7010)](https://www.saudiexchange.sa/wps/portal/saudiexchange/hidden/company-profile-main/?companySymbol=7010) and [Saudi Aramco (2222)](https://www.saudiexchange.sa/wps/portal/saudiexchange/hidden/company-profile-main/?companySymbol=2222).

Names, symbols, and listed status are sourced from the exchange directory. Sector labels and short Arabic activity summaries are curated for this MVP. Rows use `is_synthetic=false` for issuer identity and carry the exchange directory URL. **No financial results, valuation, or share prices are seeded.** The app will show financial criteria as unavailable until a sourced annual filing is imported.

## Financial data import

Use the header-only template `data/companies_demo.csv`. Include an HTTPS official source URL and fiscal year for every financial row. `scripts/import_companies.py` matches known issuers by symbol and updates their financial year, or adds a new issuer row. Financial input rows marked synthetic are rejected. Do not mark any data non-synthetic without checking its official source and period.

Potential primary data sources include Saudi Exchange company announcements and issuer annual reports. The MVP does not synchronize these sources automatically.

## Scoring and limitations

The three analysis modes use separate weights. Missing financial values stay missing; weights are normalized over available criteria and confidence is reduced. LLM narratives cannot modify numeric scores. Sector/product scores are preliminary heuristics, not an empirical prediction model. No compatibility score alone constitutes a purchase recommendation.

## Relationships

The demo relationship uses two real issuer records but its existence, target values, KPI actuals, and milestones are fictional. It is explicitly marked `is_simulated=true` throughout the UI. Company announcements cannot establish private contract performance; production monitoring depends on user-entered updates or reports.
