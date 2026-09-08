# Palisades NRC data

Fetches the NRC's current-quarter descriptor and the corresponding Palisades findings JSON using Node 24. No dependencies or third-party scraping relay are required.

GitHub Actions runs daily at 11:17 UTC (6:17 a.m. Central daylight time; 5:17 a.m. Central standard time) and can also be run manually. Schedules can be delayed by GitHub. Each successful run commits `data/findings.json`, including the NRC source URL, source update date, and retrieval time. Failed requests or invalid responses fail the workflow without replacing the last successful snapshot.

Run locally with `node scripts/fetch-nrc.mjs`. Optionally set `NRC_OUTPUT_DIR` to another output directory.

This is a quarterly findings feed, not an exhaustive inventory of violations or unresolved issues. It can omit newer inspection reports, minor violations, licensee-identified findings, and nonpublic security details.

## Dashboard integration

The dashboard should read this snapshot on each page load and label its `fetchedAt` time as the last successful NRC retrieval. Warn when that time is more than 48 hours old. A failed scheduled run must not be presented as an empty findings list.

This repository is private. A separately hosted dashboard needs a server-side, read-only GitHub credential scoped to this repository to read `data/findings.json` through the GitHub Contents API. Never put that credential in browser JavaScript. Repository creation does not automatically connect or update the dashboard.
