import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
import archive
import build

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

    def test_static_build_is_reproducible_and_contains_records(self):
        with contextlib.redirect_stdout(io.StringIO()): build.build()
        one=(ROOT/'_site/index.html').read_bytes()
        with contextlib.redirect_stdout(io.StringIO()): build.build()
        two=(ROOT/'_site/index.html').read_bytes()
        self.assertEqual(hashlib.sha256(one).digest(),hashlib.sha256(two).digest())
        self.assertEqual(one.count(b'data-entry '),len(self.data['findings']))
        self.assertEqual(one.count(b'data-report '),len(self.data['reports']))
        self.assertNotIn(b'{{',one)
        self.assertIn(b'05000255/2026090-01',one)
        self.assertNotIn(b'is not in this feed',one)

if __name__=='__main__': unittest.main()
