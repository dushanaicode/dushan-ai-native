import importlib
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[2] / "dushan-admin-backend/module_infra"
IMPLEMENTATIONS = [
    "module_infra." + ".".join(path.relative_to(MODULE).with_suffix("").parts)
    for path in sorted(MODULE.rglob("*.py"))
    if path.name != "__init__.py"
]


@pytest.mark.parametrize("name", IMPLEMENTATIONS)
def test_module_imports(name):
    importlib.import_module(name)
