from typing import Annotated

from pydantic import Field


def register(mcp, service):
    @mcp.tool(
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        }
    )
    async def find_completed_trials(
        intervention: Annotated[str | None, Field(max_length=120)] = None,
        limit: Annotated[int, Field(ge=1, le=5, strict=True)] = 3,
    ) -> dict:
        """Find a bounded list of completed type 2 diabetes intervention trials.

        Optional intervention narrows the fixed Type 2 Diabetes condition query.
        Enforces COMPLETED, INTERVENTIONAL and explicit supported type 2 condition
        labels. The conservative label screen can miss broadly labeled studies.
        Returns candidate
        identifiers, source links, results availability, exact search criteria and
        coverage limitations. Use get_trial_evidence_card for actual study details.
        This is not exhaustive searching or screening for diagnosed participants.
        """
        return await service.find_completed_trials(
            intervention=intervention, limit=limit
        )
