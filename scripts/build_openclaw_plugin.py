from __future__ import annotations

import argparse
import json
import shutil
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist" / "openclaw-plugin"
ARCHIVE_STEM = ROOT / "dist" / "mine-openclaw-plugin"
INCLUDED_PATHS = (
    Path("api.ts"),
    Path("index.ts"),
    Path("openclaw.config.example.jsonc"),
    Path("openclaw.plugin.json"),
    Path("package.json"),
    Path("README.md"),
    Path("SKILL.md"),
    Path("scripts"),
    Path("src"),
)
EXCLUDED_NAMES = {
    ".git",
    ".gitignore",
    ".pytest_cache",
    ".DS_Store",
    "__pycache__",
    "node_modules",
    "tests",
}


def _copy_tree(source_root: Path, relative_path: Path, copied_files: list[Path]) -> None:
    source_path = source_root / relative_path
    if not source_path.exists():
        return
    if source_path.is_dir():
        for child in sorted(source_path.rglob("*")):
            child_relative = child.relative_to(source_root)
            if any(part in EXCLUDED_NAMES for part in child_relative.parts):
                continue
            if child.is_dir():
                (DIST_DIR / child_relative).mkdir(parents=True, exist_ok=True)
                continue
            target = DIST_DIR / child_relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(child, target)
            copied_files.append(target)
        return
    target = DIST_DIR / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target)
    copied_files.append(target)


def build_plugin_dist() -> list[Path]:
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    copied_files: list[Path] = []
    for relative_path in INCLUDED_PATHS:
        _copy_tree(ROOT, relative_path, copied_files)

    manifest = {
        "source": str(ROOT.resolve()),
        "dist": str(DIST_DIR.resolve()),
        "files": [str(path.relative_to(DIST_DIR)).replace("\\", "/") for path in copied_files],
        "included_paths": [str(path).replace("\\", "/") for path in INCLUDED_PATHS],
        "excluded_names": sorted(EXCLUDED_NAMES),
    }
    (DIST_DIR / "release-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    copied_files.append(DIST_DIR / "release-manifest.json")
    return copied_files


def build_archives() -> tuple[Path, Path]:
    zip_path = Path(
        shutil.make_archive(
            str(ARCHIVE_STEM),
            "zip",
            root_dir=str(DIST_DIR.parent),
            base_dir=DIST_DIR.name,
        )
    )
    tar_path = ARCHIVE_STEM.with_suffix(".tar.gz")
    with tarfile.open(tar_path, "w:gz") as handle:
        handle.add(DIST_DIR, arcname=DIST_DIR.name)
    return zip_path, tar_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the minimal Mine OpenClaw plugin distribution bundle.")
    parser.add_argument("--no-archive", action="store_true", help="Skip .zip and .tar.gz archive generation.")
    args = parser.parse_args()

    copied_files = build_plugin_dist()
    print(json.dumps({"dist": str(DIST_DIR.resolve()), "files": len(copied_files)}, ensure_ascii=False))
    if args.no_archive:
        return 0
    zip_path, tar_path = build_archives()
    print(json.dumps({"zip": str(zip_path.resolve()), "tar_gz": str(tar_path.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
