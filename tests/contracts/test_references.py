import json
from pathlib import Path

import pytest
from contracts.references import ReferenceUnavailable, load_reference_bundle
from django.core.management import call_command
from django.core.management.base import CommandError


def test_loads_only_verified_installed_version(reference_bundle):
    bundle = load_reference_bundle()
    assert bundle.version == "synthetic-v1"
    assert bundle.template_bytes("yayasan").startswith(b"PK")


def test_template_corruption_fails_on_second_read(reference_bundle):
    bundle = load_reference_bundle()
    (reference_bundle / "yayasan.docx").write_bytes(b"changed")
    with pytest.raises(ReferenceUnavailable):
        bundle.template_bytes("yayasan")


@pytest.mark.parametrize("file", ["../outside.docx", "C:/secret.docx", "/secret.docx"])
def test_symlink_or_relative_escape_rejected(reference_bundle, file):
    path = reference_bundle / "manifest.json"
    data = json.loads(path.read_text())
    data["templates"]["yayasan"]["file"] = file
    path.write_text(json.dumps(data))
    with pytest.raises(ReferenceUnavailable):
        load_reference_bundle()


def test_failed_install_does_not_switch_active(reference_bundle, tmp_path):
    destination = tmp_path / "installed"
    call_command("install_contract_references", source=str(reference_bundle), root=str(destination))
    active = (destination / "active.json").read_bytes()
    (reference_bundle / "guru.docx").write_bytes(b"changed")
    with pytest.raises(CommandError):
        call_command(
            "install_contract_references", source=str(reference_bundle), root=str(destination)
        )
    assert (destination / "active.json").read_bytes() == active


def test_same_version_different_content_rejected(reference_bundle, tmp_path):
    destination = tmp_path / "installed"
    call_command("install_contract_references", source=str(reference_bundle), root=str(destination))
    (reference_bundle / "unlisted.txt").write_text("changed")
    with pytest.raises(CommandError):
        call_command(
            "install_contract_references", source=str(reference_bundle), root=str(destination)
        )


def test_development_accepts_isolated_build_override(monkeypatch, tmp_path):
    import importlib

    from config.settings import development

    monkeypatch.setenv("HRM_FRONTEND_DIST", str(tmp_path))
    try:
        assert importlib.reload(development).FRONTEND_DIST == Path(tmp_path)
    finally:
        monkeypatch.delenv("HRM_FRONTEND_DIST")
        importlib.reload(development)
