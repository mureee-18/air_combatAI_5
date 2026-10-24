import atexit
import importlib
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

zip_path = Path(sys.argv[1])
extract_root = Path(tempfile.mkdtemp(prefix="zipcheck_"))
atexit.register(shutil.rmtree, extract_root, True)

with zipfile.ZipFile(zip_path) as z:
    z.extractall(extract_root / "MyAgent")

sys.path.insert(0, str(extract_root))
module = importlib.import_module("MyAgent")
args = json.load(open(extract_root / "MyAgent" / "args.json"))

print("class:", module.getUserAgentClass(args).__name__)
print("config entries:", len(module.getUserAgentModelConfig(args)))
print("single asset:", module.isUserAgentSingleAsset(args))
print("policy:", module.getUserPolicy(args).__class__.__name__)
