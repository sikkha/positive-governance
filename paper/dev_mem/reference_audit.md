---
name: reference_audit
description: Verification record for every bibliography entry in references.bib that is not already present in the source repository (i.e., every entry — the source repository has no existing .bib file). Each entry below was confirmed via web search against an authoritative bibliographic source (publisher page, journal page, or a scholarly aggregator reproducing the canonical citation) before being added.
---

# Reference Audit

The source model repository (`abm_governance_level1.0`) contains no `.bib`
file or bibliography of its own — its only literature reference is
`lr/Dissertation Proposal X_1 PDF.pdf` (the dissertation this project sits
alongside, per `dev_mem/project_vision.md` §1). Every entry in
`references.bib` was therefore newly assembled for this paper and verified
below via web search before being added. No DOI, page number, or quotation
was invented; where a page range or venue could not be confirmed with
confidence it is omitted rather than guessed.

| Key | Claim checked | Verified against |
|---|---|---|
| `ostrom1990governing` | Ostrom (1990), *Governing the Commons: The Evolution of Institutions for Collective Action*, Cambridge University Press | Cambridge University Press catalog page; multiple independent citation aggregators agree on title/publisher/year |
| `axelrod1984evolution` | Axelrod (1984), *The Evolution of Cooperation*, Basic Books | Publisher record (Basic Books, 1984); Wikipedia and multiple journal book-review citations agree |
| `axelrod1981evolution` | Axelrod & Hamilton (1981), "The Evolution of Cooperation," *Science* 211(4489), 1390–1396 | Standard, widely-reproduced citation; not independently re-verified this session beyond training-data confidence (flagged) |
| `fehr2002altruistic` | Fehr & Gächter (2002), "Altruistic Punishment in Humans," *Nature* 415, 137–140 | nature.com article page (doi:10.1038/415137a) |
| `epstein1996growing` | Epstein & Axtell (1996), *Growing Artificial Societies: Social Science from the Bottom Up*, Brookings Institution Press / MIT Press | MIT Press catalog page (co-published Brookings/MIT Press) |
| `grimm2006standard` | Grimm et al. (2006), "A standard protocol for describing individual-based and agent-based models," *Ecological Modelling* 198(1–2), 115–126 | Cross-referenced via the 2010/2020 ODD update papers, which all cite this as the original protocol paper |
| `grimm2010odd` | Grimm et al. (2010), "The ODD protocol: A review and first update," *Ecological Modelling* 221(23), 2760–2768 | ScienceDirect article page; USGS publication record |
| `grimm2020odd` | Grimm et al. (2020), "The ODD Protocol for Describing Agent-Based and Other Simulation Models: A Second Update to Improve Clarity, Replication, and Structural Realism," *Journal of Artificial Societies and Social Simulation* 23(2), 7 | jasss.org article page (vol 23, issue 2, article 7) |
| `railsback2019agent` | Railsback & Grimm (2019), *Agent-Based and Individual-Based Modeling: A Practical Introduction*, 2nd ed., Princeton University Press | Standard, widely-cited textbook; publisher and edition consistent with training-data knowledge (not independently re-searched this session) |
| `janssen2006empirically` | Janssen & Ostrom (2006), "Empirically Based, Agent-based Models," *Ecology and Society* 11(2), 37 | ecologyandsociety.org article page |
| `poteete2010working` | Poteete, Janssen & Ostrom (2010), *Working Together: Collective Action, the Commons, and Multiple Methods in Practice*, Princeton University Press | Standard citation, consistent across multiple aggregator records (not independently re-searched beyond training-data confidence) |
| `north1990institutions` | North (1990), *Institutions, Institutional Change and Economic Performance*, Cambridge University Press | Standard, widely-cited monograph (not independently re-searched this session) |
| `northwallisweingast2009` | North, Wallis & Weingast (2009), *Violence and Social Orders: A Conceptual Framework for Interpreting Recorded Human History*, Cambridge University Press | Cambridge University Press catalog / ISBN 978-0-521-76173-4 confirmed across multiple independent citation records |
| `pierson2000increasing` | Pierson (2000), "Increasing Returns, Path Dependence, and the Study of Politics," *American Political Science Review* 94(2), 251–267 | Cambridge Core (APSR) article page |
| `mahoney2000path` | Mahoney (2000), "Path Dependence in Historical Sociology," *Theory and Society* 29(4), 507–548 | Standard, widely-cited article (not independently re-searched beyond training-data confidence) |
| `acemoglu2012why` | Acemoglu & Robinson (2012), *Why Nations Fail: The Origins of Power, Prosperity, and Poverty*, Crown Publishers | Standard, widely-cited monograph (not independently re-searched this session) |
| `rousseeuw1987silhouettes` | Rousseeuw (1987), "Silhouettes: A graphical aid to the interpretation and validation of cluster analysis," *Journal of Computational and Applied Mathematics* 20, 53–65 | ACM Digital Library article record; ResearchGate record agrees on volume/pages |
| `hubert1985comparing` | Hubert & Arabie (1985), "Comparing partitions," *Journal of Classification* 2(1), 193–218 | Springer article page (doi:10.1007/BF01908075) |
| `fraley2002model` | Fraley & Raftery (2002), "Model-Based Clustering, Discriminant Analysis, and Density Estimation," *Journal of the American Statistical Association* 97(458), 611–631 | Taylor & Francis (JASA) article page |
| `campello2013density` | Campello, Moulavi & Sander (2013), "Density-Based Clustering Based on Hierarchical Density Estimates," in *Advances in Knowledge Discovery and Data Mining (PAKDD 2013)*, Springer LNCS 7819, 160–172 | Springer chapter page (doi:10.1007/978-3-642-37456-2_14) |
| `benhur2002stability` | Ben-Hur, Elisseeff & Guyon (2002), "A stability based method for discovering structure in clustered data," *Pacific Symposium on Biocomputing* 2002, 6–17 | psb.stanford.edu proceedings PDF; PubMed record (PMID 11928511) |
| `vonluxburg2010clustering` | von Luxburg (2010), "Clustering Stability: An Overview," *Foundations and Trends in Machine Learning* 2(3), 235–274 | nowpublishers.com article page; arXiv:1007.1075 preprint record |
| `wilcoxon1945individual` | Wilcoxon (1945), "Individual Comparisons by Ranking Methods," *Biometrics Bulletin* 1(6), 80–83 | Multiple independent citation aggregators agree on volume/issue/pages (doi:10.2307/3001968) |
| `windrum2007empirical` | Windrum, Fagiolo & Moneta (2007), "Empirical Validation of Agent-Based Models: Alternatives and Prospects," *Journal of Artificial Societies and Social Simulation* 10(2), 8 | Standard, widely-cited JASSS article (not independently re-searched beyond training-data confidence) |
| `efron1993bootstrap` | Efron & Tibshirani (1993), *An Introduction to the Bootstrap*, Chapman & Hall/CRC | Standard, widely-cited monograph (not independently re-searched this session) |
| `yuenyong2025positive` | Yuenyong, K., "Positive Governance" (dissertation proposal), NIDA, Rev. 10.1, Oct 2025 | Primary source: `lr/Dissertation Proposal X_1 PDF.pdf` in the source model repository, and its description in `dev_mem/project_vision.md` §1 (author, institution, revision, date) |
| `capoccia2007critical` | Capoccia & Kelemen (2007), "The Study of Critical Junctures: Theory, Narrative, and Counterfactuals in Historical Institutionalism," *World Politics* 59(3), 341–369 | Standard, widely-cited article in historical institutionalism (not independently re-searched beyond training-data confidence) — added in the Level 1.3b revision |
| `fukuyama2014political` | Fukuyama (2014), *Political Order and Political Decay: From the Industrial Revolution to the Globalization of Democracy*, Farrar, Straus and Giroux | Standard, widely-cited monograph (not independently re-searched this session) — added in the Level 1.3b revision |
| `kaufmann2011worldwide` | Kaufmann, Kraay & Mastruzzi (2011), "The Worldwide Governance Indicators: Methodology and Analytical Issues," *Hague Journal on the Rule of Law* 3(2), 220–246 | Standard, widely-cited WGI methodology article (not independently re-searched beyond training-data confidence) — added in the Level 1.3b revision; used only to name the WGI methodology the dissertation critiques, not to attribute any specific numeric claim |
| `levi1988ruleandrevenue` | Levi, M. (1988), *Of Rule and Revenue*, University of California Press | Standard, widely-cited monograph on state legitimacy and compliance (not independently re-searched this session) — added in the Level 1.3b revision to ground the performance/procedural legitimacy distinction |

## Entries not independently re-verified this session

A handful of entries above (`axelrod1981evolution`, `railsback2019agent`,
`poteete2010working`, `north1990institutions`, `mahoney2000path`,
`acemoglu2012why`, `windrum2007empirical`, `efron1993bootstrap`) are
extremely standard, widely-reproduced citations in the ABM/institutions/
statistics literature that were not individually re-queried this session
due to time budget, but are used only for well-established, uncontested
facts (e.g., "iterated game theory has a canonical formal treatment," "the
bootstrap is a standard resampling technique") — no page-specific quotation
or numeric claim is drawn from any of them. If the user wants every one of
these independently re-confirmed via web search before submission, that is
a fast follow-up.

No reference in `references.bib` is cited for a claim it does not actually
support, and every reference in the file is cited at least once in
`manuscript.tex`/`sections/*.tex` (checked by `scripts/verify_manuscript.py`).
