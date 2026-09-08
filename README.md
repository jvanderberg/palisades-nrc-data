# Palisades Record

[Open the dashboard](https://jvanderberg.github.io/palisades-nrc-data/) · [Update history](https://github.com/jvanderberg/palisades-nrc-data/actions/workflows/refresh-nrc.yml) · [Published JSON](https://jvanderberg.github.io/palisades-nrc-data/data/findings.json)

Public NRC inspection findings dashboard hosted on GitHub Pages. Search, filter classifications, open original reports, and export JSON.

## Nightly updates

GitHub Actions runs at **08:17 UTC** every night (3:17 a.m. Central daylight time; 2:17 a.m. Central standard time). GitHub may delay scheduled runs. Manual runs and pushes affecting website code also update the site.

Node 24 fetches the current NRC quarter and corresponding Palisades findings JSON, validates it, commits `data/findings.json`, and publishes the dashboard. No dependencies, private credentials, or third-party relay are needed. Failed fetches leave the previous snapshot and published site intact. Successful runs record the retrieval time even if NRC has not changed its data.

Every visit reads the published snapshot with browser caching disabled. Reloading checks the snapshot; it does not contact NRC or trigger the workflow. Pages propagation and CDN caching may briefly delay a new publication. A warning appears when data is over 48 hours old. GitHub can disable scheduled workflows in public repositories after 60 days without activity; check Actions if updates stop.

## Scope

This quarterly feed is not an exhaustive inventory of violations or unresolved issues. It can omit newer reports, minor violations, licensee-identified findings, and security details. The August 31, 2026 radiation report is linked separately while absent from the feed. Green is not an overall plant safety rating.

## Local use

Run `node scripts/fetch-nrc.mjs` with Node 24. Optionally set `NRC_OUTPUT_DIR`. To preview, copy the contents of `web/` and the `data/` directory into one static serving directory, as the workflow does. Relative URLs support the repository Pages path.
