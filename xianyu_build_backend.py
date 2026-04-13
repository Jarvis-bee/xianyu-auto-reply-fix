from __future__ import annotations

import base64
import csv
import hashlib
import os
from pathlib import Path
import tomllib
from typing import Iterable
import zipfile


ROOT = Path(__file__).resolve().parent
PYPROJECT_PATH = ROOT / "pyproject.toml"


def _load_project_metadata() -> dict:
    with PYPROJECT_PATH.open("rb") as handle:
        data = tomllib.load(handle)
    return data["project"]


PROJECT = _load_project_metadata()
NAME = PROJECT["name"]
VERSION = PROJECT["version"]
SUMMARY = PROJECT.get("description", "")
REQUIRES_PYTHON = PROJECT.get("requires-python", "")
DEPENDENCIES = PROJECT.get("dependencies", [])
SCRIPTS = PROJECT.get("scripts", {})
DIST_NAME = NAME.replace("-", "_")
DIST_INFO = f"{DIST_NAME}-{VERSION}.dist-info"
WHEEL_BASENAME = f"{DIST_NAME}-{VERSION}-py3-none-any"


def _supported_features() -> list[str]:
    return ["build_editable"]


def get_requires_for_build_wheel(config_settings=None) -> list[str]:
    return []


def get_requires_for_build_editable(config_settings=None) -> list[str]:
    return []


def prepare_metadata_for_build_wheel(metadata_directory: str, config_settings=None) -> str:
    return _prepare_metadata(Path(metadata_directory))


def prepare_metadata_for_build_editable(metadata_directory: str, config_settings=None) -> str:
    return _prepare_metadata(Path(metadata_directory))


def build_wheel(wheel_directory: str, config_settings=None, metadata_directory: str | None = None) -> str:
    return _build_archive(Path(wheel_directory), editable=False)


def build_editable(wheel_directory: str, config_settings=None, metadata_directory: str | None = None) -> str:
    return _build_archive(Path(wheel_directory), editable=True)


def _prepare_metadata(metadata_directory: Path) -> str:
    dist_info_dir = metadata_directory / DIST_INFO
    dist_info_dir.mkdir(parents=True, exist_ok=True)
    (dist_info_dir / "METADATA").write_text(_metadata_text(), encoding="utf-8")
    (dist_info_dir / "WHEEL").write_text(_wheel_text(), encoding="utf-8")
    entry_points = _entry_points_text()
    if entry_points:
        (dist_info_dir / "entry_points.txt").write_text(entry_points, encoding="utf-8")
    return DIST_INFO


def _build_archive(wheel_directory: Path, *, editable: bool) -> str:
    wheel_directory.mkdir(parents=True, exist_ok=True)
    filename = f"{WHEEL_BASENAME}.whl"
    wheel_path = wheel_directory / filename

    entries: list[tuple[str, bytes]] = []
    if editable:
        entries.append((f"{DIST_NAME}.pth", f"{ROOT}\n".encode("utf-8")))
    else:
        entries.extend(_package_entries())

    entries.extend(_dist_info_entries())
    record_rows = _record_rows(entries)
    entries.append((f"{DIST_INFO}/RECORD", _record_bytes(record_rows)))

    with zipfile.ZipFile(wheel_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative_path, content in entries:
            archive.writestr(relative_path, content)

    return filename


def _package_entries() -> list[tuple[str, bytes]]:
    entries: list[tuple[str, bytes]] = []
    package_root = ROOT / "xianyu_cli"
    for file_path in sorted(package_root.rglob("*.py")):
        relative_path = file_path.relative_to(ROOT).as_posix()
        entries.append((relative_path, file_path.read_bytes()))
    return entries


def _dist_info_entries() -> list[tuple[str, bytes]]:
    entries = [
        (f"{DIST_INFO}/METADATA", _metadata_text().encode("utf-8")),
        (f"{DIST_INFO}/WHEEL", _wheel_text().encode("utf-8")),
    ]

    entry_points = _entry_points_text()
    if entry_points:
        entries.append((f"{DIST_INFO}/entry_points.txt", entry_points.encode("utf-8")))

    return entries


def _metadata_text() -> str:
    lines = [
        "Metadata-Version: 2.1",
        f"Name: {NAME}",
        f"Version: {VERSION}",
    ]

    if SUMMARY:
        lines.append(f"Summary: {SUMMARY}")
    if REQUIRES_PYTHON:
        lines.append(f"Requires-Python: {REQUIRES_PYTHON}")

    for dependency in DEPENDENCIES:
        lines.append(f"Requires-Dist: {dependency}")

    lines.append("")
    return "\n".join(lines)


def _wheel_text() -> str:
    return "\n".join(
        [
            "Wheel-Version: 1.0",
            "Generator: xianyu_build_backend",
            "Root-Is-Purelib: true",
            "Tag: py3-none-any",
            "",
        ]
    )


def _entry_points_text() -> str:
    if not SCRIPTS:
        return ""

    lines = ["[console_scripts]"]
    for name, target in SCRIPTS.items():
        lines.append(f"{name} = {target}")
    lines.append("")
    return "\n".join(lines)


def _record_rows(entries: Iterable[tuple[str, bytes]]) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for relative_path, content in entries:
        digest = hashlib.sha256(content).digest()
        hash_value = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
        rows.append((relative_path, f"sha256={hash_value}", str(len(content))))

    rows.append((f"{DIST_INFO}/RECORD", "", ""))
    return rows


def _record_bytes(rows: Iterable[tuple[str, str, str]]) -> bytes:
    from io import StringIO

    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator=os.linesep)
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8")
