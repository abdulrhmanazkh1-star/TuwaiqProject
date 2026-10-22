# AI evaluation

## What is automated vs human

| Check | Method | Result source |
| --- | --- | --- |
| Compatibility formulas | pytest | executed tests |
| Retained KPI formula helper | pytest | utility tests only; business monitoring page removed |
| Monitoring event write-path | pytest | executed tests |
| Live LLM factual accuracy | human template below | not invented |

Do not report an accuracy percentage unless a human completed the template on a saved analysis.

## Human review template

Copy for each analysis ID:

- Analysis ID:
- Reviewer:
- Mode (demo_rules / llm):
- Factual claims listed:
- Claims supported by company DB/source URL: / total claims
- Unsupported or invented claims:
- Did the text distinguish facts vs interpretation? (yes/no)
- Notes:

Store completed reviews in `ai_evaluation_results` (model exists) or in this file.

## Demo Mode policy

If `LLM_API_KEY` is empty, narratives are rule-based and labeled **وضع التجربة**. That is not live model inference.
