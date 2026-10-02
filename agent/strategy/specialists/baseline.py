from ASRCAISim1.policy import StandalonePolicy


def get_agent_class(args={}):
    from BasicAirToAirCombatModels01 import BasicAACRuleBasedAgent01

    return BasicAACRuleBasedAgent01


def get_policy(args={}):
    return DummyPolicy()


def get_model_config(args={}):
    import json
    import os

    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config.json")
    with open(path) as f:
        configs = json.load(f)
    return configs.get("Baseline", {}).get("Fixed", {})


class DummyPolicy(StandalonePolicy):
    def step(self, observation, reward, done, info, agentFullName, observation_space, action_space):
        return None
