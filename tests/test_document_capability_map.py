"""Coverage for structured document, engineering-drawing and CAD capability paths."""
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class DocumentCapabilityMapTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf-8'))
        cls.items={x['id']:x for x in cls.data['items']}
        cls.sources={x['id']:x for x in cls.data['sources']}

    def test_domain_has_distinct_provenance_backed_stages(self):
        expected={
            'docling':'parse', 'mineru-4-2':'parse',
            'paddleocr-vl-1-6-document':'parse',
            'blockie-vrd-ie':'extract',
            'edocr2-engineering-drawings':'drawing',
            'ezdxf-cad-structure':'cad'
        }
        for ident,stage in expected.items():
            with self.subTest(ident=ident):
                item=self.items[ident]
                self.assertEqual(item['category'],'文档处理')
                self.assertEqual(item.get('capability_stage','parse'),stage)
                self.assertFalse(item['tested'])
                self.assertTrue(item['sources'])
                self.assertTrue(all(s in self.sources for s in item['sources']))
                self.assertIn('不',item['boundary'])
        self.assertEqual({x.get('capability_stage','parse') for x in self.items.values() if x['category']=='文档处理'},set(expected.values()))

    def test_blockie_is_never_promoted_to_unverified_deployment(self):
        method=self.items['blockie-vrd-ie']
        self.assertEqual(method['status'],'research')
        self.assertTrue(method['show_in_map'])
        self.assertIsNone(method['repo'])
        self.assertIn('FUNSD',method['scope'])
        self.assertIn('工程图纸',method['boundary'])

    def test_mineru_date_and_source_are_real_release_not_review_time(self):
        source=self.sources['mineru-4-2-release']
        self.assertEqual(source['published'],'2026-11-10')
        self.assertEqual(source['published_at'],'2026-11-10T11:45:47Z')
        self.assertEqual(source['checked'],'2026-11-11')
        release=next(x for x in self.data['events'] if x['id']=='mineru-4-2-release-20261110')
        self.assertEqual(release['date'],source['published'])
        self.assertEqual(release['published_at'],source['published_at'])

    def test_available_and_research_paths_separated_in_ui(self):
        js=(ROOT/'src/progress-v4.js').read_text(encoding='utf-8')
        css=(ROOT/'src/progress-v4.css').read_text(encoding='utf-8')
        self.assertIn("x.status==='research'&&x.show_in_map===true",js)
        self.assertIn("t.status==='research'",js)
        for stage in ('parse','extract','drawing','cad'):
            self.assertIn("'"+stage+"'",js)
        self.assertIn('p5-more-categories',js)
        self.assertIn('data-doc-stage',js)
        self.assertIn('focus-visible',css)
        self.assertIn('@media(max-width:620px)',css)

if __name__=='__main__':
    unittest.main()
