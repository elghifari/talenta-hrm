import json

import pytest


@pytest.fixture
def frontend_build(tmp_path, settings):
    (tmp_path / ".vite").mkdir()
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "main.js").write_text("console.log('synthetic')")
    (tmp_path / "assets" / "main.css").write_text("body{color:black}")
    manifest = {"index.html": {"file": "assets/main.js", "css": ["assets/main.css"]}}
    (tmp_path / ".vite" / "manifest.json").write_text(json.dumps(manifest))
    settings.FRONTEND_DIST = tmp_path
    return tmp_path


def test_employee_deep_link_uses_built_manifest(client, frontend_build):
    response = client.get("/employees/00000000-0000-0000-0000-000000000001/edit")
    assert response.status_code == 200
    assert b"/assets/main.js" in response.content
    assert b"/assets/main.css" in response.content


@pytest.mark.parametrize(
    "path", ["/api/unknown/", "/assets/missing.js", "/assets/../secret", "/.vite/manifest.json"]
)
def test_frontend_fallback_does_not_serve_protected_paths(client, frontend_build, path):
    response = client.get(path)
    assert response.status_code == 404
    assert b'<div id="root"' not in response.content


def test_missing_frontend_build_is_controlled(client, settings, tmp_path):
    settings.FRONTEND_DIST = tmp_path
    assert client.get("/employees").status_code == 503


def test_malformed_frontend_manifest_is_controlled(client, frontend_build):
    (frontend_build / ".vite" / "manifest.json").write_text("not json")
    assert client.get("/employees").status_code == 503


def test_asset_can_be_served_from_build(client, frontend_build):
    response = client.get("/assets/main.js")
    assert response.status_code == 200
    assert "javascript" in response["Content-Type"]
    response.close()
