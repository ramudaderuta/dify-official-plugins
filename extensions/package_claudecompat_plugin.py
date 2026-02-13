#!/usr/bin/env python3
import argparse
import zipfile
from pathlib import Path

EXCLUDE_DIRS = {"__pycache__", ".pytest_cache"}
EXCLUDE_FILES = {"uv.lock"}
EXCLUDE_EXTS = {".pyc"}


def should_skip(path: Path, rel: Path) -> bool:
    if any(part in EXCLUDE_DIRS for part in rel.parts):
        return True
    if path.name in EXCLUDE_FILES:
        return True
    if path.suffix in EXCLUDE_EXTS:
        return True
    return False


def package_plugin(source_dir: Path, output_path: Path) -> None:
    if output_path.exists():
        output_path.unlink()

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in source_dir.rglob("*"):
            rel = path.relative_to(source_dir)
            if should_skip(path, rel):
                continue
            if path.is_dir():
                continue
            zf.write(path, rel.as_posix())


def main() -> int:
    parser = argparse.ArgumentParser(description="Package claudecompat_dify_model plugin.")
    parser.add_argument(
        "--source",
        default="/home/build/code/easycheck-linux/extensions/claudecompat_dify_model",
        help="Plugin source directory",
    )
    parser.add_argument(
        "--output",
        default="/home/build/code/easycheck-linux/extensions/claudecompat_dify_model.difypkg",
        help="Output .difypkg path",
    )
    args = parser.parse_args()

    source_dir = Path(args.source).resolve()
    output_path = Path(args.output).resolve()

    if not source_dir.exists():
        raise SystemExit(f"source dir not found: {source_dir}")

    package_plugin(source_dir, output_path)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
