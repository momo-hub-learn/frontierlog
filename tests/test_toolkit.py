"""Guard the evidence and build contract for task-first toolkit guides."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from toolkit_data import validate_toolkit
from build import build

class ToolkitTests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((ROOT/'data/toolkit.json').read_text(encoding='utf-8'))
        self.catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf-8'))
    def test_eligible_tasks_once(self):
        validate_toolkit(self.data,self.catalog)
        self.assertEqual(len(self.data['items']),10)
        self.assertNotIn('alphaevolve',{x['id'] for x in self.data['items']})
    def test_chatgpt_publisher(self):
        row=next(x for x in self.data['items'] if x['id']=='chatgpt-voice-work')
        self.assertEqual(row['publisher'],'OpenAI')
    def test_sources_and_dates_required(self):
        for key,value in [('url','https://untrusted.example/a'),('url','https://github.com@evil.example/a'),('url','javascript:alert(1)'),('verified_at','2099-01-01'),('verified_at','2026-09'),('published_at','2099-01-01')]:
            with self.subTest(key=key,value=value):
                data=copy.deepcopy(self.data);data['items'][0]['sources'][0][key]=value
                with self.assertRaises(ValueError):validate_toolkit(data,self.catalog)
    def test_no_runtime_claim_without_logs(self):
        for key,value in [('runtime_tested',True),('evidence_level','onsite-test')]:
            data=copy.deepcopy(self.data);data['items'][0][key]=value
            with self.assertRaises(ValueError):validate_toolkit(data,self.catalog)
    def test_missing_and_duplicate_tasks_rejected(self):
        for rows in [self.data['items'][:-1],self.data['items']+[self.data['items'][0]]]:
            data=copy.deepcopy(self.data);data['items']=rows
            with self.assertRaises(ValueError):validate_toolkit(data,self.catalog)
    def test_bad_facets_and_empty_steps_rejected(self):
        for key,value in [('access','free'),('group','other'),('steps',[]),('input',''),('sources',[])]:
            data=copy.deepcopy(self.data);data['items'][0][key]=value
            with self.assertRaises(ValueError):validate_toolkit(data,self.catalog)
    def test_commands_include_actual_flow(self):
        row=next(x for x in self.data['items'] if x['id']=='docling')
        command=row['steps'][1]['command']
        self.assertIn('\n',command);self.assertIn('docling ./sample.pdf',command)
    def test_build_contains_exact_guides_and_frontend(self):
        with tempfile.TemporaryDirectory() as tmp:
            app=build(Path(tmp),'momo-hub-learn/frontierlog','https://momo-hub-learn.github.io/frontierlog/')
            self.assertEqual(app['toolkit'],self.data)
            self.assertEqual(json.loads((Path(tmp)/'api/v1/toolkit.json').read_text()),self.data)
            html=(Path(tmp)/'index.html').read_text()
            self.assertIn("const TK =",html);self.assertIn('.tk-wrap',html)
            self.assertEqual(html,(Path(tmp)/'404.html').read_text())

if __name__=='__main__': unittest.main()
