"""Deterministic NRC archive. Python stdlib + Node 24 + Poppler; no model calls."""
import argparse
import hashlib
import html
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parent.parent
BASE = 'https://www.nrc.gov/sites/default/files/doc_library/cdn/data/performance-indicators'
# Backend of NRC's ADAMS Public Search site; serves document text when /docs/ PDFs are refused.
ADAMS = 'https://adams-search.nrc.gov/api/search'
PDF_SOURCE = 'NRC report text'
ADAMS_SOURCE = 'ADAMS indexed text'
ISSUE = r'(?:NCV|FIN|NOV|AV)\s+(\d{8}/\d{7}[-‑–]\d{2})'

def compact(s):
    return re.sub(r'\s+', ' ', s).strip()

def read_json(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)

class FetchError(Exception):
    pass

def download(url, body=None):
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / 'response'
        command = ['node', str(ROOT/'scripts/http.mjs'), url, str(target)] + ([json.dumps(body)] if body is not None else [])
        run = subprocess.run(command, stderr=subprocess.PIPE, text=True)
        if run.returncode: raise FetchError(run.stderr.strip() or f'Download failed: {url}')
        return target.read_bytes()

def warn(message):
    # Surface as a GitHub Actions annotation without failing the run.
    print(('::warning::' if os.environ.get('GITHUB_ACTIONS') else 'warning: ')+message, flush=True)

def adams_document(accession):
    """Fetch one public ADAMS document's metadata and indexed text by accession number."""
    query={'q':accession,'filters':[],'legacyLibFilter':True,'mainLibFilter':True,'content':False,
           'anyFilters':[],'sort':'','sortDirection':1}
    results=json.loads(download(ADAMS,query)).get('results') or []
    hit=next((r['document'] for r in results if r['document'].get('AccessionNumber')==accession),None)
    if not hit: raise FetchError('ADAMS has no public document '+accession)
    document=json.loads(download(f"{ADAMS}/docdetails/{hit['IdT']}"))['document']
    if document.get('AccessionNumber')!=accession or not (document.get('content') or '').strip():
        raise FetchError('ADAMS returned no text for '+accession)
    return document

def paginate_adams(content):
    """Rebuild PDF page breaks in ADAMS indexed text so page numbers match the PDF.

    ADAMS emits each page's running header/footer before its body: cover-letter pages start with
    "M. Name 2", the distribution page with "Letter to ... dated", the enclosure cover with
    "Enclosure", and later enclosure pages with their bare printed page number.
    """
    lines=content.replace('\r\n','\n').split('\n')
    header=re.compile(r"^[A-Z]\.(?: [A-Z]\.)? [A-Z][A-Za-z'’-]+ +(\d{1,2})$")
    out=[]; letter=2; printed=2; enclosure=False; last_break=-99
    def page_break():
        nonlocal last_break
        out.append('\f'); last_break=len(out)
    for line in lines:
        s=line.strip()
        if not enclosure:
            m=header.match(s)
            if m and int(m[1])==letter:
                page_break(); letter+=1
            elif re.match(r'Letter to .+ dated ',s) and len(out)-last_break>4:
                page_break(); letter+=1
            elif s in ('Enclosure','U.S. NUCLEAR REGULATORY COMMISSION') and letter>2:
                page_break(); enclosure=True
            out.append(line)
        elif s==str(printed):
            page_break(); printed+=1
        else:
            out.append(line)
    # Like pdftotext, start each page's first line directly after the form feed.
    return re.sub(r'\f\n(?:[ \t]*\n)*','\f','\n'.join(out))

def adams_metadata(document, text, url):
    accession=document['AccessionNumber']
    subject=re.search(r'SUBJECT:\s*(.*?)\n\s*Dear ',text[:9000],re.S)
    title=compact(subject[1]) if subject else compact(document.get('DocumentTitle') or accession)
    number=re.search(r'05000255\s*/\s*(20\d{5})',title) or re.search(r'05000255\s*/\s*(20\d{5})',text[:9000])
    numbers=[m for n in document.get('DocumentReportNumber') or [] for m in re.findall(r'\b(20\d{5})\b',n)]
    date=document.get('DocumentDate') or ''
    if '05000255' not in (document.get('DocketNumber') or []) or not re.fullmatch(r'20\d{2}-\d{2}-\d{2}',date):
        raise ValueError('Unrecognized Palisades ADAMS metadata: '+accession)
    if not number and not numbers: raise ValueError('No report number in ADAMS document: '+accession)
    return {'accession':accession,'number':number[1] if number else numbers[0],'date':date,'title':title,'url':url}

