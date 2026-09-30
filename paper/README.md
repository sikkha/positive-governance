> **Publication note (added when this repository was prepared; the rest of this README is the paper workspace's original text).**
> This is the LaTeX source of the ABM paper, identical to tag `level13b-revision-complete` (commit `c708116`) of the paper's own local git history. The history is not included in this repository and is archived separately by the author. Since that revision the manuscript covers Levels 1.2, 1.2b, 1.3 **and** 1.3b. The layout line "`00_abstract.tex ... 11_reproducibility.tex`" should read `13_reproducibility.tex`.
> **Evidence is not bundled here.** Every figure is a byte-copy from `../abm/outputs/level1{2,2b,3,3b}_figures/` (see `dev_mem/figure_manifest.md`). Every numerical claim is mapped in `claim_evidence_manifest.csv` / `dev_mem/evidence_ledger.md` to a file under `../abm/outputs/` (the paths there are relative to the ABM root). The "separate, read-only repository" mentioned below is `../abm/` in this repository.
> Build with TeX Live (pdflatex, biber ≥ 2.19 matching your biblatex, latexmk, and the `lmodern`, `microtype`, `cleveref`, `adjustbox` and `underscore` packages): `make verify` (verified: 93 pages, `=== VERIFY PASSED ===`). `make figures` also needs `pdftoppm`. It calls the non-existent `scripts/make_conceptual_diagram_check.py`, which is harmless (`|| true`). The compiled PDF and `build/` are not tracked.
> `dev_mem/` holds the paper's development records (status logs, evidence ledger, reference audit, figure manifest). Local absolute paths there are replaced by `<LOCAL_PATH>`.

---

# abm_governance_paper

LaTeX source for *From Institutional Emergence to Phenotypic Continuity: An
Outcome-Blind Agent-Based Search for Recurrent Governance Forms*, documenting
the Level 1.2 and Level 1.2b experiments from the companion `abm_governance`
model project.

This repository is a standalone paper workspace. It does not contain, and
does not modify, the source model repository (`abm_governance_level1.0`),
which remains scientifically frozen; it only copies the specific outputs
(figures, and the numbers recorded in `dev_mem/evidence_ledger.md`) needed
to write this paper.

## Build

```bash
make pdf      # build manuscript.pdf (latexmk if available, else manual pdflatex/biber sequence)
make figures  # regenerate the one originally-authored figure (conceptual_framework)
make verify   # build + check citations/figures/cross-refs/evidence-ledger coverage
make clean    # remove build artifacts
```

Requires `pdflatex`, `biber`, and (optionally) `latexmk` from a standard TeX
Live installation. No absolute paths are used anywhere in the manuscript;
all figure/table paths are relative to the repository root.

## Layout

```
manuscript.tex        top-level document
sections/              main-text section sources (00_abstract.tex ... 11_reproducibility.tex)
appendix/appendix.tex  appendix content
references.bib         BibLaTeX bibliography (biber backend)
figures/main/          main-text figures (curated copies + the one original diagram)
figures/appendix/      appendix figures (curated copies)
tables/                standalone tabular fragments, \input by the sections/appendix
source_data/           small extracted data snippets backing specific tables/figures
scripts/                figure-generation scripts (conceptual_framework.tex, verify_manuscript.py)
build/                  latexmk/pdflatex working directory (gitignored-style scratch)
dev_mem/                paper development log, evidence ledger, reference audit, figure manifest
```

## Provenance

Every figure in `figures/` is either a byte-for-byte copy of an existing
figure from the source model repository's own `outputs/level12_figures/`
or `outputs/level12b_figures/` (see `dev_mem/figure_manifest.md` for the
exact source path of each), or the one originally authored
conceptual-framework diagram (`scripts/conceptual_framework.tex`). Every
central numerical claim in the manuscript is mapped to its exact source
file and field in `dev_mem/evidence_ledger.md`, independently recomputed
from raw JSON output during this paper's own preflight, not merely copied
from prose summaries. `dev_mem/reference_audit.md` records how every
bibliography entry was verified.

## Source model repository (read-only)

The generative model, its full test suite, and every raw experiment output
referenced here live in a separate, read-only repository
(`abm_governance_level1.0` / `abm_governance`), which this paper's own
workspace never modifies. See `dev_mem/paper_status.md` for the full
preflight log and `sections/11_reproducibility.tex` for what is required
to reproduce or extend the results reported here.
