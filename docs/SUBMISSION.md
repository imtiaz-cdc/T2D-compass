# T2D Compass submission checklist

Status: **repository prepared for completion; final submission artifacts and reviews remain pending**. Updated November 12, 2026. The team confirmed that no final demo video or completed model/clinical evaluation is available yet.

The submitted scope is version 0.4.0: one MCP server, two tools, browser search and evidence cards, JSON export and an optional tool-using assistant. ClinicalTrials.gov is the only data source. A dedicated comparison tool and expanded benchmark are future work.

## Organizer requirements and prepared evidence

The [official GSA event page](https://www.gsa.gov/super-intelligence/si-community-of-practice/events-and-training/mcp-server-and-si-agent-government-hackathon), checked November 12, requests documented GitHub code, a presentation and evaluation documentation. It still lists **Friday, November 20, 2026** as the submission date, without a cutoff time or submission channel. Judging covers technical quality, innovation, mission alignment and presentation. Confirm any later organizer instructions before sending the final entry.

| Deliverable | Repository location / current status | Remaining work |
| --- | --- | --- |
| Complete, documented code | [Repository](https://github.com/imtiaz-cdc/T2D-compass), [README](../README.md), `src/`, `tests/`, dependency/configuration files | Confirm the final published revision and evaluator access; retain its commit identifier with the submission |
| Presentation | See the presentation link in the [README](../README.md) | Review final wording against actual evidence; record the accepted revision and include the demo link |
| Evaluation documentation | [Evaluation report](EVALUATION.md), [evidence index](../eval/README.md) | Complete independent references and real-model scoring; preserve honest pending labels for anything unfinished |
| Demonstration video | **Pending: no final recording supplied** | Record the tested T2D workflow and make its link accessible to evaluators |

The [October 19 kickoff recording](https://vimeo.com/reviews/3f823da1-c1a8-48bd-8024-a6a2b994b789/videos/1237744098), **30:17–32:01**, asks for an accessible repository, a deck and evaluation evidence, plus a video showing the use case and evaluation. Its slide at **31:40** displays the literal `>5 mins`; the spoken guidance does not give a numeric duration. Confirm the final format/duration instruction rather than treating a team recording target as a verified organizer rule.

## App access

- [T2D Compass app](https://t2d-compass-7474654188777746.aws.databricksapps.com/): user-reported deployed instance. Databricks sign-in and appropriate app permissions are required; successful local checks do not prove each evaluator can access it.
- [Management overview](https://dbc-aae0ba16-8727.cloud.databricks.com/apps-v2/app/t2d-compass/overview?o=7474654188777746): deployment, logs and settings for authorized **CAN MANAGE** users. This is not the evaluator's app link.
- Test the ordinary app link using the intended reviewer's access. Keep the app in the authorized authenticated environment. Provide a playable demonstration because judges may not be able to execute the application themselves.

## Finish the evidence

Chinelo leads technical delivery, evaluation execution, packaging and submission. Mohammad leads clinical source interpretation and reference review; both reconcile discrepancies.

- [ ] Freeze the candidate code, prompt, dependencies, snapshot hashes, scenario bindings, model identity and scoring rules before acceptance testing.
- [ ] Mohammad prepares source-first references; Chinelo independently checks all required groups, source locations and relationships. Approve the exact reviewed records in the existing reference form.
- [ ] Compare approved development references, then perform the first held-out evaluation on the frozen candidate. Preserve first-run results and report the four held-out records separately from development.
- [ ] Verify the chosen model route, then run all twelve scenarios twice. Retain actual tool traces, answers, failure fixtures and durations; independently score every case. Target at least 11/12 per run with all seven critical cases passing. These are team targets, not organizer thresholds.
- [ ] Verify deployed search, card retrieval, source links, JSON export and optional assistant/trace export with authorized access. Record actual model/source mode and version; retain failures as evidence.
- [ ] Update the evaluation report and presentation with measured counts, denominators and limitations. Do not convert software checks into model or clinical accuracy claims.

## Record and assemble

Use the [demonstration script](DEMO.md) for a rehearsal of the current scope.

- [ ] Record the problem and intended researcher workflow, search with enforced scope, a source-linked card, results-availability limits, an error/out-of-scope example, and evaluation evidence. Show the assistant only with an actual verified run; label recorded or snapshot segments.
- [ ] Check that the video has no tokens, private prompts, patient data or management-only information. Confirm the recording plays through and its sharing permission works for evaluators.
- [ ] Add the final video link to the README and presentation; replace pending statements only when the artifact exists.
- [ ] Review the repository for credentials, local environments/caches, private material, broken relative links and stale placeholder claims. Preserve the MIT license and starter attribution.
- [ ] Confirm that the deck, evaluation report, video and source all describe the same two-tool T2D version. Record the final commit identifier and dates together.
- [ ] Confirm the official cutoff time, submission channel, file formats and repository/video access expectations from current organizer instructions.
- [ ] Submit the final repository, deck, evaluation document and video through that channel; retain the confirmation. Publishing repository files alone is not an event submission.

## Accurate claims to retain

The public source set contains ten core records (six development/four held-out) plus one separate active-study exclusion. The agent suite has twelve scenarios, not twenty. The recorded November 12 suite passed 294 automated software tests; it does not establish clinical accuracy. Independent references, scored model results and the final video remain pending until their own reviewed artifacts are added. Do not relabel historical Alzheimer or obesity runs as T2D evidence.
