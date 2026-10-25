import json
import os


def get_model_config(args={}):
    here = os.path.abspath(__file__)
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(here))))
    path = os.path.join(root, "config.json")
    with open(path) as f:
        configs = json.load(f)
    if isinstance(args, dict) and "maxSimulShot" in args:
        configs.setdefault("Fixed", {})["maxSimulShot"] = int(args["maxSimulShot"])
    return configs.get("Fixed", {})
