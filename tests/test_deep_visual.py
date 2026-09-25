"""Content contracts for the Jev guide; no API calls or performance assertions."""
import importlib.util
import json
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class DeepVisualTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = json.loads((ROOT / 'data/deep-dives.json').read_text())
        cls.article = next(a for a in data['articles'] if a['id'] == 'jev-agent-decision-layer')
        spec = importlib.util.spec_from_file_location('jev_demo', ROOT / 'examples/jev/jev_knowledge_demo.py')
        cls.demo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.demo)

    def test_same_request_in_article_and_script(self):
        self.assertEqual(self.article['demo']['request'], self.demo.REQUEST_BODY)
        self.assertEqual(self.article['demo']['answers'], self.demo.ILLUSTRATIVE_ANSWERS)

    def test_illustration_is_not_reported_as_measurement(self):
        self.assertIn('预设', self.article['demo']['label'])
        self.assertIn('不是本站运行', self.article['opening'][0])
        text = json.dumps(self.article, ensure_ascii=False)
        self.assertIn('没有真实 Jev 实测', text)
        self.assertIn('不是官方 Jev', text)

    def test_probability_and_score_contract(self):
        result = self.demo.inspect_answers(self.article['demo']['answers'])
        self.assertEqual(result['decision_status'], 'review_required_no_execution')
        self.assertTrue(math.isclose(result['relevance_expected_level'], 1.8))

    def test_invalid_probability_rejected(self):
        for p in [True, -0.1, 1.1, float('nan'), '0.9']:
            with self.assertRaises(ValueError):
                self.demo.probability(p)

    def test_bad_distribution_and_score_rejected(self):
        for value in [{'a': 0.5}, {'a': 0.5, 'b': 0.8}]:
            with self.assertRaises(ValueError):
                self.demo.distribution(value, {'a','b'})
        answers = json.loads(json.dumps(self.demo.ILLUSTRATIVE_ANSWERS))
        answers['relevance']['score'] = 0.2
        with self.assertRaises(ValueError):
            self.demo.inspect_answers(answers)

    def test_unique_sections_sources_and_apps(self):
        sections = self.article['sections']
        self.assertEqual(len(sections), 7)
        self.assertEqual(len({x['key'] for x in sections}), len(sections))
        source_ids = {s['id'] for s in self.article['sources']}
        self.assertEqual(len(source_ids), len(self.article['sources']))
        self.assertEqual({x['id'] for x in self.article['applications']}, {'theme','model','agent','knowledge'})
        for app in self.article['applications']:
            self.assertTrue(set(app['refs']) <= source_ids)
            for key in ['input','output','steps','mvp','data','metrics','boundary','experiment']:
                self.assertTrue(app[key])

    def test_rich_block_types_have_renderers(self):
        kinds = {b['type'] for s in self.article['sections'] for b in s['blocks']}
        self.assertTrue({'scene','demo','flow','implementation','router','applications','experiment','code'} <= kinds)
        js = (ROOT / 'src/deep-dives.js').read_text()
        for kind in kinds:
            self.assertIn("case '" + kind + "':", js)
        self.assertIn('aria-selected', js)
        self.assertIn('navigator.clipboard.writeText', js)
        self.assertNotIn('fetch(', js)

    def test_mobile_and_print_contract(self):
        css = (ROOT / 'src/deep-dives.css').read_text()
        self.assertIn('white-space:pre-wrap', css)
        self.assertIn('@container (max-width:400px)', css)
        self.assertIn('.dv-tabpanel[hidden]{display:none!important}', css)
        self.assertIn('@media print', css)
        self.assertIn('prefers-reduced-motion', css)

if __name__ == '__main__':
    unittest.main()
