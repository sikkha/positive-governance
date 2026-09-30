"""Archive-protection guard for experiment scripts (added for the public
research archive; does not touch any model or analysis code).

Every experiment script writes its results relative to the current working
directory (``outputs/<stage>/``). When the working directory is the archive
root of this repository -- recognised by the marker file
``ARCHIVED_OUTPUTS.sha256`` -- a re-run would overwrite the archived evidence
that the dissertation and paper cite. The guard stops that unless

* an explicit output location outside ``outputs/`` is given on the command
  line (``--out``, ``--out-dir`` or ``--out-root``, for scripts that accept
  one), or
* ``ABM_ALLOW_ARCHIVE_OVERWRITE=1`` is set deliberately.

The recommended way to re-run any experiment is the isolating runner::

    python experiments/run_isolated.py <script>.py --out-dir /path/to/rerun

which executes the unmodified script in a scratch workspace.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

MARKER = "ARCHIVED_OUTPUTS.sha256"
OUT_FLAGS = ("--out", "--out-dir", "--out-root")


def _explicit_out_paths(argv: list[str]) -> list[str]:
    paths = []
    for i, a in enumerate(argv):
        for flag in OUT_FLAGS:
            if a == flag and i + 1 < len(argv):
                paths.append(argv[i + 1])
            elif a.startswith(flag + "="):
                paths.append(a.split("=", 1)[1])
    return paths


def is_archive_root(cwd: Path) -> bool:
    return (cwd / MARKER).is_file()


def check(cwd: Path, argv: list[str], env: dict) -> str | None:
    """Return a refusal message, or None if the run may proceed."""
    if not is_archive_root(cwd) or env.get("ABM_ALLOW_ARCHIVE_OVERWRITE") == "1":
        return None
    archive = (cwd / "outputs").resolve()
    outs = _explicit_out_paths(argv)
    if outs and all(archive not in (cwd / p).resolve().parents and (cwd / p).resolve() != archive for p in outs):
        return None
    return (
        "Refusing to run: the working directory holds the ARCHIVED experiment outputs "
        f"({MARKER} present) and this script writes into outputs/ in place.\n"
        "Re-run in isolation instead:\n"
        f"    python experiments/run_isolated.py {Path(argv[0]).name if argv else '<script>.py'} --out-dir /tmp/abm_rerun\n"
        "or set ABM_ALLOW_ARCHIVE_OVERWRITE=1 if you really intend to replace the archive."
    )


def refuse_archive_overwrite() -> None:
    msg = check(Path.cwd(), list(sys.argv), dict(os.environ))
    if msg:
        sys.stderr.write(msg + "\n")
        raise SystemExit(2)