class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.href=None; self.words=[]; self.links=[]
    def handle_starttag(self, tag, attrs):
        if tag == 'a': self.href=dict(attrs).get('href'); self.words=[]
    def handle_data(self, data):
        if self.href is not None: self.words.append(data)
    def handle_endtag(self, tag):
        if tag == 'a' and self.href is not None:
            self.links.append((self.href, compact(' '.join(self.words))))
            self.href=None

def normalize_text(text):
    # Preserve wording and form-feed page boundaries; remove only page-number-only lines.
    return re.sub(r'(?m)^[ \t]*\d{1,3}[ \t]*$', '', text)

def rating(text):
    colors = re.findall(r'\b(?:Green|White|Yellow|Red)\b', text)
    levels = re.findall(r'Severity\s+Level\s+(?:IV|III|II|I)\b', text, re.I)
    if colors: return colors[0]
    if levels: return compact(levels[0]).title().replace('Iv','IV').replace('Iii','III').replace('Ii','II')
    short=re.search(r'\bSL\s+(IV|III|II|I)\b',text)
    if short: return 'Severity Level '+short[1]
    return 'Not specified'

def extract(text, report):
    """Extract only explicit NRC finding tables, labeled violations and cover-letter findings."""
    clean = normalize_text(text)
    found=[]
    def add(kind, title, body, offset, identifier=None, significance=None):
        body=body.strip()
        identifier=identifier or (report['accession']+':'+kind+':'+hashlib.sha256((title+'\n'+body).encode()).hexdigest()[:16])
        identifier=identifier.replace('‑','-').replace('–','-')
        found.append({'id':identifier,'title':compact(title),'kind':kind,
                      'rating':significance or rating(body),'text':body,
                      'reportAccession':report['accession'],'reportNumber':report['number'],
                      'reportDate':report['date'],'page':clean[:offset].count('\f')+1,
                      'url':report['url'],'source':report.get('textSource',PDF_SOURCE)})
    start=clean.find('List of Findings and Violations')
    end=clean.find('Additional Tracking Items', start)
    if start>=0 and end>start:
        section=clean[start:end]
        lines=section.splitlines(keepends=True)
        offsets=[]; p=0
        for line in lines: offsets.append(p); p+=len(line)
        blocks=[]
        for i,line in enumerate(lines):
            if line.strip().startswith('Cornerstone'):
                j=i-1
                while j>=0 and not lines[j].strip(): j-=1  # ADAMS text puts a blank line before the table
                end=j+1
                while j>=0 and lines[j].strip(): j-=1
                blocks.append((j+1,end))
        for n,(a,b) in enumerate(blocks):
            stop=blocks[n+1][0] if n+1<len(blocks) else len(lines)
            body=''.join(lines[a:stop]).strip(); title=' '.join(x.strip() for x in lines[a:b])
            issue=re.search(ISSUE, body)
            if issue:
                add('Finding / violation',title,body,start+offsets[a],issue[1])
    # Explicit headings in Inspection Results, including items absent from the summary.
    heading=re.compile(r'(?m)^[ \t\f]*(Licensee[-‑]Identified Non[-‑]Cited Violation|Minor Violation)[ \t]+([0-9][\w.‑-]*)[ \t]*$')
    matches=list(heading.finditer(clean))
    ordinals={}
    for m in matches:
        limit=len(clean)
        for next_m in matches:
            if next_m.start()>m.start(): limit=min(limit,next_m.start()); break
        rest=clean[m.end():limit]
        boundary=re.search(r'(?m)^\s*(?:Observation:|Assessment:|Very Low Safety Significance Issue Resolution|EXIT MEETINGS|DOCUMENTS REVIEWED)',rest)
        if boundary: limit=min(limit,m.end()+boundary.start())
        # A formal finding's title directly precedes its Cornerstone table.
        corner=re.search(r'(?m)^\s*Cornerstone\s',clean[m.end():limit])
        if corner:
            before=clean[m.end():m.end()+corner.start()]
            split=before.rfind('\n\n')
            if split>=0: limit=min(limit,m.end()+split)
        body=clean[m.start():limit].strip()
        # End a licensee entry after its corrective-action references when available.
        corrective=re.search(r'Corrective Action References?:[^\n]*(?:\n(?!\s*\n)[^\n]+)?',body)
        if corrective: body=body[:corrective.end()]
        kind='Minor violation' if m[1]=='Minor Violation' else 'Licensee-identified violation'
        key=f"{report['accession']}:{kind}:{m[2]}"
        ordinals[key]=ordinals.get(key,0)+1
        add(kind,m[1]+' · '+m[2],body,clean.find(m[1],m.start(),m.end()),identifier=key+':'+str(ordinals[key]),significance='Minor' if kind=='Minor violation' else None)
    # Older executive summaries: explicit bullet describing an NCV.
    if not found:
        summary=re.search(r'(?s)SUMMARY\s*\n(.*?)(?:\f[^\n]*Report Details|\f[^\n]*REPORT DETAILS)',clean)
        if summary:
            for bullet in re.finditer(r'(?s)[•]\s+(.*?)(?=\n\s*[•]|\Z)',summary[1]):
                body=bullet[1].strip()
                if re.search(r'\b(?:NCV|non-cited violation)\b',body,re.I):
                    ids=list(dict.fromkeys(re.findall(ISSUE,clean)))
                    identifier=ids[0] if len(ids)==1 else None
                    add('Finding / violation',compact(body).split('. ')[0],body,summary.start(1)+bullet.start(1),identifier)
    # Public security cover letters can confirm findings while withholding the enclosure.
    if not found:
        cover=clean[:clean.find('If you contest') if 'If you contest' in clean else min(len(clean),6000)]
        for para in re.split(r'\n\s*\n',cover):
            if re.search(r'\bOne (?:finding|Severity Level IV violation)',compact(para),re.I) and 'documented in this report' in compact(para):
                add('Finding / violation',compact(para).split('. ')[0],para,clean.find(para))
    return list({item['id']:item for item in found}.values())

