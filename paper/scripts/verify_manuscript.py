#!/usr/bin/env python3
"""make verify: post-build checks for the manuscript.

Checks:
  1. build/manuscript.pdf exists (compilation succeeded).
  2. build/manuscript.log has no "LaTeX Warning: Reference ... undefined"
     or "Citation ... undefined" warnings.
  3. Every \\includegraphics path referenced in sections/ or appendix/
     resolves to a file that actually exists in this repository.
  4. Every \\cite/\\parencite/\\textcite/\\citealt key resolves to an entry
     in references.bib, and every references.bib entry is cited at least
     once (no orphan bibliography entries).
  5. A spot-check that a sample of central numerical claims (the
     orientation values named in the task brief) appear in the evidence
     ledger.

Exits non-zero on any failure, printing every problem found (not just the
first).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
problems = []


def check_pdf_exists():
    pdf = BUILD / "manuscript.pdf"
    if not pdf.exists():
        pdf2 = ROOT / "manuscript.pdf"
        if not pdf2.exists():
            problems.append(f"No compiled PDF found at {pdf} or {pdf2}")
            return
    print("[ok] compiled PDF exists")


def check_log_warnings():
    log = BUILD / "manuscript.log"
    if not log.exists():
        problems.append(f"No log file at {log} -- cannot check for undefined refs/citations")
        return
    text = log.read_text(errors="ignore")
    undefined_refs = re.findall(r"LaTeX Warning: Reference `([^']*)' .*undefined", text)
    undefined_cites = re.findall(r"LaTeX Warning: Citation '([^']*)' .*undefined", text)
    undefined_cites += re.findall(r"Package biblatex Warning: .*?entry '([^']*)' not found", text)
    if undefined_refs:
        problems.append(f"Undefined cross-references: {sorted(set(undefined_refs))}")
    else:
        print("[ok] no undefined cross-references")
    if undefined_cites:
        problems.append(f"Undefined citations: {sorted(set(undefined_cites))}")
    else:
        print("[ok] no undefined citations")
    if "Rerun to get" in text or "There were undefined references" in text:
        problems.append("Log indicates a rerun was still required (undefined references/labels remained)")


def check_figures():
    tex_files = list((ROOT / "sections").glob("*.tex")) + list((ROOT / "appendix").glob("*.tex")) + [ROOT / "manuscript.tex"]
    missing = []
    found = 0
    for tf in tex_files:
        text = tf.read_text()
        for m in re.finditer(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", text):
            path = m.group(1)
            candidates = [ROOT / path]
            if not path.endswith((".pdf", ".png", ".jpg", ".jpeg")):
                candidates += [ROOT / (path + ext) for ext in (".pdf", ".png")]
            if not any(c.exists() for c in candidates):
                missing.append((tf.name, path))
            else:
                found += 1
    if missing:
        for tf, path in missing:
            problems.append(f"Missing figure file referenced in {tf}: {path}")
    else:
        print(f"[ok] all {found} \\includegraphics references resolve to local files")


def check_citations():
    bib_text = (ROOT / "references.bib").read_text()
    bib_keys = set(re.findall(r"@\w+\{([^,]+),", bib_text))

    tex_files = list((ROOT / "sections").glob("*.tex")) + list((ROOT / "appendix").glob("*.tex"))
    cited_keys = set()
    for tf in tex_files:
        text = tf.read_text()
        for m in re.finditer(r"\\(?:cite|parencite|textcite|citealt|citep|citet|autocite)\*?(?:\[[^\]]*\])*\{([^}]+)\}", text):
            for key in m.group(1).split(","):
                cited_keys.add(key.strip())

    unresolved = cited_keys - bib_keys
    orphans = bib_keys - cited_keys
    if unresolved:
        problems.append(f"Citation keys with no references.bib entry: {sorted(unresolved)}")
    else:
        print(f"[ok] all {len(cited_keys)} cited keys resolve in references.bib")
    if orphans:
        problems.append(f"references.bib entries never cited in the manuscript: {sorted(orphans)}")
    else:
        print(f"[ok] all {len(bib_keys)} references.bib entries are cited at least once")


def check_evidence_ledger_coverage():
    ledger = (ROOT / "dev_mem" / "evidence_ledger.md").read_text()
    orientation_values = [
        "1,320", "576", "326", "161", "89", "384", "245", "86", "53",
        "0.84", "0.48", "0%", "87.5%",
    ]
    missing = [v for v in orientation_values if v not in ledger]
    if missing:
        problems.append(f"Evidence ledger missing coverage for orientation values: {missing}")
    else:
        print("[ok] evidence ledger covers every task-brief orientation value")


def main():
    check_pdf_exists()
    check_log_warnings()
    check_figures()
    check_citations()
    check_evidence_ledger_coverage()

    if problems:
        print("\n=== VERIFY FAILED ===")
        for p in problems:
            print(f" - {p}")
        sys.exit(1)
    print("\n=== VERIFY PASSED ===")


if __name__ == "__main__":
    main()
