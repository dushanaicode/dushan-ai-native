import importlib.metadata
import os
import subprocess
import sys
from pathlib import Path


def test_otel_release_versions_match():
    assert {
        importlib.metadata.version(name)
        for name in (
            "opentelemetry-api",
            "opentelemetry-sdk",
            "opentelemetry-exporter-otlp-proto-grpc",
            "opentelemetry-proto",
        )
    } == {"1.44.0"}


def test_plain_import_does_not_create_providers_channels_or_threads(tmp_path):
    code = """
import importlib, pathlib, socket, threading
import grpc
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
def blocked(*args, **kwargs):
    raise AssertionError('ordinary import attempted resource creation')
TracerProvider.__init__ = blocked
OTLPSpanExporter.__init__ = blocked
grpc.insecure_channel = blocked
grpc.secure_channel = blocked
socket.socket.connect = blocked
socket.create_connection = blocked
threading.Thread.start = blocked
root = pathlib.Path(__import__('sys').argv[1])
for path in root.rglob('*.py'):
    name = 'framework.starter_monitor.' + '.'.join(path.relative_to(root).with_suffix('').parts)
    if name.endswith('.__init__'): name = name[:-9]
    importlib.import_module(name)
print('ordinary import verified')
"""
    path = tmp_path / "import_probe.py"
    path.write_text(code, encoding="utf-8")
    root = Path(__file__).resolve().parents[3] / "dushan-admin-backend"
    environment = {**os.environ, "PYTHONPATH": str(root), "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run(
        [sys.executable, "-B", str(path), str(root / "framework/starter_monitor")],
        env=environment,
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=True,
    )
    assert "ordinary import verified" in result.stdout
