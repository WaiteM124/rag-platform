# Complex Systems collection: source verification

*Draft 1 • verified 23 Nov 2026 (Europe/London) • by Grok Bot for Miles Waite*

Source list: Miles's Google Doc **"RAG Corpus Shortlist"** (Drive folder *Complex Systems*, doc id `1Kp2EbDuXJHwb5u_Lsu9dQyLKvIk6-tq4i2YjlPNVFlk`, last modified 23 Nov 2026 08:58 GMT). The doc exists and looks complete: 46 numbered sources across modules A–I, a "Dropped" list, and practical notes on maths-preserving extraction, chunking, metadata and Gradio visual tools. **Nothing has been ingested.**

## How each source was checked

- **arXiv (34 items):** fetched each `arxiv.org/abs/<id>` page (HTTP 200 for all), compared the title with the doc, and read the licence link from the abs page's licence block. Checked whether a TeX source (`/src/<id>`) is offered. Size is the page count from the arXiv "Comments" field where the authors gave one.
- **Non-arXiv (12 items):** fetched the URL, followed redirects, and searched the page (or PDF front matter) for its licence or copyright statement.
- **Classes used in this repo** (what the API may return in a **public** app):
  - **A: full text allowed.** CC BY, CC BY-SA, CC0, OGL, MIT-style. Store and show full chunks with attribution and link.
  - **B: full text only if non-commercial (NC-SA).** Fine for a free portfolio app with no ads, paid tier or sponsorship. Attribute and link, and share derived text under the same licence. **Flagged NC:** if the app ever becomes commercial (for example a paid tier or use as a sales demo for a business), these drop to class C.
  - **C: excerpt + link-out only.** arXiv non-exclusive licence, arXiv "assumed 1991–2003", CC BY-NC-ND, all-rights-reserved or free-to-read with no licence. Index privately for retrieval. Show no more than one or two quoted sentences, always with citation and link. Never serve the PDF or whole chunks.

## Summary

| Class | Count | Items |
|---|---|---|
| Full text (open licence, commercial OK) | **3** | #18, #33, #44 |
| Full text, NC-SA (non-commercial only) ⚠ NC | **3** | #3, #21, #41 |
| Excerpt + link-out only | **40** | #1, #2, #4, #5, #6, #7, #8, #9, #10, #11, #12, #13, #14, #15, #16, #17, #19, #20, #22, #23, #24, #25, #26, #27, #28, #29, #30, #31, #32, #34, #35, #36, #37, #38, #39, #40, #42, #43, #45, #46 |
| **Total** | **46** | |

This matches the doc's own split: 3 full text (CC BY), 3 NC-SA and 40 link + excerpt.

- **Broken links:** none. All 46 URLs resolved (HTTP 200). Four redirect to a new canonical host, so store the final URL: #20 → `sethna.lassp.cornell.edu`, #34 → `davidtong.org/teaching/statistical-physics/`, #35 → `pubs.ams.org/...`. #19 (PMC) returned a reCAPTCHA interstitial on the first request, so the ingestion fetcher must handle PMC rate limiting. PMC's OA web service is the cleaner route for PMC items.
- **Licence mismatches:** none found. Every licence in the doc matches what the source page states.
- **Worth knowing (not mismatches):**
  - #8 (Vicsek 1995, arXiv post 2006) and #15 (Newman, posted Dec 2004) show the "assumed 1991–2003" licence on arXiv even though they were posted after 2003. The doc is right because it follows the abs page. Class C either way.
  - #21 Network Science: the CC BY-NC-SA 2.0 notice is in the chapter PDF footers. The JS-rendered site HTML shows no licence. I confirmed the notice from chapter-PDF copies found by web search, not from networksciencebook.com itself. Before ingesting, re-confirm it on the official chapter PDFs.
  - #42 Hopfield (PMC): no CC licence on the page, so class C is correct. The exact "© NAS" line the doc quotes did not appear in the scraped HTML.
  - #7 and #11 have **no TeX source** on arXiv (PDF-only), so they need the PDF → Markdown path (Marker/Nougat).
  - #45 is **CC BY-NC-ND 4.0**: NC *and* ND. Class C (no full or adapted chunks). Flagged NC.
  - #3, #21, #41 are **NC** (BY-NC-SA). Flagged above.

