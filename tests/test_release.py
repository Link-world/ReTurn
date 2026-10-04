"""Offline regressions for released caches and incomplete-result handling."""
import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


class ReleaseTests(unittest.TestCase):
    def invoke(self, module, *args, code=0):
        result = subprocess.run([sys.executable, '-m', module, *map(str, args)],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def test_all_released_caches_reproduce_scores_and_reports(self):
        contracts = sorted((ROOT / 'examples').glob('*/*/run_contract.json'))
        self.assertEqual(len(contracts), 9)
        count = 0
        with tempfile.TemporaryDirectory() as tmp:
            for index, contract in enumerate(contracts):
                original = contract.parent
                run = Path(tmp) / str(index)
                shutil.copytree(original, run)
                self.invoke('return_eval.score', '--run', run,
                            '--cache', run / 'review_cache.jsonl')
                self.invoke('return_eval.report', '--run', run)
                before = rows(original / 'scoring/scored_records.jsonl')
                after = rows(run / 'scoring/scored_records.jsonl')
                self.assertEqual(after, before, str(original))
                self.assertEqual(json.loads((run / 'report/summary.json').read_text()),
                                 json.loads((original / 'report/summary.json').read_text()))
                count += len(after)
        self.assertEqual(count, 144)

    def test_failed_inference_cannot_pass_scoring(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / 'run'
            shutil.copytree(ROOT / 'examples/recorded_outputs/qwen38_api', run)
            (run / 'predictions.jsonl').write_text('')
            self.invoke('return_eval.score', '--run', run, code=2)
            summary = json.loads((run / 'scoring/summary.json').read_text())
            self.assertGreater(summary['inference_failed'], 0)
            self.assertEqual(summary['scored'], 0)

    def test_empty_report_replaces_previous_csv_and_reports_exclusions(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / 'run'
            shutil.copytree(ROOT / 'examples/recorded_outputs/qwen38_api', run)
            self.assertGreater(len(list(csv.DictReader((run / 'report/groups.csv').read_text().splitlines()))), 0)
            (run / 'scoring/scored_records.jsonl').write_text('')
            self.invoke('return_eval.report', '--run', run, code=2)
            self.assertEqual(list(csv.DictReader((run / 'report/groups.csv').read_text().splitlines())), [])
            summary = json.loads((run / 'report/summary.json').read_text())
            self.assertEqual(summary['valid_single_multi_views'], 0)
            self.assertEqual(summary['excluded_views'], summary['logical_views_expected'])

    def test_invalid_selection_is_rejected(self):
        task = rows(ROOT / 'data/tasks/tasks.jsonl')[0]['task_id']
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / 'selection.json'
            for ids in ([], ['unknown-task'], [task, task]):
                manifest.write_text(json.dumps({'task_ids': ids}))
                self.invoke('return_eval.check', '--manifest', manifest, code=2)
        self.invoke('return_eval.check', '--manifest', 'data/quickstart_manifest.json')


if __name__ == '__main__':
    unittest.main()
