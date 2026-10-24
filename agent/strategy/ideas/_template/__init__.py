"""新しいアイデアの雛形。

ideas/<作者>_<名前>/ にコピーし、agent/presets/<作者>_<名前>.json で "specialist": "<作者>_<名前>" を指定する。
名前が _ で始まるディレクトリは発見されないので、この雛形自体は選ばれない。
共有コード（specialists/、agents/）は編集せず、継承かコピーで変える。
"""
from ...specialists.default import DefaultPolicy, get_agent_class, get_model_config  # noqa: F401


def get_policy(args={}):
    return IdeaPolicy(args)


class IdeaPolicy(DefaultPolicy):
    pass
