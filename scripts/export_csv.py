"""Export the persistent archive to the SPA's CSV data sources."""
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
data=json.loads((ROOT/'data/archive.json').read_text())

def write(name, fields, rows):
    target=ROOT/'data'/name
    temp=target.with_suffix('.csv.tmp')
    with temp.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore')
        writer.writeheader();writer.writerows(rows)
    temp.replace(target)

write('findings.csv',['id','title','kind','rating','text','reportAccession','reportNumber','reportDate','page','url','source','firstSeenAt'],data['findings'])
write('reports.csv',['accession','number','date','title','url','extractedCount','pdfPath','textPath','text'],[
    {**r,'text':(ROOT/r['textPath']).read_text()} for r in data['reports']
])
write('status.csv',['checkedAt','startDate'],[data])
print(f"Exported {len(data['findings'])} findings and {len(data['reports'])} reports to CSV")
