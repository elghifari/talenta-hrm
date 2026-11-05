import json
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType

from django.conf import settings

from .constants import JOB_CATALOG_FIELDS, UNIT_CATALOG_FIELDS

KINDS = frozenset(("yayasan", "guru", "klinik_umum"))
VERSION = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")


class ReferenceUnavailable(Exception):
    def __init__(self):
        super().__init__("Reference package unavailable")


def checked_path(root, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ReferenceUnavailable()
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ReferenceUnavailable()
    return path


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ReferenceUnavailable()
            result[key] = value
        return result

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)


def verified_file(directory, name, digest):
    if not isinstance(digest, str) or not HASH.fullmatch(digest):
        raise ReferenceUnavailable()
    path = checked_path(directory, name)
    if path.stat().st_size > 5 * 1024 * 1024:
        raise ReferenceUnavailable()
    content = path.read_bytes()
    if sha256(content).hexdigest() != digest:
        raise ReferenceUnavailable()
    return content


def catalog(content):
    rows = json.loads(content)
    if not isinstance(rows, list):
        raise ReferenceUnavailable()
    result = {}
    for row in rows:
        if not isinstance(row, dict) or not all(isinstance(v, str) for v in row.values()):
            raise ReferenceUnavailable()
        key = row.get("key", "").strip().casefold()
        if not key or key in result:
            raise ReferenceUnavailable()
        result[key] = MappingProxyType(row)
    return MappingProxyType(result)


@dataclass(frozen=True)
class ReferenceBundle:
    directory: Path
    version: str
    templates: object
    units: object
    jobs: object

    def template_sha256(self, pkwt_type):
        if pkwt_type not in KINDS:
            raise ReferenceUnavailable()
        return self.templates[pkwt_type]["sha256"]

    def template_bytes(self, pkwt_type):
        try:
            digest = self.template_sha256(pkwt_type)
            return verified_file(self.directory, self.templates[pkwt_type]["file"], digest)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise ReferenceUnavailable() from exc


def load_directory(directory, version):
    try:
        if not isinstance(version, str) or not VERSION.fullmatch(version):
            raise ReferenceUnavailable()
        manifest = read_json(directory / "manifest.json")
        if manifest["version"] != version or set(manifest["templates"]) != KINDS:
            raise ReferenceUnavailable()
        templates = MappingProxyType(
            {key: MappingProxyType(value) for key, value in manifest["templates"].items()}
        )
        bundle = ReferenceBundle(
            directory,
            version,
            templates,
            catalog(verified_file(directory, manifest["units_file"], manifest["units_sha256"])),
            catalog(verified_file(directory, manifest["jobs_file"], manifest["jobs_sha256"])),
        )
        for row in bundle.units.values():
            if row.keys() - UNIT_CATALOG_FIELDS:
                raise ReferenceUnavailable()
            if (
                not row.get("unit", "").strip()
                or row["key"].strip().casefold() != row["unit"].strip().casefold()
            ):
                raise ReferenceUnavailable()
        for row in bundle.jobs.values():
            if row.keys() - JOB_CATALOG_FIELDS:
                raise ReferenceUnavailable()
            if not {"key", "unit", "division", "title", "pkwt_type", "jobdesk"} <= row.keys():
                raise ReferenceUnavailable()
            if (
                row["pkwt_type"] not in KINDS
                or not row["title"].strip()
                or not row["jobdesk"].strip()
            ):
                raise ReferenceUnavailable()
            if len(row["jobdesk"]) > 20000 or row["unit"].strip().casefold() not in bundle.units:
                raise ReferenceUnavailable()
            expected = "||".join(
                (row["unit"].strip(), row["division"].strip() or "(Umum)", row["title"].strip())
            )
            if row["key"] != expected:
                raise ReferenceUnavailable()
        for kind in KINDS:
            bundle.template_bytes(kind)
        return bundle
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise ReferenceUnavailable() from exc


def load_reference_bundle(version=None):
    try:
        root = Path(settings.CONTRACT_REFERENCE_ROOT).resolve()
        if version is None:
            active = read_json(root / "active.json")
            if set(active) != {"version"}:
                raise ReferenceUnavailable()
            version = active["version"]
        if not isinstance(version, str) or not VERSION.fullmatch(version):
            raise ReferenceUnavailable()
        return load_directory(checked_path(root, version), version)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise ReferenceUnavailable() from exc
