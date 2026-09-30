"""Focused checks that tests and experiments cannot overwrite archived evidence
(added for the public research archive)."""
from __future__ import annotations

import ast
import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
EXPERIMENTS = REPO / "experiments"
sys.path.insert(0, str(EXPERIMENTS))
import _archive_guard as guard  # noqa: E402


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _manifest() -> dict[str, str]:
    lines = (REPO / "ARCHIVED_OUTPUTS.sha256").read_text().splitlines()
    return {rel.strip(): d for d, rel in (l.split(None, 1) for l in lines if l.strip())}


def test_session_runs_in_scratch_workspace():
    if os.environ.get("ABM_TESTS_IN_PLACE") == "1":
        pytest.skip("isolation disabled explicitly")
    assert Path.cwd().resolve() != REPO.resolve()
    assert (Path.cwd() / "outputs").is_dir() and not (Path.cwd() / "outputs").is_symlink()
    assert REPO / "outputs" not in [(Path.cwd() / "outputs").resolve()]


def test_every_experiment_main_is_guarded():
    unguarded = []
    for f in sorted(EXPERIMENTS.glob("*.py")):
        if f.name in ("_archive_guard.py", "run_isolated.py"):
            continue
        src = f.read_text()
        tree = ast.parse(src)
        for node in tree.body:
            if isinstance(node, ast.If) and "__main__" in ast.unparse(node.test):
                first_line = src.splitlines()[node.body[0].lineno - 1]
                if "refuse_archive_overwrite()" not in first_line:
                    unguarded.append(f.name)
    assert not unguarded, unguarded


def test_guard_refuses_in_archive_root_and_allows_elsewhere(tmp_path):
    (tmp_path / guard.MARKER).write_text("x")
    (tmp_path / "outputs").mkdir()
    assert guard.check(tmp_path, ["x.py"], {}) is not None                      # archive root: refused
    assert guard.check(tmp_path, ["x.py", "--out", "outputs/a"], {}) is not None  # explicit but inside archive: refused
    assert guard.check(tmp_path, ["x.py", "--out", str(tmp_path / "elsewhere")], {}) is None
    assert guard.check(tmp_path, ["x.py", "--out-dir=/tmp/somewhere"], {}) is None
    assert guard.check(tmp_path, ["x.py"], {"ABM_ALLOW_ARCHIVE_OVERWRITE": "1"}) is None
    (tmp_path / guard.MARKER).unlink()
    assert guard.check(tmp_path, ["x.py"], {}) is None                          # not the archive root


def test_guard_blocks_real_script_before_any_work():
    # the guard is the first statement of __main__, so nothing is imported or run past it
    r = subprocess.run([sys.executable, "experiments/level13b_stage7_model_comparison.py"], cwd=REPO,
                       capture_output=True, text=True, timeout=120,
                       env={**{k: v for k, v in os.environ.items() if k != "ABM_ALLOW_ARCHIVE_OVERWRITE"}, "PYTHONPATH": str(REPO)})
    assert r.returncode == 2, r.stderr
    assert "Refusing to run" in r.stderr


def test_isolated_runner_writes_figures_outside_archive(tmp_path):
    before = {rel: d for rel, d in _manifest().items() if rel.startswith("outputs/level13b_figures/")}
    r = subprocess.run([sys.executable, str(EXPERIMENTS / "run_isolated.py"), "make_level13b_visualizations.py",
                        "--out-dir", str(tmp_path / "rerun")], cwd=REPO, capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (tmp_path / "rerun" / "rerun_manifest.json").is_file()
    assert any((tmp_path / "rerun" / "outputs" / "level13b_figures").glob("*.png"))
    for rel, d in before.items():
        assert _sha(REPO / rel) == d, rel


def test_isolated_runner_rejects_archive_as_out_dir():
    r = subprocess.run([sys.executable, str(EXPERIMENTS / "run_isolated.py"), "make_level13b_visualizations.py",
                        "--out-dir", str(REPO / "outputs" / "x")], cwd=REPO, capture_output=True, text=True, timeout=60)
    assert r.returncode != 0 and "must not" in r.stderr
