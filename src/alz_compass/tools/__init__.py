from alz_compass.tools.find_completed_trials import register as register_search
from alz_compass.tools.get_trial_evidence_card import register as register_card


def register_tools(mcp, service):
    register_search(mcp, service)
    register_card(mcp, service)
