# Data handling and security

## Authorized data boundary

Use publicly accessible ClinicalTrials.gov records and clearly labeled synthetic test fixtures. Do not add patient records, internal agency material, CUI, nonpublic project documents, or real patient identifiers to the vendor environment.

The organizer restriction appears in [Databricks Training 1, 00:43–01:03](https://vimeo.com/reviews/3f823da1-c1a8-48bd-8024-a6a2b994b789/videos/1233408257). The presence of enterprise security features in a vendor demonstration does not broaden that authorized data scope.

## Application boundary

- The two MCP tools retrieve records. They do not alter the registry, submit study data, send messages, or provide arbitrary network access.
- The API adapter uses a fixed ClinicalTrials.gov origin. Tool inputs accept an NCT ID or bounded search options, never a caller-supplied URL.
- Keep the local server on loopback. The Databricks deployment listens on the application interface behind Databricks authentication.
- Use the assigned authenticated workspace. Do not make the app public or expose a local server through a public tunnel.
- Grant teammates only the app/model access needed for their task. Confirm permissions for both the human and application identity.

## Credentials and logs

ClinicalTrials.gov retrieval requires no project secret. Authenticate Databricks through the approved workspace workflow. Do not paste tokens into chat, commit them, embed them in notebooks, or put them in screenshots. Store application secrets through supported environment/resource bindings.

Preserve tool arguments, public returned records, response timings, model identifier, and prompt version for evaluation. Do not log authorization headers or credential values. User prompts may contain unexpected private text: use public test prompts only and review logs before sharing.

Snapshot files should contain their public source URL and retrieval time. Preserve the raw public response so another reviewer can reproduce field checks. Separate synthetic failure fixtures from real registry snapshots.

## Retrieved text is untrusted data

Study descriptions and eligibility text may contain instruction-like content. The agent must treat those passages as quoted source evidence. They cannot authorize changing tools, ignoring the system prompt, contacting third parties, or sending credentials. Keep only the project's two retrieval tools available to the agent.

Test this boundary with an explicitly synthetic fixture. Passing a single injection test does not establish general security assurance.

## Clinical and research limits

The assistant prepares registry evidence for review. It does not establish efficacy, choose treatment, perform risk-of-bias appraisal, or certify a systematic review. Missing registry results do not establish that findings or publications do not exist. Trial registration fields may change over time.

## Before publishing a repository or demonstration

1. Review the staged file list and exclude secrets, local environments, raw logs with private prompts, and unrelated project documents.
2. Include only public snapshots and deliberately synthetic tests.
3. Label local, saved-snapshot, and live executions accurately.
4. Confirm the current organizer rules and permitted sharing destination.
5. Keep deployment and model access failures visible in the evaluation report instead of treating them as successful tests.
