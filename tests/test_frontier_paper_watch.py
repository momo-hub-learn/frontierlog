"""Regress world-model source discovery without auto-ranking or fabricating model scores."""
from __future__ import annotations
from datetime import date,datetime,timezone
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from frontier_paper_watch import parse_feed,candidates,covered_ids,discover,feed_url
from hot_sync import collect_candidates
from model_data import validate_models
from build import validate_research_radar

MODELS=json.loads((ROOT/'data/models.json').read_text(encoding='utf-8'))
RESEARCH=json.loads((ROOT/'data/research-radar.json').read_text(encoding='utf-8'))
TODAY=date(2026,10,13)

def atom(entries):
    return ('<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">'+
      ''.join('<entry><id>https://arxiv.org/abs/'+p+'</id><title>'+t+'</title>'+
       '<published>'+d+'T12:00:00Z</published><summary>Action-conditioned world models for planning</summary>'+
       '<author><name>'+author+'</name></author></entry>' for p,t,d,author in entries)+
       '</feed>').encode()

PAPERS=[
 ('2610.06805','H-JEPA: End-to-End Learning of Hierarchical World Models','2026-10-05','Yann LeCun'),
 ('2610.07540','Preserving Unstable Modes in JEPA World Models','2026-10-06','Yann LeCun'),
 ('2610.09998','A New Action-Conditioned World Model','2026-10-12','A. Author')
]

class WorldModelCoverageTests(unittest.TestCase):
    def test_frontier_world_track_contains_verified_papers_and_linked_ami(self):
        validate_models(MODELS)
        world=next(t for t in MODELS['frontier_tracks'] if t['id']=='world-models')
        neo=next(t for t in MODELS['frontier_tracks'] if t['id']=='neo-labs')
        ids={x['id'] for x in world['items']}
        self.assertTrue({'hjepa-hierarchical-planning','jepa-control-unstable-modes'}<=ids)
        self.assertEqual(len([x for x in world['items'] if x['id']=='hjepa-hierarchical-planning']),1)
        ami=next(x for x in neo['items'] if x['id']=='ami-world-model-progress')
        self.assertEqual(ami['related_tracks'],['world-models'])
        self.assertEqual(len([x for t in MODELS['frontier_tracks'] for x in t['items'] if x['id']==ami['id']]),1)
        hjepa=next(x for x in world['items'] if x['id']=='hjepa-hierarchical-planning')
        self.assertEqual(hjepa['date'],'2026-10-05')
        self.assertIn('73.3%',hjepa['summary'])
        self.assertIn('DROID',hjepa['summary'])
        self.assertIn('闭环',hjepa['summary'])
        self.assertNotIn('intelligence',hjepa)
        self.assertNotIn('preference',hjepa)
        self.assertIn('hjepa-paper',hjepa['sources'])

    def test_bad_topic_relation_rejected(self):
        x=copy.deepcopy(MODELS)
        x['frontier_tracks'][-1]['items'][-1]['related_tracks']=['missing']
        with self.assertRaisesRegex(ValueError,'frontier cross-track'):validate_models(x)

    def test_research_records_reference_original_dates_and_primary_evidence(self):
        validate_research_radar(RESEARCH)
        ids={x['id'] for x in RESEARCH['items']}
        self.assertIn('hjepa-hierarchical-planning',ids)
        self.assertIn('jepa-control-unstable-modes',ids)
        self.assertIn('event-transitions-world-model-return-error',ids)
        x=next(x for x in RESEARCH['items'] if x['id']=='hjepa-hierarchical-planning')
        self.assertEqual(x['date'],'2026-10-05')
        self.assertTrue(all(s['strength']=='primary' for s in x['sources']))
        self.assertIn('本站没有复现',x['boundary'])
        self.assertIn('https://arxiv.org/abs/2610.06805',[s['url'] for s in x['sources']])
        event=next(x for x in RESEARCH['items'] if x['id']=='event-transitions-world-model-return-error')
        self.assertEqual(event['date'],'2026-10-21')
        self.assertIn('Atari-100k',event['fact'])
        self.assertIn('https://arxiv.org/abs/2610.29435',[s['url'] for s in event['sources']])
        self.assertIn('不代表',event['boundary'])
        judgment=next(x for x in RESEARCH['items'] if x['id']=='anthropic-agent-judgment-calls')
        self.assertEqual(judgment['date'],'2026-10-27')
        self.assertIn('86%',judgment['fact'])
        self.assertIn('一个任务',judgment['boundary'])
        self.assertEqual([s['url'] for s in judgment['sources']],['https://www.anthropic.com/research/agents-judgment-calls'])
        self.assertTrue(all(s['strength']=='primary' for s in judgment['sources']))

    def test_known_arxiv_ids_are_cross_source_deduplicated(self):
        known=covered_ids(MODELS,RESEARCH)
        self.assertIn('2610.06805',known)
        self.assertIn('2610.07540',known)

    def test_arxiv_atom_author_and_topic_intake(self):
        rows=parse_feed(atom(PAPERS))
        self.assertEqual(len(rows),3)
        out=candidates(rows,rows,{'2610.06805','2610.07540'},TODAY)
        self.assertEqual([r['arxiv_id'] for r in out],['2610.09998'])
        self.assertEqual(out[0]['status'],'editorial_review_required')
        self.assertNotIn('rank',out[0])
        self.assertNotIn('model_score',out[0])
        self.assertIn('search_query=',feed_url('au:LeCun'))

    def test_world_model_paper_does_not_require_a_celebrity_author(self):
        rows=parse_feed(atom([PAPERS[2]]))
        self.assertEqual(len(candidates([],rows,set(),TODAY)),1)

    def test_dtd_and_empty_invalid_source_fail_visible(self):
        with self.assertRaises(ValueError):parse_feed(b'<!DOCTYPE bad><feed/>')
        with self.assertRaises(ValueError):parse_feed(b'<html/>')
        with self.assertRaises(ValueError):discover(TODAY,fetch=lambda _:atom([]))

    def test_shadow_candidate_contains_research_but_never_auto_publishes(self):
        now=datetime(2026,10,13,10,tzinfo=timezone.utc)
        rows=collect_candidates(now)
        hjepa=[x for x in rows if x['url']=='https://arxiv.org/abs/2610.06805']
        self.assertTrue(hjepa)
        self.assertTrue(all(x['action'] in {'hold','merge'} for x in hjepa))
        self.assertTrue(all(x['priority_score']<1 for x in hjepa))

if __name__=='__main__':unittest.main()
