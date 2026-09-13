import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def test_resources_are_packaged_and_declared():
    from importlib.resources import files

    resource = files("framework.starter_captcha").joinpath("resources")
    manifest = json.loads(resource.joinpath("provenance.json").read_text(encoding="utf-8"))
    font = resource.joinpath(manifest["font"]).read_bytes()
    assert hashlib.sha256(font).hexdigest() == manifest["sha256"]
    assert len(font) < 50000
    assert "SIL OPEN FONT LICENSE Version 1.1" in resource.joinpath("OFL.txt").read_text()


def test_import_does_not_open_connections_or_write_bytecode(tmp_path):
    import framework.starter_captcha as captcha

    source = """
import importlib, socket, pathlib
def blocked(*args, **kwargs):
    raise AssertionError('module import attempted external connection')
socket.socket.connect = blocked
socket.create_connection = blocked
root = pathlib.Path(__import__('sys').argv[1])
for path in sorted(root.rglob('*.py')):
    module = 'framework.starter_captcha.' + '.'.join(path.relative_to(root).with_suffix('').parts)
    if module.endswith('.__init__'):
        module = module[:-9]
    importlib.import_module(module)
print('imported all captcha modules without connections')
"""
    script = tmp_path / "import_check.py"
    script.write_text(source, encoding="utf-8")
    root = Path(captcha.__file__).parent
    env = {**os.environ, "PYTHONPATH": str(root.parents[1]), "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run(
        [sys.executable, "-B", str(script), str(root)],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "without connections" in result.stdout
    assert not list(root.rglob("*.pyc"))


def test_protocol_signature_vectors(settings):
    from framework.starter_captcha.model.captcha_answer import CaptchaAnswer
    from framework.starter_captcha.provider.aliyun_captcha_provider import AliyunCaptchaProvider
    from framework.starter_captcha.provider.tencent_captcha_provider import TencentCaptchaProvider

    config = settings(
        aliyun={
            "access_key_id": "test-id",
            "access_key_secret": "test-secret",
            "scene_id": "test-scene",
            "prefix": "test-prefix",
        },
        tencent={
            "app_id": 123456,
            "app_secret": "test-app-secret",
            "secret_id": "test-id",
            "secret_key": "test-secret",
        },
    )
    vectors = json.loads(Path(__file__).with_name("protocol_vectors.json").read_text())
    headers, body = AliyunCaptchaProvider(config.aliyun, None).signed_request(
        "opaque +/=", "2026-09-12T00:00:00Z", "fixed-test-nonce"
    )
    assert headers["authorization"] == vectors["aliyun_authorization"]
    assert hashlib.sha256(body).hexdigest() == vectors["aliyun_body_sha256"]
    headers, body = TencentCaptchaProvider(config.tencent, None).signed_request(
        CaptchaAnswer(ticket="test-ticket", randstr="test-rand"), "2001:db8::1", 1789171200
    )
    assert headers["authorization"] == vectors["tencent_authorization"]
    assert hashlib.sha256(body).hexdigest() == vectors["tencent_body_sha256"]
