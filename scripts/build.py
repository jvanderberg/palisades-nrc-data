"""Render saved NRC data into static HTML. No network, clock, or AI dependency."""
import html
import json
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'_site'
def esc(value): return html.escape(str(value),quote=True)

def build():
    data=json.loads((ROOT/'data/archive.json').read_text())
    OUT.mkdir(exist_ok=True)
    (OUT/'data').mkdir(exist_ok=True)
    shutil.copyfile(ROOT/'data/archive.json',OUT/'data/archive.json')
    shutil.copyfile(ROOT/'web/style.css',OUT/'style.css')
    shutil.copyfile(ROOT/'web/archive.js',OUT/'app.js')
    cards=[]
    for f in data['findings']:
        year=f['reportDate'][:4]
        cards.append(f'''<details class="finding" data-entry data-kind="{esc(f['kind'])}" data-year="{year}" data-rating="{esc(f['rating'])}">
<summary><span class="rating {'green' if f['rating']=='Green' else 'amber'}">{esc(f['rating'])}</span><div class="finding-name"><h2>{esc(f['title'])}</h2><p>{esc(f['kind'])} · {esc(f['id'])}</p></div><time datetime="{esc(f['reportDate'])}">{esc(f['reportDate'])}</time><span class="expand">+</span></summary>
<div class="detail"><p class="source-label">NRC report {esc(f['reportNumber'])} · PDF page {f['page']}</p><pre class="source-text">{esc(f['text'])}</pre><div class="record-source"><a href="{esc(f['url'])}#page={f['page']}">Original NRC PDF ↗</a><a href="#report-{esc(f['reportAccession'])}">{esc(f['reportAccession'])} · full report text ↓</a></div></div></details>''')
    reports=[]
    for r in data['reports']:
        text=(ROOT/r['textPath']).read_text()
        # Archive documents are content-addressed and retain earlier source versions.
        for version in r['versions']:
            for key in ['pdfPath','textPath']:
                target=OUT/version[key]; target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(ROOT/version[key],target)
        versions=''.join(f'<a href="./{esc(v["pdfPath"])}">Saved PDF {esc(v["sha256"][:12])}</a> ' for v in r['versions'])
        reports.append(f'''<details class="finding report" id="report-{esc(r['accession'])}" data-report data-year="{r['date'][:4]}"><summary><div class="finding-name"><h2>{esc(r['title'])}</h2><p>{esc(r['accession'])} · {r['extractedCount']} extracted entries</p></div><time>{esc(r['date'])}</time><span class="expand">+</span></summary><div class="detail"><div class="record-source"><a href="{esc(r['url'])}">Original NRC PDF ↗</a><a href="./{esc(r['textPath'])}">Extracted text ↗</a>{versions}</div><pre class="source-text full-report">{esc(text)}</pre></div></details>''')
    options=lambda values: ''.join(f'<option>{esc(v)}</option>' for v in sorted(set(values)))
    replacements={
        'CHECKED_AT':esc(data['checkedAt']), 'START_DATE':esc(data['startDate']),
        'REPORT_COUNT':str(len(data['reports'])), 'FINDING_COUNT':str(len(data['findings'])),
        'MINOR_COUNT':str(sum(f['kind']=='Minor violation' for f in data['findings'])),
        'LICENSEE_COUNT':str(sum(f['kind']=='Licensee-identified violation' for f in data['findings'])),
        'FINDINGS':'\n'.join(cards), 'REPORTS':'\n'.join(reports),
        'YEARS':options(r['date'][:4] for r in data['reports']),
        'KINDS':options(f['kind'] for f in data['findings']),
        'RATINGS':options(f['rating'] for f in data['findings']),
    }
    page=(ROOT/'web/template.html').read_text()
    for key,value in replacements.items(): page=page.replace('{{'+key+'}}',value)
    (OUT/'index.html').write_text(page)
    (OUT/'.nojekyll').touch()
    print(f"Rendered {len(data['findings'])} entries and {len(data['reports'])} complete reports")

if __name__=='__main__': build()
