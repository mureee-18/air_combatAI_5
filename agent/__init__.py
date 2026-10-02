from .strategy import active


def getUserAgentClass(args={}):
    return active.get_agent_class(args)


def getUserAgentModelConfig(args={}):
    return active.get_agent_model_config(args)


def isUserAgentSingleAsset(args={}):
    return active.is_single_asset(args)


def getUserPolicy(args={}):
    return active.get_policy(args)
