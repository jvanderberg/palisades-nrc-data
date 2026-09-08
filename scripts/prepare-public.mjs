import { copyFile, cp, mkdir } from 'node:fs/promises';

await mkdir('public/data', { recursive: true });
for (const name of ['findings.csv', 'reports.csv', 'status.csv']) {
	await copyFile(`data/${name}`, `public/data/${name}`);
}
await cp('archive/reports', 'public/archive/reports', { recursive: true });
