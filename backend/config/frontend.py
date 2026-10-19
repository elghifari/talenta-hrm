import json
import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.utils.html import escape
from django.views.decorators.http import require_GET


def build_root():
    if not getattr(settings, "FRONTEND_DEV_ENABLED", False):
        raise Http404
    return Path(settings.FRONTEND_DIST).resolve()


def asset_path(root, name):
    if not isinstance(name, str) or "\\" in name or ":" in name:
        raise ValueError("Invalid asset path")
    target = (root / name).resolve()
    if not target.is_relative_to(root / "assets") or not target.is_file():
        raise ValueError("Missing asset")
    return target


@require_GET
def asset(request, name):
    root = build_root()
    try:
        target = asset_path(root, "assets/" + name)
    except ValueError as error:
        raise Http404 from error
    return FileResponse(target.open("rb"), content_type=mimetypes.guess_type(target)[0])


@require_GET
def spa(request, path=""):
    root = build_root()
    if path.startswith(("api/", "assets/", "static/", ".")) or path in ("api", "assets", "static"):
        raise Http404
    try:
        manifest = json.loads((root / ".vite" / "manifest.json").read_text(encoding="utf-8"))
        entry = manifest["index.html"]
        script = entry["file"]
        asset_path(root, script)
        css = entry.get("css", [])
        if not isinstance(css, list):
            raise ValueError("Invalid styles")
        for style in css:
            asset_path(root, style)
        styles = "".join(f'<link rel="stylesheet" href="/{escape(style)}">' for style in css)
    except (OSError, ValueError, KeyError, TypeError):
        return HttpResponse(
            "Frontend build unavailable. Run npm run build in frontend.", status=503
        )
    response = HttpResponse(
        '<!doctype html><html lang="id"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>Talenta HRIS</title>{styles}</head><body><div id="root"></div>'
        f'<script type="module" src="/{escape(script)}"></script></body></html>'
    )
    response["Cache-Control"] = "no-store"
    return response
