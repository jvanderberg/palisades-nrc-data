import {mkdir, writeFile, rename} from 'node:fs/promises';
import {resolve} from 'node:path';
import {NRC_BASE, normalizeNrc} from './nrc.ts';

export async function collect(fetcher = fetch) {
  async function get(url) {
    let lastError;
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        const response = await fetcher(url, {
          cache: 'no-store',
          headers: {Accept: 'application/json', 'User-Agent': 'PalisadesRecord/1.0 (public NRC findings reader)'},
          signal: AbortSignal.timeout(20000),
        });
        if (!response.ok) throw new Error(`NRC HTTP ${response.status}: ${url}`);
        return await response.json();
      } catch (error) {
        lastError = error;
        if (attempt < 2) await new Promise(r => setTimeout(r, 1000 * 2 ** attempt));
      }
    }
    throw lastError;
  }
  const current = await get(`${NRC_BASE}/current-quarter.json`);
  const quarter = current.pimreport;
  if (!Number.isInteger(quarter?.Year) || !/^Q[1-4]$/.test(quarter?.Abbreviation)) {
    throw new Error('Unexpected NRC reporting quarter');
  }
  const sourceUrl = `${NRC_BASE}/${quarter.Year}${quarter.Abbreviation.toLowerCase()}/docketpim/pali.json`;
  const raw = await get(sourceUrl);
  const feed = normalizeNrc(raw, sourceUrl, new Date().toISOString());
  if (!Number.isFinite(Date.parse(feed.sourceUpdatedAt))) throw new Error('Invalid NRC update date');
  return {...feed, retrieval: 'Scheduled NRC fetch via GitHub Actions'};
}

if (process.argv[1] && import.meta.url === new URL(`file://${resolve(process.argv[1])}`).href) {
  const feed = await collect();
  const directory = resolve(process.env.NRC_OUTPUT_DIR || 'data');
  await mkdir(directory, {recursive: true});
  const target = resolve(directory, 'findings.json');
  await writeFile(`${target}.tmp`, JSON.stringify(feed, null, 2) + '\n');
  await rename(`${target}.tmp`, target);
  console.log(`Fetched ${feed.findings.length} findings for ${feed.quarter} at ${feed.fetchedAt}`);
}
