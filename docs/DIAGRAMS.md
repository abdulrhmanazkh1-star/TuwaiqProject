# Technical diagrams (implemented system)

These diagrams match the running Flask + SQLite application, not a conceptual future architecture.

## Development Flow

```mermaid
flowchart LR
  A[Requirements\nTuwaiq Project 1] --> B[Data preparation\nseed.py + CSV import]
  B --> C[Backend\nFlask + SQLAlchemy models]
  C --> D[Scoring engine\napp/scoring_engine.py cm-score-v2]
  D --> E[AI integration\nai_engine.py\nLLM or Demo Mode]
  E --> F[Frontend RTL\nJinja + Chart.js]
  F --> G[Pytest\ntests/]
  G --> H[Debug\nsimulate failures]
  H --> I[Local run\npython run.py]
  I --> J[Maintenance\nlogs + monitoring events]
```

Lifecycle actually used:

1. Read the course requirements (product + monitoring + evaluation).
2. Create a local catalogue of listed company identities referenced to the Saudi Exchange issuer directory; leave financial fields blank until official data is sourced.
3. Implement models, scoring, routes, templates.
4. Wire LLM via env vars with deterministic fallback.
5. Add pytest coverage for scores, discovery, and technical monitoring.
6. Run locally, fix failures, and keep SQLite file in the instance path. Startup seeds the company catalogue and does not fabricate technical telemetry.

## Monitoring Flow

```mermaid
flowchart TB
  subgraph Technical["Technical monitoring (System dashboard)"]
    E1[Application events\nanalysis / discovery / validation] --> C1[record_event]
    C1 --> DB1[(technical_monitoring_events)]
    DB1 --> M1[dashboard_metrics\ncounts, latency, error rate, tokens, cost]
    M1 --> UI1[System Monitoring Dashboard]
    M1 --> AL1[Visible failures and simulate buttons]
  end

```

The implemented monitoring flow covers technical application events only.
