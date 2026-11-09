import { writeFile } from 'node:fs/promises';

// Usage: node http.mjs <url> <target> [json-body]  (a body makes it a JSON POST)
const [url, target, body] = process.argv.slice(2);
const allowed = ['https://www.nrc.gov', 'https://adams-search.nrc.gov'];
if (!allowed.includes(new URL(url).origin))
	throw Error('Only NRC sources are permitted');
let error;
for (let attempt = 0; attempt < 3; attempt++) {
	try {
		const r = await fetch(url, {
			method: body === undefined ? 'GET' : 'POST',
			body,
			cache: 'no-store',
			headers: {
				'User-Agent': 'PalisadesRecord/1.0 (public NRC records archive)',
				...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
			},
			signal: AbortSignal.timeout(25000),
		});
		if (!r.ok) throw Error(`NRC HTTP ${r.status}: ${url}`);
		await writeFile(target, Buffer.from(await r.arrayBuffer()));
		process.exit(0);
	} catch (e) {
		error = e;
		// A 403 is a deliberate refusal; retrying only adds load.
		if (String(e.message).includes('HTTP 403')) break;
		if (attempt < 2)
			await new Promise((r) => setTimeout(r, 1000 * 2 ** attempt));
	}
}
console.error(error.message);
process.exit(1);
