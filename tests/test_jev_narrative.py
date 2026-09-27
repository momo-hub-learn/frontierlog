"""Narrative contracts and offline policy tests; never call Jev or execute tools."""
import ast
import importlib.util
import json
from dataclasses import replace
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('decision_policy', ROOT/'examples/jev/decision_policy.py')
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
Signals, Policy, decide = module.Signals, module.Policy, module.decide

class NarrativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.article = next(a for a in json.loads((ROOT/'data/deep-dives.json').read_text())['articles'] if a['id']=='jev-agent-decision-layer')

    def test_six_continuous_chapters(self):
        a=self.article
        self.assertEqual([s['key'] for s in a['sections']],['scene','interface','implementation','confidence','stack','evaluation'])
        self.assertGreater(sum(len(b.get('text','')) for s in a['sections'] for b in s['blocks']),7500)
        for s in a['sections'][:-1]:
            self.assertEqual(s['blocks'][-1]['type'],'transition')
            self.assertGreater(len(s['blocks'][-1]['text']),50)

    def test_source_references_resolve(self):
        known={s['id'] for s in self.article['sources']}
        for s in self.article['sections']:
            for b in s['blocks']:
                self.assertTrue(set(b.get('refs',[]))<=known)
        for source in self.article['sources']:
            self.assertEqual(source['verified_at'],'2026-09-27')
            if source['id'].startswith('nano-'):
                self.assertIn('76fdfc9ecdca45a9bcef17991a07d3041a87685a',source['url'])

    def test_question_is_not_a_policy(self):
        demo=self.article['demo']
        self.assertNotIn('next_step',demo['request']['questions'])
        self.assertEqual(set(demo['request']['questions']),{'supported','document_kind','relevance'})
        self.assertEqual(demo['answers']['document_kind']['choice'],'observation')
        blocks=[b for s in self.article['sections'] for b in s['blocks']]
        self.assertEqual(sum(b['type']=='signal' for b in blocks),3)
        self.assertEqual({b['stage'] for b in blocks if b['type']=='case_update'}, {'02','03','04'})

    def test_distribution_math(self):
        b=next(b for s in self.article['sections'] for b in s['blocks'] if b['type']=='distribution')
        for row in b['series']:
            p=row['probabilities']
            self.assertAlmostEqual(sum(p),1)
            self.assertAlmostEqual(sum(i*v for i,v in enumerate(p)),1)

    def test_displayed_policy_is_actual_function(self):
        shown=next(b['code'] for s in self.article['sections'] for b in s['blocks'] if b.get('title','').startswith('策略核心'))
        source=(ROOT/'examples/jev/decision_policy.py').read_text()
        function=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='decide')
        self.assertEqual(ast.dump(ast.parse(shown).body[0]),ast.dump(function))

class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.signals=Signals(.99,1)
        self.policy=Policy(.95,validated_for_domain=True)

    def test_default_is_not_validated(self):
        self.assertEqual(decide(self.signals,Policy(.95)),'review')
    def test_read_denial_precedes_everything(self):
        self.assertEqual(decide(replace(self.signals,read_allowed=False,operation='write'),self.policy),'deny')
    def test_write_never_executes(self):
        self.assertEqual(decide(replace(self.signals,operation='write'),self.policy),'approval_required')
    def test_version_mismatch(self):
        for patch in [{'model_version':'other'},{'rubric_version':'other'}]:
            self.assertEqual(decide(replace(self.signals,**patch),self.policy),'review')
    def test_errors_and_conflicts(self):
        for patch in [{'response_valid':False},{'conflict':True}]:
            self.assertEqual(decide(replace(self.signals,**patch),self.policy),'review')
    def test_hard_evidence_failures_override_high_score(self):
        for patch in [{'entity_match':False},{'evidence_current':False}]:
            self.assertEqual(decide(replace(self.signals,**patch),self.policy),'retrieve')
            self.assertEqual(decide(replace(self.signals,remaining_rounds=0,**patch),self.policy),'review')
    def test_threshold_and_budget(self):
        self.assertEqual(decide(replace(self.signals,p_support=.08),self.policy),'retrieve')
        self.assertEqual(decide(replace(self.signals,p_support=.08,remaining_rounds=0),self.policy),'review')
        self.assertEqual(decide(self.signals,self.policy),'draft_with_citations')
    def test_invalid_inputs(self):
        for value in [True,'0.9',-1,1.1,float('nan'),float('inf')]:
            with self.assertRaises(ValueError): Signals(value,1)
        for patch in [{'remaining_rounds':-1},{'remaining_rounds':True},{'conflict':'false'},{'operation':'delete'}]:
            with self.assertRaises(ValueError): replace(self.signals,**patch)
    def test_cost_derivation(self):
        self.assertAlmostEqual(module.cost_threshold(100,5),.95)
        self.assertAlmostEqual(module.cost_threshold(10000,5),.9995)
        for costs in [(0,5),(100,-1),(100,float('nan'))]:
            with self.assertRaises(ValueError):module.cost_threshold(*costs)

if __name__=='__main__':unittest.main()
