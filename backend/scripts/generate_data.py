from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2] / "scripts" / "generate_data.py"
_spec = importlib.util.spec_from_file_location("root_generate_data", _ROOT)
if _spec is None or _spec.loader is None:
    raise ModuleNotFoundError(f"Could not load project generator from {_ROOT}")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

for _name in dir(_module):
    if _name.startswith("__"):
        continue
    globals()[_name] = getattr(_module, _name)
