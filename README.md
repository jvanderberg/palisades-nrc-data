# Palisades Record

[Public dashboard](https://jvanderberg.github.io/palisades-nrc-data/) · [Nightly runs](https://github.com/jvanderberg/palisades-nrc-data/actions/workflows/refresh-nrc.yml) · [Archive JSON](https://jvanderberg.github.io/palisades-nrc-data/data/archive.json)

An accumulating restart-era archive of NRC inspection reports published from January 1, 2024 onward. The initial backfill contains 25 reports and 22 explicitly labeled findings or violations. Full report text includes observations, tracking items and reports without extracted findings.

## Deterministic pipeline

No model, AI service, generated summary, scraping relay, or API key is used.

1. `scripts/archive.py` fetches the NRC Palisades plant index, the operating inspection-report JSON index, and the current-quarter findings JSON. The feed contributes report links; the findings displayed on the dashboard come from the PDFs.
2. It merges discovered PDF links with `config/sources.json` and every previously archived report URL. Reports disappearing from current lists remain in the archive.
3. `scripts/http.mjs` uses ordinary Node 24 HTTPS fetch. Poppler `pdftotext -layout` extracts text. PDFs and text are stored under SHA-256 content hashes; changed source files create new versions.
4. Fixed parsing rules extract the NRC's finding tables, labeled minor violations, licensee-identified violations, and explicit finding statements in public cover letters and older executive summaries. These are source excerpts, not summaries. Full report text remains available for formats the extractor does not recognize.
5. Entries merge by NRC issue number, or by report/section/ordinal for unnumbered labeled violations. Public cover statements use a content key. Previous entries are retained. These keys identify published entries, not a claim that each is a distinct underlying incident across all reports. Source revisions are retained for inspection.
6. `scripts/build.py` merges `data/archive.json` into `web/template.html`. The resulting HTML already contains all findings and report text; JavaScript only filters, opens report links, and formats timestamps. The build makes no network requests or clock calls. The same archive and template produce byte-identical HTML.

The source check time is fetch metadata. Source changes and newly discovered reports change the next archive. Dates in the interface are dates on NRC report cover letters. The coverage begins with reports published in 2024, including a report numbered 2023004 that was published in February 2024.

## Nightly schedule and failures

Actions runs every night at **08:17 UTC** (3:17 a.m. Central daylight time; 2:17 a.m. Central standard time), on relevant code pushes, and on manual dispatch. It fetches, validates, tests, renders, commits the archive, and deploys to GitHub Pages. A failed fetch or build prevents deployment, leaving the previous published site available. The page flags a source check older than 48 hours. GitHub scheduling and Pages propagation can be delayed.

## Add a source

Add an NRC PDF URL to `config/sources.json` under `extraReports`, then push or run the workflow. The parser requires a Palisades report number and a cover-letter date. Inspection reports newly linked from the monitored NRC indexes are added automatically. This source inventory is not a claim to contain every NRC document in ADAMS; historical records before 2024 are outside the configured coverage.

## Local commands

Requires Node 24, Python 3, and Poppler. No package installation is needed beyond those runtimes.

```sh
python3 scripts/archive.py
python3 -m unittest discover -s tests -v
python3 scripts/build.py
python3 -m http.server --directory _site 8000
```

For an offline re-extraction from already saved text, use `python3 scripts/archive.py --offline`. It preserves the previous check timestamp. The static build only requires Python.

NRC source wording is retained; PDF extraction can change spacing or table layout. Original PDFs and saved source versions are linked. Counts describe indexed public records, not all-time or currently open violations.
