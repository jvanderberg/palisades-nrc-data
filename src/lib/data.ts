import Papa from 'papaparse';

export type Finding = {
	id: string;
	title: string;
	kind: string;
	rating: string;
	text: string;
	reportAccession: string;
	reportNumber: string;
	reportDate: string;
	page: string;
	url: string;
	source: string;
	firstSeenAt: string;
};
export type Report = {
	accession: string;
	number: string;
	date: string;
	title: string;
	url: string;
	extractedCount: string;
	pdfPath: string;
	textPath: string;
	text: string;
};
export type Status = { checkedAt: string; startDate: string };
export type Archive = {
	findings: Finding[];
	reports: Report[];
	status: Status;
};
export const base = import.meta.env.BASE_URL;

async function csv<T>(
	name: string,
	required: string[],
	signal?: AbortSignal,
): Promise<T[]> {
	const response = await fetch(`${base}data/${name}.csv`, {
		cache: 'no-store',
		signal,
	});
	if (!response.ok)
		throw new Error(`Could not load ${name}.csv (${response.status})`);
	const parsed = Papa.parse<T>(await response.text(), {
		header: true,
		skipEmptyLines: true,
	});
	if (
		parsed.errors.length ||
		required.some((key) => !parsed.meta.fields?.includes(key))
	) {
		throw new Error(`Invalid ${name}.csv`);
	}
	return parsed.data;
}

export async function loadArchive(signal?: AbortSignal): Promise<Archive> {
	const [findings, reports, statuses] = await Promise.all([
		csv<Finding>(
			'findings',
			['id', 'title', 'kind', 'rating', 'text', 'reportDate', 'url'],
			signal,
		),
		csv<Report>(
			'reports',
			['accession', 'title', 'date', 'text', 'url', 'pdfPath', 'textPath'],
			signal,
		),
		csv<Status>('status', ['checkedAt', 'startDate'], signal),
	]);
	if (
		statuses.length !== 1 ||
		!Number.isFinite(Date.parse(statuses[0].checkedAt))
	)
		throw new Error('Invalid update timestamp');
	return { findings, reports, status: statuses[0] };
}
