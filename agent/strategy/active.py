# Switchboard - points to active specialist
from agent.strategy.specialists import default

def agent(obs_dict):
    """Main agent function."""
    return default.execute(obs_dict)