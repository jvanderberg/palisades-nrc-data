const $ = id => document.getElementById(id);
const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const sourceLink = value => {const url = new URL(value); if(url.protocol !== 'https:' || url.hostname !== 'www.nrc.gov') throw Error('Unexpected source URL'); return escape(url.href);};
const date = value => new Date(value).toLocaleString('en-US', {dateStyle:'medium',timeStyle:'short'});
let feed, visible = [];
function render() {
  const query = $('query').value.toLowerCase(), rating = $('rating').value;
  visible = feed.findings.filter(f => (rating === 'All' || rating === f.rating) && JSON.stringify(f).toLowerCase().includes(query));
  $('count').textContent = `${visible.length} records`;
  $('findings').innerHTML = visible.map(f => `<details class="finding"><summary><span class="rating ${f.rating === 'Green' ? 'green' : 'amber'}">● ${escape(f.rating)}</span><div class="finding-name"><h2>${escape(f.title)}</h2><p>${escape([f.category,f.type,f.by].filter(Boolean).join(' · '))}</p></div><time>${escape(f.date)}</time><span class="expand">+</span></summary><div class="detail"><p>${escape(f.summary || 'No public description supplied by NRC.')}</p><dl><div><dt>Date listed by NRC</dt><dd>${escape(f.date)}</dd></div><div><dt>Current corrective-action status</dt><dd>Not provided by this feed</dd></div></dl>${f.reports.map(r => `<div class="record-source"><a href="${sourceLink(r.url)}">Read NRC report ${escape(r.number)} ↗</a><small>${escape(r.accession)}</small></div>`).join('')}</div></details>`).join('') || '<p class="empty">No findings match this view.</p>';
}
async function load() {
  $('reload').disabled = true;
  try {
    const response = await fetch('./data/findings.json', {cache:'no-store'});
    if (!response.ok) throw Error(`HTTP ${response.status}`);
    const data = await response.json();
    if (!Array.isArray(data.findings) || !Array.isArray(data.reports) || !Number.isFinite(Date.parse(data.fetchedAt))) throw Error('Invalid snapshot');
    sourceLink(data.sourceUrl);
    for (const f of data.findings) for (const r of f.reports) sourceLink(r.url);
    for (const r of data.reports) sourceLink(r.url);
    feed = data;
    $('freshness').textContent = `Last successful NRC retrieval: ${date(feed.fetchedAt)} · NRC source updated: ${date(feed.sourceUpdatedAt)} · Times shown in your local time zone`;
    const stale = Date.now() - Date.parse(feed.fetchedAt) > 48 * 60 * 60 * 1000;
    $('stale').classList.toggle('hidden', !stale);
    $('stale').textContent = 'This snapshot is over 48 hours old. The nightly update may be delayed or failing. Check the update history below.';
    $('total').textContent = feed.findings.length;
    $('green').textContent = feed.findings.filter(f => f.rating === 'Green').length;
    $('other').textContent = feed.findings.filter(f => f.rating !== 'Green').length;
    $('quarter').textContent = feed.quarter;
    $('coverage').classList.toggle('hidden', feed.findings.some(f => f.reports.some(r => r.accession === 'ML26245A104')));
    const previous = $('rating').value;
    $('rating').replaceChildren(...['All', ...new Set(feed.findings.map(f => f.rating))].map(r => new Option(r,r)));
    $('rating').value = [...$('rating').options].some(o => o.value === previous) ? previous : 'All';
    $('reports').innerHTML = feed.reports.map(r => `<a href="${sourceLink(r.url)}"><div><strong>Inspection report ${escape(r.number)}</strong><small>${escape(r.accession)}</small></div>↗</a>`).join('');
    $('source-json').href = feed.sourceUrl;
    $('source-json').classList.remove('hidden');
    $('export').disabled = false;
    render();
  } catch {
    if (feed) {
      $('stale').classList.remove('hidden');
      $('stale').textContent = 'Could not reload the snapshot. The previously loaded data remains displayed with its original retrieval time.';
    } else {
      $('freshness').textContent = 'Snapshot unavailable. Try reloading or use the NRC source links below.';
      $('count').textContent = 'Data unavailable';
      $('findings').innerHTML = '<p class="empty" role="alert">The saved findings could not be loaded. This does not mean there are no findings.</p>';
    }
  } finally { $('reload').disabled = false; }
}
$('reload').addEventListener('click', load);
$('query').addEventListener('input', () => feed && render());
$('rating').addEventListener('change', () => feed && render());
$('export').addEventListener('click', () => {
  const url = URL.createObjectURL(new Blob([JSON.stringify({...feed, findings:visible}, null, 2)], {type:'application/json'}));
  const link = document.createElement('a'); link.href = url; link.download = 'palisades-nrc-findings.json'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
});
load();
