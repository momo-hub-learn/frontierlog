"""Guard the evidence and build contract for task-first toolkit guides."""
import copy
import json
from datetime import datetime, timedelta, timezone
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
        self.assertEqual(len(self.data['items']),sum(x['status']=='code' for x in self.catalog['items']))
        nemo=next(x for x in self.data['items'] if x['id']=='nvidia-nemo-automodel-0-7')
        self.assertEqual(nemo['entry_url'].split('/')[2],'docs.nvidia.com')
        self.assertNotIn('alphaevolve',{x['id'] for x in self.data['items']})
    def test_intelligent_ui_guide(self):
        row=next(x for x in self.data['items'] if x['id']=='chatgpt-gpt6-intelligent-ui')
        self.assertEqual(row['publisher'],'OpenAI')
        self.assertEqual(row['access'],'web')
        self.assertIn('交互',row['headline'])
    def test_chatgpt_publisher(self):
        row=next(x for x in self.data['items'] if x['id']=='chatgpt-voice-work')
        self.assertEqual(row['publisher'],'OpenAI')
    def test_openhands_1_34_guide_preserves_runtime_and_secret_boundaries(self):
        row=next(x for x in self.data['items'] if x['id']=='openhands')
        self.assertFalse(row['runtime_tested'])
        self.assertIn('v1.34.0',row['requirements'])
        self.assertIn('Settings → Runtime',row['steps'][0]['body'])
        self.assertIn('不证明宿主机、网络、挂载和模型后端已隔离',row['limitation'])
        self.assertEqual(row['sources'][0]['url'],'https://github.com/OpenHands/OpenHands/releases/tag/v1.34.0')
        self.assertEqual(row['sources'][0]['published_at'],'2026-10-27')
        validate_toolkit(self.data,self.catalog)
    def test_coderabbit_security_guide_keeps_sandbox_and_human_boundaries(self):
        row=next(x for x in self.data['items'] if x['id']=='openai-coderabbit-secure')
        self.assertFalse(row['runtime_tested'])
        self.assertIn('未运行',row['limitation'])
        self.assertIn('不能把结果归因于 GPT-6.1 Sol 单独完成',row['limitation'])
        self.assertIn('无生产网络',row['steps'][1]['body'])
        self.assertIn('不启用自动合并',row['steps'][-1]['body'])
        self.assertEqual(row['sources'][0]['published_at'],'2026-10-26')
    def test_sources_and_dates_required(self):
        for key,value in [('url','https://untrusted.example/a'),('url','https://github.com@evil.example/a'),('url','javascript:alert(1)'),('verified_at','2099-01-01'),('verified_at','2026-09'),('published_at','2099-01-01')]:
            with self.subTest(key=key,value=value):
                data=copy.deepcopy(self.data);data['items'][0]['sources'][0][key]=value
                with self.assertRaises(ValueError):validate_toolkit(data,self.catalog)
    def test_reviewed_vendor_newsrooms_are_accepted(self):
        rows={row['id']:row for row in self.data['items']}
        self.assertEqual(rows['anthropic-claude-security']['sources'][0]['url'].split('/')[2],'claude.com')
        self.assertEqual(rows['nvidia-openshell']['sources'][0]['url'].split('/')[2],'nvidianews.nvidia.com')
        self.assertEqual(rows['nvidia-auto-ontology']['sources'][0]['url'].split('/')[2],'blogs.nvidia.com')
        self.assertEqual(rows['microsoft-flint-interactive']['sources'][0]['url'].split('/')[2],'www.microsoft.com')
        self.assertEqual(rows['allenai-olmoearth-v1-3']['entry_url'].split('/')[2],'olmoearth.allenai.org')
        self.assertTrue(any(source['url'].split('/')[2]=='allenai.org' for source in rows['allenai-olmoearth-v1-3']['sources']))
        validate_toolkit(self.data,self.catalog)

    def test_flint_guide_separates_official_claims_from_local_evidence(self):
        row=next(x for x in self.data['items'] if x['id']=='microsoft-flint-interactive')
        self.assertFalse(row['runtime_tested'])
        self.assertIn('未运行',row['limitation'])
        self.assertIn('键盘、触摸',row['steps'][-1]['body'])
        self.assertEqual(row['sources'][0]['published_at'],'2026-10-22')

    def test_reviewed_author_paper_is_accepted(self):
        row=next(x for x in self.data['items'] if x['id']=='agent4sci')
        self.assertEqual(row['sources'][0]['url'].split('/')[2],'arxiv.org')
        validate_toolkit(self.data,self.catalog)

    def test_auto_ontology_preserves_credential_boundary(self):
        row=next(x for x in self.data['items'] if x['id']=='nvidia-auto-ontology')
        self.assertEqual(row['publisher'],'NVIDIA')
        self.assertFalse(row['runtime_tested'])
        self.assertIn('Vault',row['requirements'])
        self.assertIn('明文',row['limitation'])

    def test_agent4sci_keeps_dry_run_separate_from_runtime_evidence(self):
        row=next(x for x in self.data['items'] if x['id']=='agent4sci')
        self.assertFalse(row['runtime_tested'])
        self.assertIn('--dry-run',row['steps'][0]['command'])
        self.assertIn('GPU',row['requirements'])
        self.assertIn('不能推出',row['limitation'])
    def test_decisions_api_keeps_vendor_claims_separate_from_local_evidence(self):
        row=next(x for x in self.data['items'] if x['id']=='openai-decisions-api')
        self.assertFalse(row['runtime_tested'])
        self.assertIn('未调用',row['limitation'])
        self.assertIn('低置信度',row['steps'][-1]['body'])
        self.assertEqual(row['sources'][0]['published_at'],'2026-10-22')
    def test_verification_dates_use_beijing_calendar_day(self):
        data=copy.deepcopy(self.data)
        target=max(s['verified_at'] for row in data['items'] for s in row['sources'])
        target_start=datetime.fromisoformat(target+'T00:00:00+08:00').astimezone(timezone.utc)
        data['items'][0]['sources'][0]['verified_at']=target
        # The same instant is still the previous UTC day, but already the target day in Beijing.
        validate_toolkit(data,self.catalog,now=target_start)
        with self.assertRaisesRegex(ValueError,'timezone'):
            validate_toolkit(data,self.catalog,now=datetime.fromisoformat(target+'T00:00:00'))
        with self.assertRaisesRegex(ValueError,'Future toolkit'):
            validate_toolkit(data,self.catalog,now=target_start-timedelta(seconds=1))
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
        self.assertEqual(row['sources'][-1]['published_at'],'2026-10-28')
        self.assertIn('v2.143.1',row['requirements'])
        self.assertIn('全页 OCR 表格 token',row['limitation'])
        self.assertIn('Tesseract',row['limitation'])
        self.assertFalse(row['runtime_tested'])
        browser=next(x for x in self.data['items'] if x['id']=='browser-use')
        self.assertEqual(browser['sources'][-1]['published_at'],'2026-10-26')
        self.assertIn('PyPI',browser['limitation'])
    def test_build_contains_exact_guides_and_frontend(self):
        with tempfile.TemporaryDirectory() as tmp:
            app=build(Path(tmp),'momo-hub-learn/frontierlog','https://momo-hub-learn.github.io/frontierlog/')
            self.assertEqual(app['toolkit'],self.data)
            self.assertEqual(json.loads((Path(tmp)/'api/v1/toolkit.json').read_text()),self.data)
            html=(Path(tmp)/'index.html').read_text()
            self.assertIn("const TK =",html);self.assertIn('.tk-wrap',html)
            self.assertIn('资料核验 · 本站未运行',html)
            self.assertEqual(html,(Path(tmp)/'404.html').read_text())

if __name__=='__main__': unittest.main()
