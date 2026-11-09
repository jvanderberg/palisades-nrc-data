# Palisades Record

[Dashboard](https://jvanderberg.github.io/palisades-nrc-data/) · [Nightly refresh](https://github.com/jvanderberg/palisades-nrc-data/actions/workflows/refresh-nrc.yml)

React 19 + Vite + TypeScript SPA, using shadcn/Base UI, Tailwind v4, Lucide, and Biome. It loads CSV files on each visit with Papa Parse.

## Data

- `data/findings.csv`: findings and violations, NRC source text, classifications, report dates and links.
- `data/reports.csv`: every archived report, including full extracted text and PDF links.
- `data/status.csv`: last source-check timestamp, coverage start date, and how many report PDFs NRC refused at that check.

The initial restart-era backfill has 25 reports published since January 2024 and 22 explicitly labeled findings or violations. Reports without extracted entries remain available with their full text. Data is sourced from NRC reports, not generated prose.

## Nightly refresh

At **08:17 UTC** nightly (3:17 a.m. CDT / 2:17 a.m. CST), GitHub Actions:

1. Fetches NRC's plant report index, inspection-report JSON index and current-quarter feed, plus URLs in `config/sources.json`.
2. Downloads PDFs with Node and extracts source text with Poppler. Fixed parsing rules identify explicit findings and violations.
   NRC's CDN refuses automated requests to `www.nrc.gov/docs/` (since November 2026). When a PDF is refused, an already-archived PDF is reused; a new report is instead read from the ADAMS Public Search backend (`adams-search.nrc.gov`), whose indexed text is re-paginated to match the PDF's page numbers. Those entries are marked `ADAMS indexed text` and are replaced by the PDF extraction once the PDF downloads.
3. Merges records into the persistent archive, retaining older entries and source versions, and exports the CSVs.
4. Runs Biome and the TypeScript/Vite build, then publishes the SPA and data on GitHub Pages.

No AI service, inference, generated summaries, or private API keys are used. Failed updates preserve the previously published site. The UI flags data older than 48 hours. GitHub's scheduler and Pages propagation can be delayed.

`data/archive.json` is the ingestion checkpoint; the SPA consumes CSVs. `archive/reports/` holds source PDFs and text under SHA-256 hashes. Entries are keyed by NRC issue ID or report/section/ordinal; older entries are retained rather than replaced by the current-quarter list. Full report text is available when extraction rules do not recognize an entry. Counts cover indexed public sources, not an all-time or currently-open violation total.

## Development

```sh
npm ci
npm run dev
npm run check
npm run format
npm run build
```

To update the CSVs, install Node 24, Python 3 and Poppler, then run `npm run data:refresh`. To re-export existing archived data only, run `npm run data:export`.

Add a report URL to `config/sources.json` and push to include another NRC report. Newly linked inspection reports are discovered automatically. The historical source inventory can be extended without editing the React application.