def metadata(text, accession, url):
    cover=text[:9000]
    dates=re.findall(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+20\d{2}',cover)
    date=datetime.strptime(compact(dates[0]),'%B %d, %Y').date().isoformat() if dates else None
    subject=re.search(r'SUBJECT:\s*(.*?)\n\s*Dear ',cover,re.S)
    title=compact(subject[1]) if subject else accession
    number=re.search(r'05000255\s*/\s*(20\d{5})',title)
    if not number: number=re.search(r'05000255\s*/\s*(20\d{5})',cover)
    if 'PALISADES' not in cover.upper() or not number or not date:
        raise ValueError('Unrecognized Palisades report metadata: '+accession)
    return {'accession':accession,'number':number[1],'date':date,'title':title,'url':url}

def fetch_pdf(url, accession):
    pdf=download(url)
    if not pdf.startswith(b'%PDF'): raise FetchError('Non-PDF response: '+url)
    digest=hashlib.sha256(pdf).hexdigest()
    folder=ROOT/'archive/reports'/accession; folder.mkdir(parents=True,exist_ok=True)
    pdfpath=folder/(digest+'.pdf'); textpath=folder/(digest+'.txt')
    if not pdfpath.exists(): pdfpath.write_bytes(pdf)
    if not textpath.exists(): subprocess.run(['pdftotext','-layout',str(pdfpath),str(textpath)],check=True)
    text=textpath.read_text()
    version={'sha256':digest,'pdfPath':str(pdfpath.relative_to(ROOT)),'textPath':str(textpath.relative_to(ROOT)),'source':PDF_SOURCE}
    return metadata(text,accession,url),text,version

def fetch_adams(url, accession):
    document=adams_document(accession)
    content=document['content']
    digest=hashlib.sha256(content.encode()).hexdigest()
    folder=ROOT/'archive/reports'/accession; folder.mkdir(parents=True,exist_ok=True)
    textpath=folder/(digest+'.adams.txt')
    if not textpath.exists(): textpath.write_text(paginate_adams(content))
    text=textpath.read_text()
    version={'sha256':digest,'pdfPath':'','textPath':str(textpath.relative_to(ROOT)),'source':ADAMS_SOURCE}
    return adams_metadata(document,text,url),text,version

def refresh(offline=False):
    config=read_json(ROOT/'config/sources.json')
    previous=read_json(ROOT/'data/archive.json',{'reports':[],'findings':[]})
    now=datetime.now(timezone.utc).isoformat().replace('+00:00','Z') if not offline else previous['checkedAt']
    reports={r['accession']:r for r in previous['reports']}
    urls={r['url'] for r in reports.values()}|{r['url'] for r in config['extraReports']}
    rawdir=ROOT/'archive/sources'; rawdir.mkdir(parents=True,exist_ok=True)
    unavailable=[]
    if not offline:
        page=download(config['plantPage']); (rawdir/'plant.html').write_bytes(page)
        listing=download(BASE+'/list-of-reports.json'); (rawdir/'report-index.json').write_bytes(listing)
        current=download(BASE+'/current-quarter.json'); (rawdir/'current-quarter.json').write_bytes(current)
        q=json.loads(current)['pimreport']
        if not isinstance(q.get('Year'),int) or not re.fullmatch('Q[1-4]',q.get('Abbreviation','')): raise ValueError('Invalid quarter')
        feedurl=f"{BASE}/{q['Year']}{q['Abbreviation'].lower()}/docketpim/pali.json"
        raw=download(feedurl); feed=json.loads(raw)
        if feed.get('DocketNum')!='05000255': raise ValueError('Wrong feed docket')
        digest=hashlib.sha256(raw).hexdigest()
        (rawdir/f'feed-{digest}.json').write_bytes(raw)
        parser=Links(); parser.feed(page.decode())
        for href,title in parser.links:
            if re.search(r'inspection report|annual assessment',title,re.I):
                url=urljoin(config['plantPage'],href)
                match=re.search(r'/ML(\d{2})\d{3}[A-Z0-9]{4}\.pdf$',url,re.I)
                if match and int(match[1])>=24: urls.add(url)
        sites=json.loads(listing)['Sites']
        site=next(s for s in sites if s['SiteCode']=='pali')
        for r in site['Reports']:
            if int(str(r['Num'])[:4])>=2024: urls.add(urljoin('https://www.nrc.gov',r['Url']))
        for key,items in feed.items():
            if key.endswith('Findings') and isinstance(items,list):
                for item in items:
                    for r in item['Reports']: urls.add(urljoin('https://www.nrc.gov',r['ReportUrl']))
    for url in sorted(urls):
        match=re.fullmatch(r'https://www\.nrc\.gov/docs/ML\d{4}/(ML\d{5}[A-Z0-9]{4})\.pdf',url)
        if not match: raise ValueError('Unexpected NRC PDF URL: '+url)
        accession=match[1]
        old=reports.get(accession,{})
        if offline:
            fetched=None
        else:
            try:
                fetched=fetch_pdf(url,accession)
            except FetchError as error:
                # NRC's CDN refuses automated /docs/ requests: keep an archived PDF if there is one,
                # otherwise use ADAMS indexed text so new reports still arrive.
                fetched=None; fallback='none'; message=str(error)
                if old and old.get('textSource',PDF_SOURCE)==PDF_SOURCE:
                    fallback='archived PDF'
                else:
                    try:
                        fetched=fetch_adams(url,accession); fallback='ADAMS text'
                    except FetchError as adams_error:
                        message+=f'; {adams_error}'
                        if old: fallback='archived ADAMS text'
                unavailable.append({'url':url,'accession':accession,'fallback':fallback,'error':message})
                warn(f"{message} (using {fallback})" if fallback!='none' else f"{message} (not yet archived; will retry next run)")
        if fetched is None:
            if accession not in reports: continue
            record=reports[accession]
            text=(ROOT/record['textPath']).read_text()
        else:
            record,text,version=fetched
            if record['date']<config['startDate']: continue
            versions=list(old.get('versions',[]))
            if not any(v['sha256']==version['sha256'] for v in versions): versions.append(version)
            record.update({k:version[k] for k in ('sha256','pdfPath','textPath')},textSource=version['source'],
                          versions=versions,firstSeenAt=old.get('firstSeenAt',now),lastCheckedAt=now)
        items=extract(text,record)
        record['extractedCount']=len(items)
        record['extractionStatus']='Extracted entries' if items else 'Full report text available'
        record['findings']=items
        reports[accession]=record
        print(f"{accession} {record['number']}: {len(items)} extracted entries",flush=True)
    # Merge rather than replace: disappearing sources and entries remain available.
    # ADAMS-text entries are provisional: re-extraction (or the PDF arriving) supersedes them.
    seen={f['id']:f['firstSeenAt'] for f in previous['findings'] if f.get('firstSeenAt')}
    findings={f['id']:f for f in previous['findings']
              if not (f.get('source')==ADAMS_SOURCE and f['reportAccession'] in reports)}
    for record in reports.values():
        for f in record.pop('findings',[]):
            findings[f['id']]={**f,'firstSeenAt':seen.get(f['id'],now)}
    result={'schemaVersion':2,'startDate':config['startDate'],'checkedAt':now,
            'sources':[config['plantPage'],BASE+'/list-of-reports.json',BASE+'/current-quarter.json'],
            'unavailableReports':unavailable if not offline else previous.get('unavailableReports',[]),
            'reports':sorted(reports.values(),key=lambda r:(r['date'],r['accession']),reverse=True),
            'findings':sorted(findings.values(),key=lambda f:(f['reportDate'],f['id']),reverse=True)}
    write_json(ROOT/'data/archive.json',result)
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true')
    result=refresh(parser.parse_args().offline)
    print(f"Archive: {len(result['reports'])} reports; {len(result['findings'])} entries")
    blocked=result['unavailableReports']
    if blocked:
        counts={k:sum(r['fallback']==k for r in blocked) for k in ('archived PDF','ADAMS text','archived ADAMS text','none')}
        warn(f"{len(blocked)} report PDFs could not be downloaded: "+', '.join(f'{v} {k}' for k,v in counts.items() if v))
