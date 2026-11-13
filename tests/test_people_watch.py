import copy
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import people_watch as watch

class PeopleWatchTests(unittest.TestCase):
 def setUp(self):
  self.cfg=json.loads((ROOT/"data/people-watch-config.json").read_text())
  self.now=datetime(2026,11,13,9,30,tzinfo=timezone.utc)
  self.channels={"cn":{"items":[{"id":"one","title":"腾讯混元 Hy4 更新","publisher_id":"tencent-hunyuan","source_url":"https://www.tencent.com/hy4","published_at":None}]},
                 "media":{"items":[{"id":"two","title":"姚顺雨谈 Agent 研发","source_url":"https://www.qbitai.com/123","published_at":"2026-11-12T09:00:00Z"}]}}
 def test_same_person_id_exists_and_is_not_a_private_follow(self):
  data=json.loads((ROOT/"data/people.json").read_text())
  self.assertEqual(sum(p["id"]=="shunyu-yao" for p in data["people"]),1)
  self.assertEqual(self.cfg["people"][0]["person_id"],"shunyu-yao")
  self.assertNotIn("following",self.cfg)
 def test_public_team_signal_is_not_personal_credit(self):
  out,meta=watch.find_leads(self.cfg,self.channels,{},self.now)
  self.assertEqual(meta["new_candidates"],2)
  one=next(x for x in out["items"] if x["source_channel"]=="cn")
  two=next(x for x in out["items"] if x["source_channel"]=="media")
  self.assertEqual(one["relation"],"organization_context_only")
  self.assertIn("不代表本人独立贡献",one["boundary"])
  self.assertEqual(two["relation"],"named_mention")
  self.assertEqual(one["review_status"],"unreviewed")
  self.assertEqual(one["evidence_level"],"lead_only_not_people_event")
 def test_idempotence_and_review_not_overwritten(self):
  old,_=watch.find_leads(self.cfg,self.channels,{},self.now)
  old["items"][0]["review_status"]="rejected"
  old["items"][0]["editor_note"]="Not directly attributable"
  later=datetime(2026,11,14,9,30,tzinfo=timezone.utc)
  new,meta=watch.find_leads(self.cfg,self.channels,old,later)
  self.assertEqual(meta["new_candidates"],0)
  self.assertEqual(new["last_ingested_at"],old["last_ingested_at"])
  self.assertEqual(new["items"],old["items"])
 def test_absence_of_person_is_not_an_event(self):
  out,meta=watch.find_leads(self.cfg,{"media":{"items":[{"title":"unrelated","source_url":"https://qbitai.com/x"}]}},{},self.now)
  self.assertEqual(meta["new_candidates"],0)
  self.assertEqual(out["items"],[])
  self.assertIsNone(out["last_ingested_at"])
 def test_bad_clock_and_broken_queue_rejected(self):
  with self.assertRaises(ValueError):
   watch.find_leads(self.cfg,self.channels,{},datetime(2026,11,13))
  with self.assertRaises(ValueError):
   watch.find_leads(self.cfg,{"cn":{"items":{}}},{},self.now)
if __name__=="__main__":
 unittest.main()
