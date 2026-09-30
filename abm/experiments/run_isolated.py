#!/usr/bin/env python3
"""Run any experiment script without touching the archived outputs.

    python experiments/run_isolated.py SCRIPT.py --out-dir DIR [--no-archived-inputs] [-- SCRIPT_ARGS...]

What it does (the experiment script itself is executed unmodified):

1. Creates DIR (must not lie inside this repository's archived ``outputs/``).
2. Unless ``--no-archived-inputs`` is given, copies the archived ``outputs/``
   tree to ``DIR/outputs`` so that scripts which read upstream stage results
   (e.g. Level 1.2b stage l3 reads l1 and l2) find them.
3. Runs the script with working directory DIR, the repository root and
   ``experiments/`` on ``sys.path``, and ``sys.argv = [SCRIPT] + SCRIPT_ARGS``.
   All relative writes therefore land in ``DIR/outputs/<stage>/``.
4. Writes ``DIR/rerun_manifest.json`` classifying every file under
   ``DIR/outputs`` as new, modified or unchanged relative to the archive,
   and re-verifies the archive checksums (``ARCHIVED_OUTPUTS.sha256``).

A re-run reproduces an archived result only where the manifest shows the
stage's files as "unchanged"; "modified" files must be compared with care
(figures, for example, differ at the rendering level across matplotlib
versions even when their input data are identical).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import runpy
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "outputs"
MANIFEST = ROOT / "ARCHIVED_OUTPUTS.sha256"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest() -> dict[str, str]:
    out = {}
    for line in MANIFEST.read_text().splitlines():
        if line.strip():
            digest, rel = line.split(None, 1)
            out[rel.strip()] = digest
    return out


def verify_archive() -> list[str]:
    bad = []
    for rel, digest in load_manifest().items():
        p = ROOT / rel
        if not p.is_file() or sha256(p) != digest:
            bad.append(rel)
    return bad


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    extra: list[str] = []
    if "--" in argv:
        i = argv.index("--")
        argv, extra = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("script", help="experiment script, e.g. level13b_stage6_history_erasure.py")
    ap.add_argument("--out-dir", required=True, help="scratch directory for this re-run")
    ap.add_argument("--no-archived-inputs", action="store_true", help="do not copy archived outputs as inputs")
    a = ap.parse_args(argv)

    script = Path(a.script)
    if not script.is_file():
        script = ROOT / "experiments" / a.script
    script = script.resolve()
    if not script.is_file():
        ap.error(f"script not found: {a.script}")
    out = Path(a.out_dir).resolve()
    if out == ARCHIVE or ARCHIVE in out.parents or out == ROOT:
        ap.error("--out-dir must not be the repository root or lie inside the archived outputs/")
    out.mkdir(parents=True, exist_ok=True)
    if not a.no_archived_inputs and not (out / "outputs").exists():
        shutil.copytree(ARCHIVE, out / "outputs")

    archived = load_manifest()
    old_cwd, old_argv, old_path = Path.cwd(), sys.argv[:], sys.path[:]
    t0 = time.time()
    status = 0
    try:
        os.chdir(out)
        sys.path[:0] = [str(ROOT), str(ROOT / "experiments")]
        sys.argv = [str(script)] + extra
        try:
            runpy.run_path(str(script), run_name="__main__")
        except SystemExit as e:  # scripts may call sys.exit(main())
            status = int(e.code or 0) if not isinstance(e.code, str) else 1
    finally:
        os.chdir(old_cwd)
        sys.argv, sys.path[:] = old_argv, old_path

    files = {}
    for p in sorted((out / "outputs").rglob("*")) if (out / "outputs").exists() else []:
        if not p.is_file():
            continue
        rel = str(p.relative_to(out))
        d = sha256(p)
        if rel in archived:
            files[rel] = "unchanged_vs_archive" if d == archived[rel] else "modified_vs_archive"
        else:
            files[rel] = "new"
    bad = verify_archive()
    report = {"script": str(script.relative_to(ROOT)), "args": extra, "exit_status": status,
              "wall_seconds": round(time.time() - t0, 1), "out_dir": str(out),
              "files_new_or_modified": {k: v for k, v in files.items() if v != "unchanged_vs_archive"},
              "n_files_unchanged_vs_archive": sum(v == "unchanged_vs_archive" for v in files.values()),
              "archive_checksums_intact": not bad, "archive_checksum_failures": bad}
    (out / "rerun_manifest.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ("script", "exit_status", "wall_seconds", "archive_checksums_intact")}))
    print(f"{len(report['files_new_or_modified'])} new/modified file(s); manifest: {out / 'rerun_manifest.json'}")
    return 3 if bad else status


if __name__ == "__main__":
    raise SystemExit(main())
