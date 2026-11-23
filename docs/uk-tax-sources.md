# UK Tax collection: source list (DRAFT, paused)

*Draft 0 • 23 Nov 2026 (Europe/London) • Grok Bot for Miles Waite*

> **Status: paused.** Priorities changed, so Complex Systems is now built first. This file keeps only what was verified before work stopped. It falls short of the 25–40 target. Finish it in the UK Tax phase (see build-plan.md, Phase 5).

## Ingestion route

The **GOV.UK Content API works** for these paths: `GET https://www.gov.uk/api/content/<base_path>` returns JSON with `document_type`, `schema_name`, `title`, `public_updated_at` and the body HTML in `details`. Tested 23 Nov 2026 on all paths below. Things to know:

- Moved pages return HTTP 200 with `schema_name: redirect`. The ingester must follow `redirects[].destination`. Some old paths return a 303.
- HMRC manuals (`hmrc_manual`) return a contents page listing `child_section_groups`. Crawl each `hmrc_manual_section` child. For example, the ESM root lists 19 child sections in 2 groups.
- Multi-part guides (`guide`) put each part in `details.parts[]`.
- Use `public_updated_at` together with `content_hash` for change detection.

## Licence

The GOV.UK page footer (checked on VAT Notice 700) says: *"All content is available under the Open Government Licence v3.0, except where otherwise stated"* and links `nationalarchives.gov.uk/doc/open-government-licence/version/3/`. That makes these pages class A (full text allowed with attribution). **Still to do:** confirm the OGL v3 exclusions (Royal Arms, departmental logos, third-party content, personal data) from the National Archives OGL page and GOV.UK's terms page, and strip logos and images on ingest. This was not done before the pause.

## Verified so far (HTTP 200 via the Content API on 23 Nov 2026)

Sizes are Content API JSON bytes, which roughly tracks text size. "Updated" is `public_updated_at`.

| # | Topic | Path | Title | Type | JSON size | Updated |
|---|---|---|---|---|---|---|
| 1 | VAT | /guidance/vat-guide-notice-700 | VAT guide (VAT Notice 700) | detailed_guide | 426 KB | 2026-11-18 |
| 2 | VAT | /vat-rates | VAT rates | answer | 9 KB | 2014-12-12 |
| 3 | VAT | /how-vat-works | How VAT works | guide | 29 KB | 2024-10-24 |
| 4 | VAT | /charge-reclaim-record-vat | Charge, reclaim and record VAT | guide | 66 KB | 2024-10-30 |
| 5 | VAT | /vat-flat-rate-scheme | VAT Flat Rate Scheme | guide | 32 KB | 2024-11-11 |
| 6 | VAT | /guidance/vat-cash-accounting-scheme-notice-731 | Cash Accounting Scheme (VAT Notice 731) | detailed_guide | 69 KB | 2023-12-18 |
| 7 | VAT | /guidance/vat-place-of-supply-of-services-notice-741a | Place of supply of services (VAT Notice 741A) | detailed_guide | 126 KB | 2022-09-29 |
| 8 | VAT | /guidance/vat-reverse-charge-technical-guide | VAT domestic reverse charge technical guide | detailed_guide | 80 KB | 2024-09-18 |
| 9 | VAT | /guidance/vat-domestic-reverse-charge-for-building-and-construction-services | Check when you must use the VAT domestic reverse charge for building and construction services | detailed_guide | 24 KB | 2020-09-24 |
| 10 | VAT | /guidance/partial-exemption-vat-notice-706 | Partial exemption (VAT Notice 706) | detailed_guide | 172 KB | 2025-12-16 |
| 11 | VAT | /hmrc-internal-manuals/vat-registration-manual | VAT Registration (manual contents) | hmrc_manual | 36 KB (contents only) | 2026-10-27 |
| 12 | MTD | /guidance/find-software-thats-compatible-with-making-tax-digital-for-vat | Find software that's compatible with Making Tax Digital for VAT | detailed_guide | 18 KB | 2025-05-01 |
| 13 | MTD | /government/publications/vat-notice-70022-making-tax-digital-for-vat | VAT Notice 700/22: Making Tax Digital for VAT | publication (notice) | 17 KB (landing page; the notice body is a linked attachment or HTML publication) | 2022-04-01 |
| 14 | MTD | /guidance/use-making-tax-digital-for-income-tax | Use Making Tax Digital for Income Tax | manual | 58 KB (contents; has child sections) | 2026-11-18 |
| 15 | IR35 | /guidance/understanding-off-payroll-working-ir35 | Understanding off-payroll working (IR35) | detailed_guide | 28 KB | 2026-02-26 |
| 16 | IR35 | /guidance/off-payroll-working-for-clients | Off-payroll working for clients | detailed_guide | 29 KB | 2024-08-30 |
| 17 | IR35 | /guidance/check-employment-status-for-tax | Check employment status for tax (CEST) | detailed_guide | 30 KB | 2025-04-30 |
| 18 | IR35 | /employment-status | Employment status | guide | 59 KB | 2015-02-12 |
| 19 | IR35 | /hmrc-internal-manuals/employment-status-manual | Employment Status Manual (contents) | hmrc_manual | 119 KB (contents) | 2026-10-07 |
| 20 | IR35 | /hmrc-internal-manuals/employment-status-manual/esm0500 | Guide to determining status – overview: contents | hmrc_manual_section | 13 KB | 2016-01-18 |
| 21 | IR35 | /hmrc-internal-manuals/employment-status-manual/esm10000 | Off-payroll working legislation: Chapter 10, ITEPA 2003 (from 6 April 2021): Contents | hmrc_manual_section | 12 KB | 2024-12-05 |
| 22 | IR35 | /hmrc-internal-manuals/employment-status-manual/esm10010 | Off-payroll working … basic principles: contracted-out services | hmrc_manual_section | 15 KB | 2021-03-03 |

