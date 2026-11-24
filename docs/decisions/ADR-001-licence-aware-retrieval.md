# ADR-001: Licence-aware retrieval and response composer

**Status:** Accepted  
**Date:** 2026-11-24  

---

## Context

The platform indexes third-party sources with mixed licences (OGL / CC BY / CC BY-NC-SA / arXiv non-exclusive / all-rights-reserved). A public demo must ground answers in retrieved text without republishing restricted full text.

## Decision

Classify every source and chunk with a licence class (`A` / `B` / `C`) in the collection registries and database. Retrieval may use full chunk text for grounding. Public output is enforced by `LicenceComposer` in `app/core/composer.py`:

- **Class A** (and open licences such as OGL, CC BY): full text with attribution.
- **Class B** (e.g. CC BY-NC-SA): full text while the app is non-commercial; Terraform can flip behaviour toward Class C when commercial.
- **Class C**: ≤300 character excerpt + link out; n-gram overlap check prevents long verbatim quotes in the answer (`output_guard` stage on `/api/ask`).

Ingest fails closed without licence metadata (`ingest/licence.py`).

## Consequences

- Every response path must run the composer / output guard; bypassing it is a defect.
- Changes to `app/core/composer.py` require tests (see `tests/unit/test_composer.py`).
- Eval gates include `licence_compliance: 1.0` in `evals/thresholds.yaml`.
- Class C corpora remain useful for retrieval quality without illegal republication.
