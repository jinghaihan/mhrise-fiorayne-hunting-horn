#!/usr/bin/env python3

import argparse
import hashlib
import re
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MOD_NAME = "Fiorayne Hunting Horn"
MOD_ROOT = ROOT / "mod" / MOD_NAME
VERSION_PATH = ROOT / "VERSION"
EXPECTED_DATA_FILES = 18


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a reproducible Fluffy Mod Manager release archive."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "dist",
        help="Output directory (default: dist)",
    )
    return parser.parse_args()


def read_version() -> str:
    version = VERSION_PATH.read_text(encoding="utf-8").strip()
    if re.fullmatch(r"\d+\.\d+\.\d+", version) is None:
        raise RuntimeError(f"VERSION is not a stable SemVer value: {version}")
    return version


def release_files(version: str) -> list[Path]:
    if not MOD_ROOT.is_dir():
        raise RuntimeError(f"Missing mod directory: {MOD_ROOT}")

    files = sorted(path for path in MOD_ROOT.rglob("*") if path.is_file())
    unsupported = [
        path.relative_to(MOD_ROOT)
        for path in files
        if path.name != "modinfo.ini" and path.suffixes[-2:] != [".user", ".2"]
    ]
    if unsupported:
        raise RuntimeError(f"Unexpected mod files: {unsupported}")

    data_files = [path for path in files if path.suffixes[-2:] == [".user", ".2"]]
    if len(data_files) != EXPECTED_DATA_FILES:
        raise RuntimeError(
            f"Expected {EXPECTED_DATA_FILES} .user.2 files, found {len(data_files)}"
        )

    modinfo = MOD_ROOT / "modinfo.ini"
    expected_version = f"version=v{version}"
    if expected_version not in modinfo.read_text(encoding="utf-8").splitlines():
        raise RuntimeError(f"modinfo.ini does not contain {expected_version}")
    return files


def add_file(archive: zipfile.ZipFile, path: Path) -> None:
    relative = path.relative_to(MOD_ROOT)
    info = zipfile.ZipInfo(f"{MOD_NAME}/{relative.as_posix()}")
    info.date_time = (1980, 1, 1, 0, 0, 0)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, path.read_bytes())


def package(output: Path) -> tuple[Path, Path]:
    version = read_version()
    files = release_files(version)
    output.mkdir(parents=True, exist_ok=True)

    archive_path = output / f"mhrise-fiorayne-hunting-horn-v{version}.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for path in files:
            add_file(archive, path)

    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    checksum_path = archive_path.with_suffix(f"{archive_path.suffix}.sha256")
    checksum_path.write_text(
        f"{digest}  {archive_path.name}\n",
        encoding="utf-8",
    )
    return archive_path, checksum_path


def main() -> None:
    archive, checksum = package(parse_args().output.resolve())
    print(archive)
    print(checksum)


if __name__ == "__main__":
    main()
