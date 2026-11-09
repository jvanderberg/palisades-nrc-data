import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
import archive

class ArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((ROOT/'data/archive.json').read_text())
        cls.reports={r['accession']:r for r in cls.data['reports']}

    def parse(self,accession):
        report=self.reports[accession]
        return archive.extract((ROOT/report['textPath']).read_text(),report)

    def test_radiation_findings_and_pdf_pages(self):
        rows=self.parse('ML26245A104')
        self.assertEqual({r['id'] for r in rows},{'05000255/2026090-01','05000255/2026090-02'})
        self.assertTrue(all(r['page']==5 for r in rows))

    def test_minor_items_not_lost_when_summary_says_none(self):
        rows=self.parse('ML26055A151')
        self.assertEqual(len(rows),4)
        self.assertTrue(all(r['kind']=='Minor violation' for r in rows))

    def test_licensee_items_and_minor_items_outside_summary(self):
        rows=self.parse('ML26125A118')
        self.assertEqual(len(rows),4)
        self.assertEqual(sum(r['kind']=='Minor violation' for r in rows),2)
        self.assertEqual(sum(r['kind']=='Licensee-identified violation' for r in rows),1)

    def test_no_findings_report_is_not_an_invented_finding(self):
        self.assertEqual(self.parse('ML24078A315'),[])

    def test_security_cover_and_legacy_summary(self):
        self.assertEqual(self.parse('ML25205A049')[0]['rating'],'Severity Level IV')
        self.assertEqual(self.parse('ML24045A147')[0]['id'],'05000255/2023004-01')

    def test_anonymous_ids_do_not_depend_on_pdf_whitespace(self):
        r=self.reports['ML26055A151'];text=(ROOT/r['textPath']).read_text()
        first=archive.extract(text,r)
        second=archive.extract(text.replace('constitutes a minor violation','constitutes  a minor violation'),r)
        self.assertEqual([f['id'] for f in first],[f['id'] for f in second])

    def test_disappearing_findings_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            archive.write_json(root/'config/sources.json',{'startDate':'2024-01-01','plantPage':'https://www.nrc.gov/info-finder/reactors/pali','extraReports':[]})
            item=self.data['findings'][0]
            archive.write_json(root/'data/archive.json',{'checkedAt':'2026-09-08T00:00:00Z','reports':[],'findings':[item]})
            with patch.object(archive,'ROOT',root): result=archive.refresh(offline=True)
            self.assertEqual(result['findings'],[item])

    def adams(self,accession):
        return json.loads((ROOT/'tests/fixtures/adams'/(accession+'.json')).read_text())['document']

    def test_adams_text_extracts_like_the_pdf(self):
        report=self.reports['ML26125A118']
        document=self.adams('ML26125A118')
        text=archive.paginate_adams(document['content'])
        meta=archive.adams_metadata(document,text,report['url'])
        self.assertEqual({k:meta[k] for k in ('number','date','title')},{k:report[k] for k in ('number','date','title')})
        fields=lambda rows:[{k:r[k] for k in ('id','title','kind','rating','page')} for r in rows]
        self.assertEqual(fields(archive.extract(text,report)),fields(self.parse('ML26125A118')))

    def run_refresh(self,root,feeds,pdfs):
        def fake_download(url,body=None):
            if body is not None:
                hits=[{'document':d} for d in feeds['adams'] if d['AccessionNumber']==body['q']]
                return json.dumps({'count':len(hits),'results':hits}).encode()
            if url.startswith(archive.ADAMS+'/docdetails/'):
                return json.dumps({'document':next(d for d in feeds['adams'] if d['IdT']==url.rsplit('/',1)[1])}).encode()
            if url in feeds: return feeds[url]
            if url in pdfs: return pdfs[url]
            raise archive.FetchError(f'NRC HTTP 403: {url}')
        with patch.object(archive,'ROOT',root),patch.object(archive,'download',fake_download):
            return archive.refresh()

    def test_blocked_pdfs_use_archive_then_adams_text_until_the_pdf_arrives(self):
        archived=self.reports['ML24045A147']; new=self.reports['ML25205A049']
        feeds={
            'https://www.nrc.gov/info-finder/reactors/pali':b'<html></html>',
            archive.BASE+'/list-of-reports.json':json.dumps({'Sites':[{'SiteCode':'pali','Reports':[]}]}).encode(),
            archive.BASE+'/current-quarter.json':json.dumps({'pimreport':{'Year':2026,'Abbreviation':'Q3'}}).encode(),
            archive.BASE+'/2026q3/docketpim/pali.json':json.dumps({'DocketNum':'05000255'}).encode(),
            'adams':[self.adams('ML25205A049')],
        }
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            archive.write_json(root/'config/sources.json',{'startDate':'2024-01-01','plantPage':'https://www.nrc.gov/info-finder/reactors/pali','extraReports':[{'url':new['url']}]})
            text=root/archived['textPath']; text.parent.mkdir(parents=True)
            text.write_text((ROOT/archived['textPath']).read_text())
            archive.write_json(root/'data/archive.json',{'checkedAt':'2026-09-08T00:00:00Z','reports':[archived],'findings':[]})

            # Every /docs/ PDF is refused: the archived report keeps its PDF, the new one comes from ADAMS.
            first=self.run_refresh(root,feeds,{})
            reports={r['accession']:r for r in first['reports']}
            self.assertEqual(reports['ML24045A147']['lastCheckedAt'],archived['lastCheckedAt'])
            self.assertEqual(reports['ML25205A049']['textSource'],archive.ADAMS_SOURCE)
            self.assertEqual(reports['ML25205A049']['pdfPath'],'')
            self.assertEqual({k:reports['ML25205A049'][k] for k in ('number','date')},{k:new[k] for k in ('number','date')})
            self.assertEqual({(r['accession'],r['fallback']) for r in first['unavailableReports']},
                             {('ML24045A147','archived PDF'),('ML25205A049','ADAMS text')})
            provisional=[f for f in first['findings'] if f['reportAccession']=='ML25205A049']
            self.assertEqual([(f['rating'],f['page'],f['source']) for f in provisional],[('Severity Level IV',1,archive.ADAMS_SOURCE)])

            # Once the PDF downloads, its extraction replaces the provisional ADAMS entries.
            second=self.run_refresh(root,feeds,{new['url']:(ROOT/new['pdfPath']).read_bytes()})
            final=[f for f in second['findings'] if f['reportAccession']=='ML25205A049']
            self.assertEqual([f['id'] for f in final],[f['id'] for f in self.parse('ML25205A049')])
            self.assertEqual(final[0]['source'],archive.PDF_SOURCE)
            report=next(r for r in second['reports'] if r['accession']=='ML25205A049')
            self.assertEqual(report['textSource'],archive.PDF_SOURCE)
            self.assertEqual([v['source'] for v in report['versions']],[archive.ADAMS_SOURCE,archive.PDF_SOURCE])

if __name__=='__main__': unittest.main()
