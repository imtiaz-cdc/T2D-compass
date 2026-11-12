# T2D Compass demonstration script

Recording status: **pending**. This is a rehearsal plan, not a claim that a video or model run exists. The team recommends approximately six to seven minutes, subject to the organizer's confirmed instructions. See [SUBMISSION.md](SUBMISSION.md) for the kickoff wording and remaining checks.

| Approximate segment | Demonstration |
| --- | --- |
| 0:00–0:45 | Explain the researcher's repeated registry-review task and the app's two-tool scope. State source mode, version and demonstration date. |
| 0:45–2:00 | Search for three completed T2D intervention studies. Show exact search criteria, bounded coverage and condition-label screening. |
| 2:00–3:15 | Open an evidence card, inspect an outcome/timeframe or enrollment label, follow the source link and download its JSON. |
| 3:15–4:15 | Explain completed status versus posted results and eligibility versus enrolled characteristics. Show an out-of-scope or invalid-input example. |
| 4:15–5:30 | If verified, ask the assistant to retrieve a card and show its actual tool trace. Otherwise explicitly demonstrate tools only and retain the pending model status. |
| 5:30–6:30 | Present software checks separately from model and clinical review. Explain what remains pending and the app's research limits. |

Suggested assistant question after the model route works:

> Retrieve the evidence card for NCT03244800. Describe its design, enrollment with its actual/estimated label, interventions and primary outcomes with timeframes. Show results availability, source links and review flags. Do not rank treatments or infer treatment benefit.

For a broader tested question, request three completed T2D intervention candidates and a card for each. Inspect actual tool calls before describing the task as successful. The snapshot examples are frozen October 28, 2026; current live records may differ.

`NCT05790681` is the frozen completed/no-posted-results example and has pediatric context. `NCT05743387` is the separate active-study exclusion. Snapshot direct lookup of that exclusion requires `data/type2diabetes/manifest-agent.json`; the default core manifest intentionally omits it.

Save the accepted source revision, source mode, model identity (when used), trace, video link and reviewer/date together. Keep private account screens and credentials out of the recording. A video of tool use does not replace a scored model evaluation.
