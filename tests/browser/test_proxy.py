import os
import shutil
import socket
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def vite_origin(live_server, tmp_path, settings):
    root = Path(__file__).resolve().parents[2]
    executable = root / "frontend" / "node_modules" / "vite" / "bin" / "vite.js"
    env = {**os.environ, "HRM_API_TARGET": live_server.url}
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    settings.CSRF_TRUSTED_ORIGINS = [*settings.CSRF_TRUSTED_ORIGINS, origin]
    with (tmp_path / "vite.log").open("w") as log:
        process = subprocess.Popen(
            [
                shutil.which("node"),
                str(executable),
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--strictPort",
            ],
            cwd=root / "frontend",
            env=env,
            stdout=log,
            stderr=log,
            start_new_session=os.name != "nt",
        )
        try:
            deadline = time.monotonic() + 30
            while True:
                if process.poll() is not None:
                    pytest.fail("Vite exited before proxy smoke test; inspect its test log")
                try:
                    with urlopen(origin + "/api/health/", timeout=1) as response:
                        if response.status == 200:
                            break
                except (OSError, URLError):
                    if time.monotonic() >= deadline:
                        pytest.fail("Vite proxy did not become ready")
                    time.sleep(0.1)
            yield origin
        finally:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True
                )
            else:
                import signal

                os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=10)


def test_proxy_preserves_real_cookie_csrf_login_write_and_logout(page, login, vite_origin):
    login(page, url=vite_origin)
    page.get_by_role("link", name="Tambah pegawai", exact=True).click()
    page.get_by_label("Kode pegawai", exact=True).fill("0088")
    page.get_by_label("Nama lengkap", exact=True).fill("Pegawai Contoh Proxy")
    page.get_by_role("button", name="Simpan pegawai", exact=True).click()
    expect(page.get_by_role("heading", name="Pegawai Contoh Proxy", exact=True)).to_be_visible()
    page.reload()
    expect(page.get_by_text("0088", exact=True)).to_be_visible()
    page.get_by_role("button", name="Keluar", exact=True).click()
    expect(page.get_by_role("button", name="Masuk", exact=True)).to_be_visible()
    assert page.context.request.get(vite_origin + "/api/auth/me/").status == 403
