"""Concurrent publication: rebuild on latest main, never rebase old generated HTML."""
from __future__ import annotations
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import retry_static_publish as p

def result(code):
    return SimpleNamespace(returncode=code)

class RetryStaticPublishTests(TestCase):
    def test_retry_discards_failed_commit_and_rebuilds(self):
        with mock.patch.object(p,'cmd') as cmd, mock.patch.object(p,'rebuild') as build:
            with mock.patch.object(p.subprocess,'run',side_effect=[result(1),result(1),result(1),result(0)]) as proc:
                p.publish('hot',attempts=2)
        self.assertEqual(build.call_count,2)
        self.assertEqual(cmd.call_args_list.count(mock.call('git','fetch','origin','main')),2)
        self.assertEqual(cmd.call_args_list.count(mock.call('git','reset','--hard','origin/main')),2)
        self.assertEqual(len([x for x in proc.call_args_list if x.args[0][1]=='push']),2)

    def test_noop_does_not_push_or_commit(self):
        with mock.patch.object(p,'cmd') as cmd, mock.patch.object(p,'rebuild'):
            with mock.patch.object(p.subprocess,'run',return_value=result(0)) as proc:
                p.publish('tibo',attempts=2)
        self.assertEqual(proc.call_count,1)
        self.assertFalse(any(x.args[:2]==('git','commit') for x in cmd.call_args_list))

    def test_retries_stop_at_bound(self):
        with mock.patch.object(p,'cmd'), mock.patch.object(p,'rebuild'):
            with mock.patch.object(p.subprocess,'run',side_effect=[result(1),result(1),result(1),result(1)]):
                with self.assertRaisesRegex(RuntimeError,'after push retries'):
                    p.publish('activity',attempts=2)

    def test_unknown_mode_fails_closed(self):
        with self.assertRaises(ValueError):
            p.publish('unknown')
        with self.assertRaises(ValueError):
            p.publish('hot',attempts=0)

    def test_production_workflows_call_verified_retry(self):
        for wf,mode in [('hot-sync.yml','hot'),('activity-radar-sync.yml','activity'),('tibo-sync.yml','tibo')]:
            source=(ROOT/'.github/workflows'/wf).read_text(encoding='utf-8')
            self.assertIn('scripts/retry_static_publish.py --mode '+mode,source)
            self.assertIn('if ! git push; then',source)