**22 verified.** The two manual roots (#11, #19) expand to many sections when crawled.

### Redirects found (follow before ingesting; destinations not yet resolved)

`/vat-registration`, `/vat-returns`, `/guidance/rates-of-vat-on-different-goods-and-services`, `/guidance/making-tax-digital-for-vat`, `/guidance/check-when-a-business-must-follow-the-rules-for-making-tax-digital-for-vat`, `/guidance/check-if-youre-eligible-for-making-tax-digital-for-income-tax`, `/guidance/sign-up-your-business-for-making-tax-digital-for-income-tax`, `/guidance/find-software-thats-compatible-with-making-tax-digital-for-income-tax`, `/government/publications/making-tax-digital`, `/guidance/april-2021-changes-to-off-payroll-working-for-clients` (all return `schema_name: redirect`). `/vat-registration/when-to-register` returned 303.

### Guessed paths that returned 404 (do not use)

`/guidance/vat-registration-notice-70017`, `/guidance/vat-record-keeping-vat-notice-70021`, `/guidance/vat-invoices-and-records-vat-notice-70021`, `/guidance/vat-flat-rate-scheme-notice-733`, `/guidance/vat-annual-accounting-scheme-notice-732`, `/guidance/vat-bad-debt-relief-notice-700-18`, `/guidance/vat-margin-schemes-notice-718`, `/hmrc-internal-manuals/vat-traders-records-manual` (and `/vatrec1010`), `/hmrc-internal-manuals/vat-recovery`, `/hmrc-internal-manuals/vat-guidance`, `/guidance/vat-notice-70022-making-tax-digital-for-vat`, plus several guessed off-payroll paths. The real slugs for Notices 700/21, 700/18, 718 and 733 and for the VAT Traders' Records manual (VATREC) still need to be found. Use GOV.UK search (`https://www.gov.uk/api/search.json?q=...`) instead of guessing.

## Remaining work when resumed

1. Resolve the redirect destinations above and add them.
2. Find the correct slugs for VATREC, VIT (VAT Input Tax), Notices 700/21, 700/1, 733, 732 and 718, the MTD for VAT and Income Tax step-by-step pages, and ESM off-payroll sections ESM10000 to ESM10030+ via the search API.
3. Confirm the OGL exclusions, then reach 25–40 sources.
