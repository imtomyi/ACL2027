import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import interim_quality as monitor
from test_run import artifact, task


def judgment(value=True):
    return {m: {'verdict': value, 'reason': 'Supported.',
                'evidence': [{'evidence_id': 'E1', 'quote': 'I feel uncertain.'}]}
            for m in monitor.METRICS}


class InterimTests(unittest.TestCase):
    def test_denominators_keep_unknown_technical_and_pending(self):
        rows = [{'status': 'complete', 'judgments': judgment(v)} for v in [True, False, None]]
        rows += [{'status': 'pending'}, {'status': 'technical_missing'}]
        result = monitor.summarize(rows)['credibility']
        self.assertEqual(result, {'T': 1, 'F': 1, 'U': 1, 'technical': 1, 'pending': 1,
                                  'binary_n': 2, 'resolved_pct': 50.0})

    def test_paired_delta_excludes_unmatched_and_unknown(self):
        left = {'a': {'status': 'complete', 'judgments': judgment(True)},
                'b': {'status': 'complete', 'judgments': judgment(None)},
                'unmatched': {'status': 'complete', 'judgments': judgment(True)}}
        right = {'a': {'status': 'complete', 'judgments': judgment(False)},
                 'b': {'status': 'complete', 'judgments': judgment(True)}}
        result = monitor.paired(left, right)
        self.assertEqual(result['shared_packets'], 2)
        self.assertEqual(result['metrics']['credibility']['joint_binary_n'], 1)
        self.assertEqual(result['metrics']['credibility']['left_minus_right_pp'], 100)
        self.assertEqual(result['metrics']['credibility']['excluded_pending_unknown_or_technical'], 1)

    def test_no_cross_phase_comparison_and_changed_input_rejected(self):
        row = {'phase': 'development', 'dataset': 'dreaddit', 'model': 'qwen3:8b',
               'method': 'warrantroute', 'packet_id': 'p', 'task_sha256': 'a',
               'status': 'complete', 'judgments': judgment()}
        other = {**row, 'phase': 'evaluation', 'model': 'llama3.1:8b'}
        self.assertFalse(monitor.comparisons([row, other])[1])
        other.update(phase='development', task_sha256='changed')
        with self.assertRaises(monitor.core.ContractError):
            monitor.comparisons([row, other])

    def fixture(self, root):
        c = monitor.core
        config = copy.deepcopy(c.BASE_CONFIG)
        c.write(root/'config.json', config)
        packets = [{'packet_id': str(i), 'task': task()} for i in range(1, 4)]
        c.write(root/'inputs.private.json', {'dreaddit': {'development': packets}})
        for i in range(1, 4):
            c.seal(root/f'development/dreaddit/qwen3_8b/{i:03d}/result.json', {
                'dataset': 'dreaddit', 'model': 'qwen3:8b', 'packet_id': str(i), 'episode': i,
                'memory_before': 'test', 'status': 'complete', 'outcome': {'artifact': artifact()}})
        return {'models': {'qwen3:8b': 'test'}}

    def test_one_call_per_tick_no_rejudging_and_parent_is_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.fixture(root)
            before = {str(p): p.read_bytes() for p in root.rglob('*.json')}
            response = {'done': True, 'response': json.dumps(judgment()), 'prompt_eval_count': 1, 'eval_count': 1}
            with patch.object(monitor.core, 'verify', return_value=manifest), patch.object(monitor.core, 'http_json', return_value=response) as http:
                folder = root/'interim_quality'
                rows = monitor.dev_records(root, folder, manifest, infer=True)
                self.assertEqual(http.call_count, 1)
                self.assertEqual(sum(r['status'] == 'complete' for r in rows), 1)
                monitor.dev_records(root, folder, manifest, infer=False)
                self.assertEqual(http.call_count, 1)
                monitor.dev_records(root, folder, manifest, infer=True)
                self.assertEqual(http.call_count, 2)
            for path, content in before.items():
                self.assertEqual(Path(path).read_bytes(), content)

    def test_qualification_judgment_reused_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.fixture(root)
            payload = {'task': task(), 'artifact': {k:v for k,v in artifact().items() if k != 'used_bullet_ids'}}
            request = {'prompt': monitor.core.COMMON+'\n'+monitor.core.PROMPTS['judge']+'\n'+json.dumps(payload, ensure_ascii=False, sort_keys=True),
                       'format': monitor.core.schemas(task())[3]}
            monitor.core.seal(root/'qualification_quality/dreaddit/qwen3_8b/calls/qualification_judge.attempt0.json',
                              {'status': 'complete', 'model': 'qwen3:8b', 'request': request, 'parsed': judgment()})
            with patch.object(monitor.core, 'http_json') as http:
                rows = monitor.dev_records(root, root/'interim_quality', manifest, infer=False)
                http.assert_not_called()
            self.assertEqual(rows[0]['origin'], 'qualification_reuse')
            self.assertEqual(rows[0]['status'], 'complete')

    def test_inflight_qualification_stays_pending_without_duplicate_judge(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.fixture(root)
            payload = {'task': task(), 'artifact': {k:v for k,v in artifact().items() if k != 'used_bullet_ids'}}
            request = {'prompt': monitor.core.COMMON+'\n'+monitor.core.PROMPTS['judge']+'\n'+json.dumps(payload, ensure_ascii=False, sort_keys=True),
                       'format': monitor.core.schemas(task())[3]}
            monitor.core.seal(root/'qualification_quality/dreaddit/qwen3_8b/calls/qualification_judge.attempt0.json',
                              {'status': 'in_flight', 'model': 'qwen3:8b', 'request': request})
            rows = monitor.dev_records(root, root/'interim_quality', manifest, infer=False)
            self.assertEqual(rows[0]['status'], 'pending')
            self.assertFalse((root/'interim_quality/development/dreaddit/qwen3_8b/1/quality.json').exists())


if __name__ == '__main__':
    unittest.main()
