import importlib

import torch

mods = [
    "torch",
    "tensorflow",
    "pandas",
    "sklearn",
    "lightgbm",
    "cv2",
    "ray",
    "ASRCAISim1",
    "r8_contest_models",
    "BasicAgentUtility",
    "MatchMaker",
]

for name in mods:
    try:
        mod = importlib.import_module(name)
        print(name, getattr(mod, "__version__", "ok"))
    except Exception as e:
        print(name, "FAILED", type(e).__name__, e)

print("cuda", torch.cuda.is_available())
