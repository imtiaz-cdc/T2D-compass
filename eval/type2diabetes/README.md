# Type 2 diabetes scenario baseline

This separate twelve-case suite adapts the existing researcher workflow to type 2 diabetes. It has **not been run with a real model**. No Alzheimer or obesity result applies to this disease baseline. The proposed twenty-case expansion remains future work.

[agent_scenarios.json](agent_scenarios.json) defines six normal cases and six boundary cases, including seven critical cases. The existing team target remains at least 11 of 12 passes in each of two runs, with every critical case passing. A completed answer is not automatically a pass.

Use [bindings.example.json](bindings.example.json) with [the T2D agent manifest](../../data/type2diabetes/manifest-agent.json). These are mechanically verified fixture roles, not approved clinical references:

| Binding | Value |
| --- | --- |
| Completed with posted results | `NCT03244800` |
| Completed without posted results | `NCT05790681` |
| Different completed comparison record | `NCT04214600` |
| Active exclusion | `NCT05743387` |
| Intervention text | `MEDI0382` |
| Missing ID in the frozen snapshot | `NCT99999999` |

The no-results example is a study in children and teenagers; comparisons must retain population/eligibility context. The two supplied comparison records are for describing differences, not demonstrating clinically equivalent outcomes or treatment effects.

The missing ID is absent from this snapshot; no new live HTTP 404 observation is claimed. Recheck it before live evaluation. `T2D_COMPASS_NO_MATCH_87C4` returns no matches in this frozen set. The outage scenario still requires the explicit snapshot-only failure fixture to be present in its saved trace.

From the repository root, set `ALZ_COMPASS_DATA_MODE` to `snapshot` and `ALZ_COMPASS_MANIFEST` to the absolute path of `data/type2diabetes/manifest-agent.json`. Use the updated runner with `--run scenarios --bindings eval/type2diabetes/bindings.example.json --repeats 2` only after its selected model route is configured and verified. The earlier successful browser assistant used a different gateway route; it does not establish that the command-line model route works. Restore the default manifest after scenario work, and keep the active exclusion outside the core accuracy denominator.

Saved local checks:

- [Fixture validation](results/fixture-validation.json): ten core records, six development/four held-out, one separate exclusion, hashes and all twelve prompt bindings.
- [Snapshot binding validation](results/binding-validation.json): six development records load from the core manifest and seven from the agent manifest; T2D label screen, search, evidence-card fixture roles and error cases pass. No held-out records loaded.
- [Pending-reference check](results/pending-reference-check.json): six pending development cards, zero compared cards, no accuracy assigned.

Clinical review, approved references, real-model scenarios and held-out accuracy remain pending. The [dataset guide](../../data/type2diabetes/README.md) documents the source selection, captured examples and limitations.
