from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import tarfile
import tempfile
import urllib.request
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class NpmPackageSpec:
    dest: str
    package: str
    version: str
    integrity: str

    def __post_init__(self) -> None:
        # ``dest`` is wiped and recreated, so it must stay inside the source
        # root and must not be the root itself.
        dest = PurePosixPath(self.dest)
        if not dest.parts or dest.is_absolute() or ".." in dest.parts:
            raise ValueError(
                f"npm-vendor: 'dest' must be a relative path inside the "
                f"source root, got {self.dest!r}"
            )


def parse_package_specs(config: Mapping[str, Any]) -> list[NpmPackageSpec]:
    raw = config.get("packages", [])
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise TypeError("npm-vendor: 'packages' must be a list of tables")
    if not raw:
        raise ValueError("npm-vendor: configure at least one packages entry")
    try:
        return [NpmPackageSpec(**entry) for entry in raw]
    except TypeError as exc:
        raise ValueError(f"npm-vendor: invalid package entry: {exc}") from exc


def install_packages(
    root: Path,
    build_data: dict[str, Any],
    specs: Sequence[NpmPackageSpec],
    *,
    src: str,
    registry: str,
) -> None:
    includes = build_data.setdefault("force_include", {})
    for spec in specs:
        target = PurePosixPath(spec.dest).as_posix()  # drops trailing "/"
        dest = root / src / target
        vendor_package(
            dest, spec.package, spec.version, spec.integrity, registry=registry
        )
        for path in dest.rglob("*"):
            if path.is_file():
                rel = path.relative_to(dest).as_posix()
                includes[str(path)] = f"{target}/{rel}"


def vendor_package(
    dest: Path,
    package: str,
    version: str,
    integrity: str,
    *,
    registry: str,
) -> None:
    meta = json.loads(_fetch(f"{registry.rstrip('/')}/{package}/{version}"))
    data = _fetch(meta["dist"]["tarball"])
    check_integrity(data, integrity)
    _extract(data, dest)


def _extract(data: bytes, dest: Path) -> None:
    """Replace ``dest`` with the contents of an npm tarball."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest.parent) as tmp:
        with tarfile.open(fileobj=BytesIO(data), mode="r:gz") as archive:
            if hasattr(tarfile, "data_filter"):
                archive.extractall(tmp, filter="data")
            else:
                archive.extractall(tmp)
        # npm tarballs wrap everything in one top-level dir (usually
        # "package", but e.g. "node" for @types/node).
        (top_level,) = Path(tmp).iterdir()
        shutil.rmtree(dest, ignore_errors=True)
        top_level.rename(dest)


def _fetch(url: str) -> bytes:
    with urllib.request.urlopen(url) as response:
        return response.read()


def check_integrity(data: bytes, integrity: str) -> None:
    algo, digest = integrity.split("-", 1)
    if algo != "sha512":
        raise RuntimeError(f"unsupported npm integrity: {integrity}")
    expected = base64.b64decode(digest)
    if hashlib.sha512(data).digest() != expected:
        raise RuntimeError(f"{integrity}: checksum mismatch")


def should_skip() -> bool:
    values = {"1", "true", "yes"}
    return os.environ.get("HATCH_NPM_VENDOR_SKIP", "").lower() in values
