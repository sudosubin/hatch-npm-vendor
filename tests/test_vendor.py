from __future__ import annotations

import base64
import hashlib
import io
import json
import tarfile
from pathlib import Path
from typing import TYPE_CHECKING, Mapping

import pytest

from hatch_npm_vendor.vendor import (
    NpmPackageSpec,
    check_integrity,
    install_packages,
    parse_package_specs,
    vendor_package,
)

if TYPE_CHECKING:
    from typing_extensions import Self

REGISTRY = "https://registry.test"


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _sha512_integrity(data: bytes) -> str:
    digest = base64.b64encode(hashlib.sha512(data).digest()).decode()
    return f"sha512-{digest}"


def _make_tarball(files: Mapping[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as archive:
        for name, payload in files.items():
            info = tarfile.TarInfo(name=f"package/{name}")
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    return buf.getvalue()


def _serve_package(
    monkeypatch: pytest.MonkeyPatch, package: str, version: str, tarball: bytes
) -> None:
    tarball_url = f"{REGISTRY}/{package}.tgz"
    meta = json.dumps({"dist": {"tarball": tarball_url}}).encode()
    responses = {
        f"{REGISTRY}/{package}/{version}": meta,
        tarball_url: tarball,
    }

    def fake_urlopen(url: str) -> FakeResponse:
        return FakeResponse(responses[url])

    monkeypatch.setattr(
        "hatch_npm_vendor.vendor.urllib.request.urlopen", fake_urlopen
    )


def test_parse_package_specs_from_list() -> None:
    config = {
        "packages": [
            {
                "dest": "pkg/node_modules/a",
                "package": "a",
                "version": "1.0.0",
                "integrity": "sha512-x",
            },
            {
                "dest": "pkg/node_modules/b",
                "package": "b",
                "version": "2.0.0",
                "integrity": "sha512-y",
            },
        ],
    }
    specs = parse_package_specs(config)
    assert len(specs) == 2
    assert specs[0].package == "a"
    assert specs[1].dest == "pkg/node_modules/b"


def test_parse_package_specs_requires_entries() -> None:
    with pytest.raises(ValueError, match="at least one"):
        parse_package_specs({})


def test_check_integrity_mismatch() -> None:
    data = b"hello"
    integrity = _sha512_integrity(b"other")
    with pytest.raises(RuntimeError, match="checksum mismatch"):
        check_integrity(data, integrity)


def test_vendor_package_extracts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = b"file-contents"
    tarball = _make_tarball({"hello.txt": payload})
    _serve_package(monkeypatch, "demo-pkg", "1.0.0", tarball)

    dest = tmp_path / "node_modules" / "demo-pkg"
    vendor_package(
        dest,
        "demo-pkg",
        "1.0.0",
        _sha512_integrity(tarball),
        registry=REGISTRY,
    )
    assert (dest / "hello.txt").read_bytes() == payload
    assert [p.name for p in dest.parent.iterdir()] == ["demo-pkg"]


def test_install_packages_force_include(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tarball = _make_tarball({"readme": b"x"})
    _serve_package(monkeypatch, "pkg-a", "1.0.0", tarball)

    (tmp_path / "src" / "mymod").mkdir(parents=True)
    build_data: dict = {}
    install_packages(
        tmp_path,
        build_data,
        [
            NpmPackageSpec(
                dest="mymod/node_modules/pkg-a",
                package="pkg-a",
                version="1.0.0",
                integrity=_sha512_integrity(tarball),
            ),
        ],
        src="src",
        registry=REGISTRY,
    )
    dest_file = tmp_path / "src" / "mymod" / "node_modules" / "pkg-a" / "readme"
    assert dest_file.is_file()
    assert (
        build_data["force_include"][str(dest_file)]
        == "mymod/node_modules/pkg-a/readme"
    )