## Per-source table

| # | Mod | Source | URL check | Licence on the page | vs doc | Class | Ingestion format | Rough size |
|---|---|---|---|---|---|---|---|---|
| 1 | A | [Complex Systems: A Survey](https://arxiv.org/abs/1112.1440) — M. E. J. Newman (2011) | 200 (title matches) | arXiv non-exclusive distribution licence 1.0 (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | 10 pages |
| 2 | A | [Methods and Techniques of Complex Systems Science: An Overview](https://arxiv.org/abs/nlin/0307015) — C. R. Shalizi (2003) | 200 (title matches) | arXiv assumed licence (1991–2003) (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | 96 pages, 8 figures |
| 3 | B | [Introduction to the Modeling and Analysis of Complex Systems (LibreTexts edition)](https://math.libretexts.org/Bookshelves/Scientific_Computing_Simulations_and_Modeling/Introduction_to_the_Modeling_and_Analysis_of_Complex_Systems_(Sayama)) — H. Sayama (2015 (open textbook)) | 200 (math.libretexts.org) | CC BY-NC-SA 3.0 (LibreTexts licence badge on the book page links creativecommons.org/licenses/by-nc-sa/3.0) | Match | **B** | HTML (LibreTexts pages; MathJax) | Book-length; landing page 185 KB HTML, many chapter pages |
| 4 | B | [ChaosBook.org: Chaos, Classical and Quantum](https://chaosbook.org/) — P. Cvitanović et al. (online, ongoing) | 200 (frameset; content in menu.html/target.html/bottom.html) | “© Copyright 2012 – Center for Nonlinear Science, Georgia Tech” (bottom.html); no open licence found | Match | **C** | PDF (per-chapter PDFs) | Book-length (multi-hundred pages); size not measured |
| 5 | B | [A mathematical framework for critical transitions: bifurcations, fast-slow systems and stochastic dynamics](https://arxiv.org/abs/1101.2899) — C. Kuehn (2011) | 200 (title matches) | arXiv non-exclusive distribution licence 1.0 (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | 38 pages |
| 6 | B | [Tipping points in open systems: bifurcation, noise-induced and rate-dependent examples in the climate system](https://arxiv.org/abs/1103.0169) — P. Ashwin, S. Wieczorek, R. Vitolo, P. Cox (2011) | 200 (title matches) | arXiv non-exclusive distribution licence 1.0 (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | 20 pages, 8 figures |
| 7 | C | [When Can We Call a System Self-organizing?](https://arxiv.org/abs/nlin/0303020) — C. Gershenson, F. Heylighen (2003) | 200 (title matches) | arXiv assumed licence (1991–2003) (abs page) | Match | **C** | PDF only (no TeX source on arXiv) | 8 pages, 1 figure |
| 8 | C | [Novel type of phase transition in a system of self-driven particles](https://arxiv.org/abs/cond-mat/0611743) — T. Vicsek, A. Czirók, E. Ben-Jacob, I. Cohen, O. Shochet (1995 (PRL), arXiv 2006) | 200 (title matches) | arXiv assumed licence (1991–2003) (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | page count not stated on abs page |
| 9 | C | [Collective motion](https://arxiv.org/abs/1010.5017) — T. Vicsek, A. Zafeiris (2010) | 200 (title matches) | arXiv non-exclusive distribution licence 1.0 (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | page count not stated on abs page |
| 10 | C | [Boolean Dynamics with Random Couplings](https://arxiv.org/abs/nlin/0204062) — M. Aldana, S. Coppersmith, L. Kadanoff (2002) | 200 (title matches) | arXiv assumed licence (1991–2003) (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | 69 pages, 16 figures, Submitted to Springer Applied Mathemat |
| 11 | C | [When the map is better than the territory](https://arxiv.org/abs/1612.09592) — E. P. Hoel (2016) | 200 (title matches) | arXiv non-exclusive distribution licence 1.0 (abs page) | Match | **C** | PDF only (no TeX source on arXiv) | 15 pages, 6 figures |
| 12 | C | [Reconciling emergences: An information-theoretic approach to identify causal emergence in multivariate data](https://arxiv.org/abs/2004.08220) — F. E. Rosas, P. A. M. Mediano, H. J. Jensen et al. (2020) | 200 (title matches) | arXiv non-exclusive distribution licence 1.0 (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | 18 pages, 7 figures |
| 13 | C | [Statistical physics of social dynamics](https://arxiv.org/abs/0710.3256) — C. Castellano, S. Fortunato, V. Loreto (2007) | 200 (title matches) | arXiv non-exclusive distribution licence 1.0 (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | 58 pages, 22 figures |
| 14 | D | [Power-law distributions in empirical data](https://arxiv.org/abs/0706.1062) — A. Clauset, C. R. Shalizi, M. E. J. Newman (2007) | 200 (title matches) | arXiv non-exclusive distribution licence 1.0 (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | 43 pages, 11 figures, 7 tables, 4 appendices |
| 15 | D | [Power laws, Pareto distributions and Zipf's law](https://arxiv.org/abs/cond-mat/0412004) — M. E. J. Newman (2004) | 200 (title matches) | arXiv assumed licence (1991–2003) (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | 28 pages, 16 figures, minor corrections and additions in thi |
| 16 | D | [Power laws and Self-Organized Criticality in Theory and Nature](https://arxiv.org/abs/1310.5527) — D. Marković, C. Gros (2013) | 200 (title matches) | arXiv non-exclusive distribution licence 1.0 (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | page count not stated on abs page |
| 17 | D | [Colloquium: Criticality and dynamical scaling in living systems](https://arxiv.org/abs/1712.04499) — M. A. Muñoz (2017) | 200 (title matches) | arXiv non-exclusive distribution licence 1.0 (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | page count not stated on abs page |
| 18 | D | [Methods for Detecting Early Warnings of Critical Transitions in Time Series Illustrated Using Simulated Ecological Data](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0041010) — V. Dakos et al. (2012) | 200 | “© 2012 Dakos et al. … open-access article distributed under the terms of the Creative Commons Attribution License” | Match | **A** | HTML (PLOS article; JATS XML also offered by PLOS) | Journal article; page 293 KB HTML |
| 19 | D | [Growth, innovation, scaling, and the pace of life in cities](https://pmc.ncbi.nlm.nih.gov/articles/PMC1852329/) — L. M. A. Bettencourt, J. Lobo, D. Helbing, C. Kühnert, G. B. West (2007) | 200 (PMC; first request hit a reCAPTCHA interstitial, retry succeeded) | “© 2007 by The National Academy of Sciences of the USA … Freely available online through the PNAS open access option.” No CC licence on page | Match | **C** | HTML (PMC) | Journal article |
| 20 | D | [Statistical Mechanics: Entropy, Order Parameters, and Complexity](https://www.lassp.cornell.edu/sethna/StatMech/EntropyOrderParametersComplexity20.pdf) — J. P. Sethna (2nd ed. (author-hosted PDF)) | 200, redirects to sethna.lassp.cornell.edu | PDF front matter: “Oxford University Press retains ownership of the copyright … Copyright Oxford University Press 2021 v2.0”; free for browsing/study only | Match (doc says © author/OUP) | **C** | PDF | 494 pages, 20.1 MB PDF |
| 21 | E | [Network Science (online textbook)](https://networksciencebook.com/) — A.-L. Barabási (2016 (online book)) | 200 (JS single-page app; licence not visible in page HTML) | CC BY-NC-SA 2.0, confirmed from the footer of the chapter PDFs (“This work/book is licensed under a Creative Commons: CC BY-NC-SA 2.0”), seen via copies of the chapter PDFs found by web search, not on networksciencebook.com itself | Match (indirectly verified) | **B** | HTML (site, JS-rendered) or per-chapter PDF | Book-length (~10 chapters); print edition (CUP 2016) is separately copyrighted |
| 22 | E | [Emergence of scaling in random networks](https://arxiv.org/abs/cond-mat/9910332) — A.-L. Barabási, R. Albert (1999) | 200 (title matches) | arXiv assumed licence (1991–2003) (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | 11 pages, 2 figures |
| 23 | E | [Statistical mechanics of complex networks](https://arxiv.org/abs/cond-mat/0106096) — R. Albert, A.-L. Barabási (2001) | 200 (title matches) | arXiv assumed licence (1991–2003) (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | 54 pages, submitted to Reviews of Modern Physics |
| 24 | E | [The structure and function of complex networks](https://arxiv.org/abs/cond-mat/0303516) — M. E. J. Newman (2003) | 200 (title matches) | arXiv assumed licence (1991–2003) (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | Review article, 58 pages, 16 figures, 3 tables, 429 referenc |
| 25 | E | [Community detection in graphs](https://arxiv.org/abs/0906.0612) — S. Fortunato (2009) | 200 (title matches) | arXiv non-exclusive distribution licence 1.0 (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | page count not stated on abs page |
| 26 | E | [Epidemic processes in complex networks](https://arxiv.org/abs/1408.2701) — R. Pastor-Satorras, C. Castellano, P. Van Mieghem, A. Vespignani (2014) | 200 (title matches) | arXiv non-exclusive distribution licence 1.0 (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | 62 pages, 15 figures, final version |
| 27 | E | [Synchronization in complex networks](https://arxiv.org/abs/0805.2976) — A. Arenas, A. Díaz-Guilera, J. Kurths, Y. Moreno, C. Zhou (2008) | 200 (title matches) | arXiv non-exclusive distribution licence 1.0 (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | page count not stated on abs page |
| 28 | F | [Computational Mechanics: Pattern and Prediction, Structure and Simplicity](https://arxiv.org/abs/cond-mat/9907176) — C. R. Shalizi, J. P. Crutchfield (1999) | 200 (title matches) | arXiv assumed licence (1991–2003) (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | 29 pages, 4 EPS figures, this http URL Revision: Typos fixed |
| 29 | F | [Regularities Unseen, Randomness Observed: Levels of Entropy Convergence](https://arxiv.org/abs/cond-mat/0102181) — J. P. Crutchfield, D. P. Feldman (2001) | 200 (title matches) | arXiv assumed licence (1991–2003) (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | 35 pages, 21 fgures, Santa Fe Institute Working Paper 01-02- |
| 30 | F | [JIDT: An information-theoretic toolkit for studying the dynamics of complex systems](https://arxiv.org/abs/1408.3270) — J. T. Lizier (2014) | 200 (title matches) | arXiv non-exclusive distribution licence 1.0 (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | 37 pages, 4 figures |
| 31 | F | [Optimal leverage from non-ergodicity](https://arxiv.org/abs/0902.2965) — O. Peters (2009) | 200 (title matches) | arXiv non-exclusive distribution licence 1.0 (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | 17 pages, 3 figures |
| 32 | F | [Evaluating gambles using dynamics](https://arxiv.org/abs/1405.0585) — O. Peters, M. Gell-Mann (2014) | 200 (title matches) | arXiv non-exclusive distribution licence 1.0 (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | 11 pages, 2 figures |
| 33 | F | [The time interpretation of expected utility theory](https://arxiv.org/abs/1801.03680) — O. Peters, A. Adamou (2018) | 200 (title matches) | CC BY 4.0 (abs page) | Match | **A** | LaTeX source (arXiv /src) → Markdown | 8 pages, 3 figures |
| 34 | F | [Statistical Physics (Cambridge lecture notes)](https://www.damtp.cam.ac.uk/user/tong/statphys.html) — D. Tong (online lecture notes) | 200, redirects to davidtong.org/teaching/statistical-physics/ | No licence statement on the page | Match | **C** | PDF (full notes + per-chapter); HTML version also offered | ~190 pages (stated on page) |
| 35 | G | [Evolutionary game dynamics (Bull. AMS 40:479–519)](https://www.ams.org/journals/bull/2003-40-04/S0273-0979-03-00988-1/) — J. Hofbauer, K. Sigmund (2003) | 200, redirects to pubs.ams.org/journals/bull/2003-40-04/S0273-0979-03-00988-1 (JS app; article “Evolutionary game dynamics”, Hofbauer & Sigmund, present in page data) | Page data: “Copyright 2003 American Mathematical Society”; free to read | Match | **C** | PDF | Journal article, Bull. AMS 40:479–519 (41 pp) |
| 36 | G | [Five rules for the evolution of cooperation](https://pmc.ncbi.nlm.nih.gov/articles/PMC3279745/) — M. A. Nowak (2006) | 200 (PMC) | “Science. Author manuscript; available in PMC” – no CC licence; standard PMC copyright notice | Match | **C** | HTML (PMC) | Short article (Science 314:1560–1563) |
| 37 | G | [Evolutionary games on graphs](https://arxiv.org/abs/cond-mat/0607344) — G. Szabó, G. Fáth (2006) | 200 (title matches) | arXiv assumed licence (1991–2003) (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | Review, final version, 133 pages, 65 figures |
| 38 | G | [Statistical physics of human cooperation](https://arxiv.org/abs/1705.07161) — M. Perc, J. J. Jordan, D. G. Rand, Z. Wang, S. Boccaletti, A. Szolnoki (2017) | 200 (title matches) | arXiv non-exclusive distribution licence 1.0 (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | 48 two-column pages, 35 figures |
| 39 | H | [powerlaw: a Python package for analysis of heavy-tailed distributions](https://arxiv.org/abs/1305.0215) — J. Alstott, E. Bullmore, D. Plenz (2013) | 200 (title matches) | arXiv non-exclusive distribution licence 1.0 (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | 18 pages, 6 figures, code and supporting information at this |
| 40 | H | [Almost None of the Theory of Stochastic Processes](https://www.stat.cmu.edu/~cshalizi/almost-none/) — C. R. Shalizi (with A. Kontorovich) (online notes) | 200 | No licence statement on the page (“book-in-progress”) | Match | **C** | PDF (per-lecture/whole-book PDFs) | Book-length; size not measured |
| 41 | H | [Think Complexity, 2nd edition](https://greenteapress.com/wp/think-complexity-2e/) — A. B. Downey (2018 (2nd ed.)) | 200 | “Attribution-NonCommercial-ShareAlike 4.0 International License” (links creativecommons.org/licenses/by-nc-sa/4.0/) | Match | **B** | HTML/PDF (free PDF from Green Tea Press); code in GitHub repo | Book-length (2nd ed.) |
| 42 | I | [Neural networks and physical systems with emergent collective computational abilities](https://pmc.ncbi.nlm.nih.gov/articles/PMC346238/) — J. J. Hopfield (1982) | 200 (PMC) | Standard PMC copyright notice; no CC licence found on page (doc says © NAS; explicit © line not found in the scraped HTML) | Match on class (no open licence); © holder not re-confirmed | **C** | HTML (PMC; scanned 1982 article, PDF scan) | Short article (PNAS 79:2554–2558) |
| 43 | I | [Scaling Laws for Neural Language Models](https://arxiv.org/abs/2001.08361) — J. Kaplan et al. (2020) | 200 (title matches) | arXiv non-exclusive distribution licence 1.0 (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | 19 pages, 15 figures |
| 44 | I | [Emergent Abilities of Large Language Models](https://arxiv.org/abs/2206.07682) — J. Wei et al. (2022) | 200 (title matches) | CC BY 4.0 (abs page) | Match | **A** | LaTeX source (arXiv /src) → Markdown | page count not stated on abs page |
| 45 | I | [Are Emergent Abilities of Large Language Models a Mirage?](https://arxiv.org/abs/2304.15004) — R. Schaeffer, B. Miranda, S. Koyejo (2023) | 200 (title matches) | CC BY-NC-ND 4.0 (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | page count not stated on abs page |
| 46 | I | [Why AI is Harder Than We Think](https://arxiv.org/abs/2104.12871) — M. Mitchell (2021) | 200 (title matches) | arXiv non-exclusive distribution licence 1.0 (abs page) | Match | **C** | LaTeX source (arXiv /src) → Markdown | 12 pages |

## Ingestion notes for this collection

- **arXiv (32 with TeX):** download `https://arxiv.org/src/<id>` (tar/gzip). Pin the version (`vN`) in metadata and convert with pandoc to GFM with LaTeX math kept. Respect arXiv's robots and rate guidance (≤1 request every 3 s; the bulk S3 or API route is preferred). Even in class C we index the full text privately, but the API only returns ≤2 sentences plus a link.
- **PDF-only (#7, #11, #20, #34, #35, #40, ChaosBook #4, Barabási chapter PDFs if used):** Marker → Markdown with LaTeX, then spot-check equations.
- **HTML (#3 LibreTexts, #18 PLOS, #19/#36/#42 PMC, #41):** extract the article body and convert MathML to LaTeX. For PLOS, prefer the JATS XML. For PMC, prefer the PMC OA/BioC API to avoid captcha pages.
- **Store `licence`, `licence_url`, `licence_class` (A/B/C), `nc_flag` and `nd_flag` on every chunk.** The response layer enforces the class (see build-plan.md §Licence enforcement).

## Dropped items (from the doc, not re-verified)

The doc lists items it dropped because no free legal copy exists, the link failed, or the licence forbids ingestion. Examples: Watts–Strogatz 1998, Bak–Tang–Wiesenfeld, Peters & Adamou (now a paid LML Press book), Crutchfield 2012 (author PDF 404), Lorenz 1963 (link unverifiable), MacKay ITILA (on-screen viewing only, **do not ingest**), and copyrighted textbooks (Strogatz, Newman *Networks*, Mitchell, etc.). I did not re-check these. They stay out of the corpus.

## Miles's own module notes (found, not ingested)

Drive folder **Complex Systems** (`1a7EyLYijoYnYyarFS4rtxNc_saJ7BPug`, in My Drive root, owner Miles, not shared) contains:

| Item | Type | Size | Last modified (Europe/London) |
|---|---|---|---|
| 00 Diagnostic / `00_diagnostic.ipynb` | Colab notebook | 324 B (near-empty) | 21 Nov 2026 10:45 GMT |
| A Foundations of Complex Systems / **A Module Overview** | Google Doc | 4.3 KB | 21 Nov 2026 11:42 GMT |
| B Dynamical Systems / **B Module Overview** | Google Doc | 4.2 KB | 22 Nov 2026 08:52 GMT |
| C Emergence and Self-Organisation / **C Module Overview** | Google Doc | 4.5 KB | 21 Nov 2026 11:46 GMT |
| D Criticality and Phase Transitions / **D Module Overview** | Google Doc | 4.4 KB | 21 Nov 2026 11:46 GMT |
| E Network Science / **E Module Overview** | Google Doc | 4.3 KB | 21 Nov 2026 11:46 GMT |
| F Information Theory and Statistical Mechanics / **F Module Overview** | Google Doc | 5.1 KB | 21 Nov 2026 11:46 GMT |
| G Evolution, Adaptation and Game Theory / **G Module Overview** | Google Doc | 4.3 KB | 21 Nov 2026 11:46 GMT |
| H Maths and Computational Foundations / **H Module Overview** | Google Doc | 5.1 KB | 21 Nov 2026 11:46 GMT |
| I Complexity, AI and Engineering / **I Module Overview** | Google Doc | 6.2 KB | 21 Nov 2026 11:36 GMT |
| **Study Record** (folder root) | Google Doc | 6.1 KB | 22 Nov 2026 08:47 GMT |
| **RAG Corpus Shortlist** (folder root) | Google Doc | 16 KB | 23 Nov 2026 08:58 GMT |

Each module folder holds exactly one "Module Overview" doc and no other notes yet (about 40 KB of Miles's own text in total). A Drive-wide search for module notes turned up nothing else related. The other hits were unrelated code files. Suggested use: once Miles approves, ingest these as a separate `owner_notes` source type with licence `© Miles Waite, all rights reserved; owner-authorised for full display` (class A by owner consent). Alternatively, use them only to seed the golden eval questions. **I have not opened their contents.**
