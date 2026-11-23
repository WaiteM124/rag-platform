# Ingestion Pipeline

Document ingestion, normalisation, chunking, and embedding pipeline.

## Planned Structure

```
ingest/
├── fetchers/            # Source-specific fetchers
│   ├── arxiv_src.py     # arXiv LaTeX source download
│   ├── pdf_marker.py    # PDF → Markdown via Marker
│   ├── html_plos.py     # PLOS JATS XML extractor
│   ├── pmc_oa.py        # PMC Open Access API
│   └── govuk_content_api.py  # GOV.UK Content API
├── normalise/           # pandoc, MathML→LaTeX, cleaning
├── chunking/            # Heading-aware chunking (500-900 tokens)
├── licence/             # Licence registry, class rules, validators
├── embed/               # Titan V2 embedding via Bedrock
└── cli.py               # ingest --collection complex-systems [--changed-only]
```

## Licence Classes

| Class | Allowed | Examples |
|-------|---------|----------|
| A | Full text with attribution | CC BY, CC0, OGL |
| B | Full text (non-commercial only) | CC BY-NC-SA |
| C | Excerpt + link-out only | arXiv non-exclusive, All Rights Reserved |

Every source **must** have a verified licence record before ingestion.
