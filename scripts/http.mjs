import {writeFile} from 'node:fs/promises';
const [url, target] = process.argv.slice(2);
if (new URL(url).origin !== 'https://www.nrc.gov') throw Error('Only NRC sources are permitted');
let error;
for (let attempt = 0; attempt < 3; attempt++) {
  try {
    const r = await fetch(url, {cache:'no-store', headers:{'User-Agent':'PalisadesRecord/1.0 (public NRC records archive)'}, signal:AbortSignal.timeout(25000)});
    if (!r.ok) throw Error(`NRC HTTP ${r.status}: ${url}`);
    await writeFile(target, Buffer.from(await r.arrayBuffer()));
    process.exit(0);
  } catch (e) { error=e; if(attempt<2) await new Promise(r=>setTimeout(r,1000*2**attempt)); }
}
throw error;
