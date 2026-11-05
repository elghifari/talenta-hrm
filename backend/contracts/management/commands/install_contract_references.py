import json
import os
import shutil
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from django.core.management.base import BaseCommand, CommandError

from contracts.references import ReferenceUnavailable, load_directory, read_json


def inventory(directory):
    result = {}
    for path in directory.rglob("*"):
        if path.is_symlink():
            raise ReferenceUnavailable()
        if path.is_file():
            result[path.relative_to(directory).as_posix()] = sha256(path.read_bytes()).hexdigest()
    return result


class Command(BaseCommand):
    help = "Verify, install and activate an immutable contract reference version (no DB writes)."

    def add_arguments(self, parser):
        parser.add_argument("--source", required=True)
        parser.add_argument("--root", required=True)

    def handle(self, *args, **options):
        try:
            source, root = Path(options["source"]).resolve(), Path(options["root"]).resolve()
            version = read_json(source / "manifest.json")["version"]
            load_directory(source, version)
            source_inventory = inventory(source)
            root.mkdir(parents=True, exist_ok=True)
            destination = root / version
            with TemporaryDirectory(prefix=".install-", dir=root) as temporary:
                staging = Path(temporary) / version
                shutil.copytree(source, staging)
                load_directory(staging, version)
                if inventory(staging) != source_inventory:
                    raise ReferenceUnavailable()
                if destination.exists():
                    if inventory(destination) != source_inventory:
                        raise ReferenceUnavailable()
                    load_directory(destination, version)
                else:
                    os.rename(staging, destination)
            pointer = root / (".active-" + str(uuid4()) + ".json")
            try:
                pointer.write_text(json.dumps({"version": version}), encoding="utf-8")
                os.replace(pointer, root / "active.json")
            finally:
                pointer.unlink(missing_ok=True)
        except (ReferenceUnavailable, OSError, ValueError, KeyError, TypeError) as exc:
            raise CommandError("Reference package installation refused") from exc
        self.stdout.write("Contract reference package verified and activated: " + version)
