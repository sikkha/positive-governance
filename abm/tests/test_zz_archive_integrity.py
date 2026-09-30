"""Runs last (alphabetical order): after the whole suite, every archived output
file must still match ARCHIVED_OUTPUTS.sha256 and no file may have been added
to the archived outputs/ tree (added for the public research archive)."""
from __future__ import annotations

import hashlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_archived_outputs_unchanged_after_suite():
    lines = (REPO / "ARCHIVED_OUTPUTS.sha256").read_text().splitlines()
    manifest = {rel.strip(): d for d, rel in (l.split(None, 1) for l in lines if l.strip())}
    assert manifest, "empty manifest"
    changed = [rel for rel, d in manifest.items() if hashlib.sha256((REPO / rel).read_bytes()).hexdigest() != d]
    present = {str(p.relative_to(REPO)) for p in (REPO / "outputs").rglob("*") if p.is_file()}
    added = sorted(present - set(manifest))
    missing = sorted(set(manifest) - present)
    assert not changed and not added and not missing, {"changed": changed, "added": added, "missing": missing}
