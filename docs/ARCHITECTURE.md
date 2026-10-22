# Architecture and data provenance

CompatibilityMatch AI runs as one Flask application with SQLAlchemy and SQLite.

## Components

- **UI:** Arabic RTL Jinja2 pages with Chart.js.
- **HTTP:** routes in `app/views.py`.
- **Scoring:** deterministic formulas in `app/scoring_engine.py`, exposed through `app/scoring.py`, version `cm-score-v2`. A normalized Arabic/English activity profile and reusable capability taxonomy find overlaps and complementary capability pairs. The explicit industry-relation dimension carries 9–10% weight; profile and capability signals drive other dimensions. No company symbol/name offsets are used. Missing verified financials are excluded from the numeric average and reduce evidence coverage.
- **AI narrative:** `app/ai_engine.py`, OpenAI-compatible API or labeled deterministic Demo Mode.
- **Technical telemetry:** `app/monitoring.py` writes application events and calculates dashboard metrics.
- **Persistence:** relational SQLAlchemy models in `app/models.py`.

## Company catalogue

The seed contains 27 companies and securities on the Saudi Exchange Main Market: 4 telecommunications, 7 energy/utilities/oil services, 8 petrochemical, and 8 banking issuers. Official exchange issuer directory: [Saudi Exchange Issuer Directory](https://www.saudiexchange.sa/wps/portal/saudiexchange/trading/participants-directory/issuer-directory?locale=en). Example exchange company profiles: [stc (7010)](https://www.saudiexchange.sa/wps/portal/saudiexchange/hidden/company-profile-main/?companySymbol=7010) and [Saudi Aramco (2222)](https://www.saudiexchange.sa/wps/portal/saudiexchange/hidden/company-profile-main/?companySymbol=2222).

Names, symbols, and listed status are sourced from the exchange directory. Sector labels and short Arabic activity summaries are curated for this MVP. Rows use `is_synthetic=false` for issuer identity and carry the exchange directory URL. **No financial results, valuation, or share prices are seeded.** The app will show financial criteria as unavailable until a sourced annual filing is imported.

## Financial data import

Use the header-only template `data/companies_demo.csv`. Include an HTTPS official source URL and fiscal year for every financial row. `scripts/import_companies.py` matches known issuers by symbol and updates their financial year, or adds a new issuer row. Financial input rows marked synthetic are rejected. Do not mark any data non-synthetic without checking its official source and period.

Potential primary data sources include Saudi Exchange company announcements and issuer annual reports. The MVP does not synchronize these sources automatically.

## Scoring and limitations

Strategic partnership and joint venture each have a separate weight set in `app/scoring_engine.py`:

| Strategic partnership criterion | Weight |
| --- | ---: |
| Business complementarity | 20% |
| Product compatibility | 17% |
| Partnership opportunity | 15% |
| Strategic alignment | 14% |
| Operational fit | 10% |
| Industry relationship | 9% |
| Risk control | 10% |
| Financial capacity | 5% |

| Joint venture criterion | Weight |
| --- | ---: |
| Resource complementarity | 20% |
| Operational capability | 15% |
| Business opportunity | 15% |
| Strategic alignment | 12% |
| Industry relationship | 10% |
| Project feasibility | 13% |
| Implementation risk | 10% |
| Financial capacity | 5% |

Capability taxonomy links describe plausible value-chain fit (for example, connectivity with banking or drilling with energy); these are explicit hypotheses, not evidence of an existing contract. Text overlap can indicate operational familiarity and competitive risk, so both fit and risk dimensions are shown. Unlisted sector relationships are neutral rather than penalized. Missing/synthetic financial rows are never treated as verified facts; unavailable criteria are omitted and the UI shows evidence coverage and limitations. Gemini can explain supplied facts and calculated scores but cannot alter them. These heuristics are not an empirically validated prediction model, and scores are not investment recommendations. Identical evidence can yield genuine ties; stable discovery tie order uses the company symbol. On the 27-company catalogue snapshot, the 351 unordered pairs produced 104 distinct rounded partnership scores and 105 distinct rounded joint-venture scores; repeated generic issuer summaries still create ties, so this is a useful prototype range, not proof of predictive accuracy.

## Removed business monitoring interface

The partnership KPI monitoring page and its write routes are not part of the current product. Legacy relationship tables may remain in an existing SQLite database for backward compatibility, but the application no longer seeds demo relationships or exposes those records in the interface. The System Monitoring Dashboard covers application and AI service telemetry only.
