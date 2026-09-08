import { ArrowUpRight, Download, ShieldCheck } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { type Archive, base, loadArchive } from '@/lib/data';

const repo = 'https://github.com/jvanderberg/palisades-nrc-data';
const options = (values: string[]) => [...new Set(values)].sort();

export default function App() {
	const [data, setData] = useState<Archive | null>(null);
	const [error, setError] = useState('');
	const [query, setQuery] = useState('');
	const [year, setYear] = useState('All');
	const [kind, setKind] = useState('All');
	const [rating, setRating] = useState('All');
	const [reportQuery, setReportQuery] = useState('');
	const [copyStatus, setCopyStatus] = useState({ report: '', message: '' });
	const copyReport = async (report: string, value: string, label: string) => {
		try {
			await navigator.clipboard.writeText(value);
			setCopyStatus({ report, message: `${label} copied.` });
		} catch {
			setCopyStatus({
				report,
				message:
					'Clipboard access failed. Use the source link or download instead.',
			});
		}
	};
	useEffect(() => {
		const controller = new AbortController();
		loadArchive(controller.signal)
			.then((archive) => {
				if (!controller.signal.aborted) setData(archive);
			})
			.catch((failure) => {
				if (!controller.signal.aborted)
					setError(
						failure instanceof Error
							? failure.message
							: 'Could not load CSV data',
					);
			});
		return () => controller.abort();
	}, []);
	const findings = data?.findings ?? [];
	const reports = data?.reports ?? [];
	const visible = findings.filter(
		(f) =>
			(year === 'All' || f.reportDate.startsWith(year)) &&
			(kind === 'All' || kind === f.kind) &&
			(rating === 'All' || rating === f.rating) &&
			`${f.title} ${f.text} ${f.id} ${f.reportNumber}`
				.toLowerCase()
				.includes(query.toLowerCase()),
	);
	const visibleReports = reports.filter((r) =>
		`${r.title} ${r.text} ${r.accession}`
			.toLowerCase()
			.includes(reportQuery.toLowerCase()),
	);
	const checkedAt = data ? new Date(data.status.checkedAt) : null;
	const stale =
		checkedAt && Date.now() - checkedAt.valueOf() > 48 * 60 * 60 * 1000;
	const count = (value: number) => (data ? value : '—');
	return (
		<>
			<header className="masthead">
				<div className="brand">
					<ShieldCheck size={23} />
					PALISADES <b>RECORD</b>
				</div>
				<span className="edition">NRC records · nightly updates</span>
				<a href="#sources">
					Sources & data <ArrowUpRight size={14} />
				</a>
			</header>
			<main>
				<div className="heading">
					<div>
						<p className="eyebrow">COVERT, MICHIGAN · DOCKET 05000255</p>
						<h1>Palisades restart-era record</h1>
						<p className="intro">
							Inspection reports, findings and violations · reports published
							since {data?.status.startDate ?? '2024-01-01'}
						</p>
					</div>
				</div>
				<div className="freshness">
					<span>
						Last source check:{' '}
						{checkedAt?.toLocaleString(undefined, {
							dateStyle: 'medium',
							timeStyle: 'short',
						}) ?? 'Loading…'}
						{checkedAt && ' (local time)'}
					</span>
					<a href={`${repo}/actions/workflows/refresh-nrc.yml`}>
						Nightly update history ↗
					</a>
				</div>
				{stale && (
					<p className="coverage-note" role="status">
						The last successful source check was more than 48 hours ago.
					</p>
				)}
				{error && (
					<p className="coverage-note" role="alert">
						{error}. Refresh the page to try again.
					</p>
				)}
				<div className="stats">
					<div>
						<span>Archived reports</span>
						<strong>{count(reports.length)}</strong>
						<small>Full source text and PDFs</small>
					</div>
					<div>
						<span>Findings / violations</span>
						<strong>{count(findings.length)}</strong>
						<small>Explicitly labeled NRC entries</small>
					</div>
					<div>
						<span>Minor violations</span>
						<strong>
							{count(
								findings.filter((f) => f.kind === 'Minor violation').length,
							)}
						</strong>
						<small>Included in entries</small>
					</div>
					<div>
						<span>Licensee-identified violations</span>
						<strong>
							{count(
								findings.filter(
									(f) => f.kind === 'Licensee-identified violation',
								).length,
							)}
						</strong>
						<small>Included in entries</small>
					</div>
				</div>
				<section aria-labelledby="findings-heading">
					<div className="section-heading">
						<h2 id="findings-heading">Findings & violations</h2>
						<a href={`${base}data/findings.csv`} download>
							<Download size={14} /> Findings CSV
						</a>
					</div>
					<div className="toolbar">
						<select
							aria-label="Report publication year"
							value={year}
							onChange={(e) => setYear(e.target.value)}
						>
							<option value="All">All years</option>
							{options(reports.map((r) => r.date.slice(0, 4))).map((v) => (
								<option key={v}>{v}</option>
							))}
						</select>
						<select
							aria-label="Entry type"
							value={kind}
							onChange={(e) => setKind(e.target.value)}
						>
							<option value="All">All types</option>
							{options(findings.map((f) => f.kind)).map((v) => (
								<option key={v}>{v}</option>
							))}
						</select>
						<select
							aria-label="NRC classification"
							value={rating}
							onChange={(e) => setRating(e.target.value)}
						>
							<option value="All">All classifications</option>
							{options(findings.map((f) => f.rating)).map((v) => (
								<option key={v}>{v}</option>
							))}
						</select>
						<div className="search">
							<Input
								type="search"
								aria-label="Search findings"
								placeholder="Search NRC text, report or requirement…"
								value={query}
								onChange={(e) => setQuery(e.target.value)}
							/>
						</div>
					</div>
					<div className="list-label">
						<span aria-live="polite">
							{data ? `${visible.length} entries` : 'Loading…'}
						</span>
						<span>REPORT PUBLICATION DATE · NEWEST FIRST</span>
					</div>
					<div className="findings">
						{visible.map((f) => (
							<details className="finding" key={f.id}>
								<summary>
									<span
										className={`rating ${f.rating === 'Green' ? 'green' : 'amber'}`}
									>
										{f.rating}
									</span>
									<div className="finding-name">
										<h2>{f.title}</h2>
										<p>
											{f.kind} · {f.id}
										</p>
									</div>
									<time dateTime={f.reportDate}>{f.reportDate}</time>
									<span className="expand">+</span>
								</summary>
								<div className="detail">
									<p className="source-label">
										NRC report {f.reportNumber} · PDF page {f.page}
									</p>
									<pre className="source-text">{f.text}</pre>
									<div className="record-source">
										<a href={`${f.url}#page=${f.page}`}>Original NRC PDF ↗</a>
										<span>{f.reportAccession}</span>
									</div>
								</div>
							</details>
						))}
						{!data && !error && (
							<p className="empty" role="status">
								Loading CSV data…
							</p>
						)}
						{data && visible.length === 0 && (
							<p className="empty">No entries match these filters.</p>
						)}
					</div>
				</section>
				<section id="reports" aria-labelledby="reports-heading">
					<div className="section-heading">
						<h2 id="reports-heading">All reports</h2>
						<a href={`${base}data/reports.csv`} download>
							<Download size={14} /> Reports CSV
						</a>
					</div>
					<div className="toolbar report-tools">
						<Input
							type="search"
							aria-label="Search all report text"
							placeholder="Search full report text…"
							value={reportQuery}
							onChange={(e) => setReportQuery(e.target.value)}
						/>
						<span aria-live="polite">{visibleReports.length} reports</span>
					</div>
					<div className="findings">
						{visibleReports.map((r) => (
							<details className="finding report" key={r.accession}>
								<summary>
									<div className="finding-name">
										<h2>{r.title}</h2>
										<p>
											{r.accession} · {r.extractedCount} extracted entries
										</p>
									</div>
									<time dateTime={r.date}>{r.date}</time>
									<span className="expand">+</span>
								</summary>
								<div className="detail">
									<div className="record-source">
										<a href={r.url}>Original NRC PDF ↗</a>
										<a
											href={`${base}${r.pdfPath}`}
											download={`${r.number}-${r.accession}.pdf`}
										>
											Download PDF ↓
										</a>
										<a
											href={`${base}${r.textPath}`}
											download={`${r.number}-${r.accession}.txt`}
										>
											Download text ↓
										</a>
										<Button
											variant="outline"
											onClick={() =>
												void copyReport(r.accession, r.url, 'Report link')
											}
										>
											Copy link
										</Button>
										<Button
											variant="outline"
											onClick={() =>
												void copyReport(r.accession, r.text, 'Report text')
											}
										>
											Copy text
										</Button>
										{copyStatus.report === r.accession && (
											<span role="status">{copyStatus.message}</span>
										)}
									</div>
									<pre className="source-text full-report">{r.text}</pre>
								</div>
							</details>
						))}
						{data && visibleReports.length === 0 && (
							<p className="empty">No reports match this search.</p>
						)}
					</div>
				</section>
				<section id="sources" className="sources">
					<div>
						<p className="eyebrow">SOURCE & DATA</p>
						<h2>Nightly archive</h2>
						<p>
							NRC source documents and CSVs refresh at 08:17 UTC each night.
							Older records remain in the archive. Dates above are report
							publication dates; source text and original PDFs are linked.
						</p>
						<div className="source-links">
							<a href="https://www.nrc.gov/info-finder/reactors/pali">
								NRC restart reports ↗
							</a>
							<a href={`${base}data/findings.csv`}>Findings CSV ↗</a>
							<a href={`${base}data/reports.csv`}>Reports CSV ↗</a>
							<a href={`${repo}/blob/main/config/sources.json`}>
								Source inventory ↗
							</a>
							<a href={repo}>Code & archive history ↗</a>
						</div>
					</div>
				</section>
				<footer>
					<span>PALISADES RECORD</span>
					<p>Public NRC records. Independent of NRC and the plant operator.</p>
					<a href={repo}>SOURCE CODE ↗</a>
				</footer>
			</main>
		</>
	);
}
