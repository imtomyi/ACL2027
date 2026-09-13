import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('ace_ta', Path(__file__).with_name('run.py'))
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


def task():
    return {'dataset': 'Dreaddit', 'research_question': 'What is expressed?',
            'evidence': [{'evidence_id': 'E1', 'source_id': 'S1', 'speaker_id': 'P1',
                          'text': 'I feel uncertain.', 'local_context': None}]}


def quote():
    return {'evidence_id': 'E1', 'quote': 'I feel uncertain.'}


def artifact():
    return {'codes': [{'code_id': 'C1', 'label': 'Uncertainty', 'definition': 'Expressed uncertainty.', 'evidence': [quote()]}],
            'themes': [], 'scope_and_gaps': ['One statement.'], 'alternative_interpretations': [], 'used_bullet_ids': []}


def audit(issues=False):
    return {'issues': [{'issue_id': 'I1', 'kind': 'methods', 'material': True, 'reason': 'A test issue.', 'evidence': [quote()]}] if issues else [],
            'checks_needed': ['methods'] if issues else [], 'summary': 'Test audit.'}


class Fake:
    def __init__(self, issues=False):
        self.config = copy.deepcopy(app.BASE_CONFIG)
        self.seen = []
        self.issues = issues

    def call(self, stage, role, payload, schema):
        self.seen.append((stage, role, copy.deepcopy(payload)))
        if role == 'scout':
            return {'observations': [{'interpretation': 'Uncertainty.', 'evidence': [quote()]}], 'gaps': [], 'checks_needed': []}
        if role in {'audit', 'methods_challenger', 'domain_challenger'}:
            return audit(self.issues and stage.startswith('initial'))
        return artifact()


class StructureTests(unittest.TestCase):
    def test_sanitization_excludes_claim_and_builder_metadata(self):
        p = {'research_question': 'Q', 'llm_generated_qualitative_claim': {'claim': 'DO NOT SEND'},
             'known_intended_flaw_type': 'DO NOT SEND', 'source_text_context': [
                 {'source_id': 'S1', 'speaker_id': 'P1', 'text': 'Original text.', 'candidate_role': 'cited',
                  'metadata': {'label': 'DO NOT SEND'}, 'local_context': None}]}
        output = json.dumps(app.sanitize(p, 'dreaddit'))
        self.assertNotIn('DO NOT SEND', output)
        self.assertNotIn('candidate_role', output)
        self.assertIn('Original text.', output)

    def test_all_roles_are_independent_then_synthesized(self):
        fake = Fake()
        app.execute_ta(fake, task(), 'all_roles', None)
        self.assertEqual(len(fake.seen), 4)
        for _, _, payload in fake.seen[:3]:
            self.assertNotIn('candidates', payload)
        self.assertEqual(len(fake.seen[-1][2]['candidates']), 3)

    def test_scout_first_pass_has_no_proposal(self):
        fake = Fake()
        out = app.execute_ta(fake, task(), 'warrantroute', {'version': 0, 'bullets': []})
        self.assertEqual(out['inner_calls'], 3)
        self.assertNotIn('artifact', fake.seen[1][2])
        self.assertEqual(out['termination'], 'checks_satisfied')

    def test_issue_owners_recheck_after_revision(self):
        fake = Fake(issues=True)
        out = app.execute_ta(fake, task(), 'warrantroute', {'version': 0, 'bullets': []})
        stages = [s for s, _, _ in fake.seen]
        self.assertIn('revision_1', stages)
        self.assertIn('recheck_1_methods', stages)
        self.assertLessEqual(out['inner_calls'], 12)

    def test_quote_and_unknown_code_checks(self):
        output = artifact()
        output['codes'][0]['evidence'][0]['quote'] = 'invented'
        self.assertEqual(app.integrity(output, task())[0]['kind'], 'quote_mismatch')

    def test_memory_update_is_local_and_cannot_use_unknown_feedback(self):
        memory = {'version': 0, 'bullets': [{'id': 'seed', 'active': True, 'provenance': 'seed', 'content': {'action': 'Keep me'}}]}
        operation = {'operation': 'ADD', 'target_id': '', 'feedback_ids': ['F1'], 'condition': 'Check evidence', 'action': 'Preserve scope', 'exception': 'Missing context'}
        proposal = {'lesson': 'A lesson', 'operations': [operation]}
        guard = {'status': 'complete', 'memory_sha256': app.digest(memory), 'proposal_sha256': app.digest(proposal),
                 'decisions': [{'proposal_id': 0, **{k: True for k in app.GUARD_CRITERIA}}]}
        updated, accepted, _ = app.apply_delta(memory, proposal, [{'feedback_id': 'F1', 'eligible': True}], 1, app.BASE_CONFIG, guard=guard)
        self.assertEqual(updated['bullets'][0], memory['bullets'][0])
        self.assertEqual(len(memory['bullets']), 1)
        self.assertEqual(len(accepted), 1)
        _, accepted, rejected = app.apply_delta(memory, proposal, [], 1, app.BASE_CONFIG)
        self.assertFalse(accepted)
        self.assertEqual(rejected[0]['reason'], 'no_eligible_feedback')

    def test_retrieval_does_not_inject_another_corpus_rule(self):
        memory = app.read(Path(__file__).with_name('seed_playbook.json'))
        ids = [b['id'] for b in app.retrieve(memory, app.BASE_CONFIG, task())]
        self.assertIn('seed-dreaddit', ids)
        self.assertNotIn('seed-cache', ids)

    def test_updater_schema_excludes_ineligible_feedback_and_wrong_targets(self):
        memory = {'bullets': [{'id':'seed', 'active':True}]}
        schema = app.updater_schema(memory,[{'feedback_id':'F1','eligible':True},{'feedback_id':'F2','eligible':False}])
        operation = {'operation':'ADD','target_id':'','replacement_id':'','feedback_ids':['F1'], 'condition':'A','action':'B','exception':'C'}
        app.Draft202012Validator(schema).validate({'lesson':'L','operations':[operation]})
        operation['feedback_ids'] = ['F2']
        self.assertFalse(app.Draft202012Validator(schema).is_valid({'lesson':'L','operations':[operation]}))
        operation.update(feedback_ids=['F1'],operation='REVISE',target_id='')
        self.assertFalse(app.Draft202012Validator(schema).is_valid({'lesson':'L','operations':[operation]}))
        empty = app.updater_schema(memory,[])
        self.assertTrue(app.Draft202012Validator(empty).is_valid({'lesson':'No eligible feedback','operations':[]}))

    def test_quote_schema_binds_exact_text_to_its_source(self):
        t = task()
        t['evidence'].append({'evidence_id':'E2','text':'Another statement.'})
        validator = app.Draft202012Validator(app.quote_schema(t))
        self.assertTrue(validator.is_valid(quote()))
        self.assertFalse(validator.is_valid({'evidence_id':'E2','quote':'I feel uncertain.'}))
        self.assertFalse(validator.is_valid({'evidence_id':'E1','quote':'I feel unsure.'}))


class JournalTests(unittest.TestCase):
    def test_playbook_citations_are_constrained_for_every_model(self):
        for model in app.MODELS:
            for playbook in [[], [{'id': 'seed-evidence'}]]:
                with self.subTest(model=model, playbook=playbook), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    schema = app.schemas(task())[0]
                    original = copy.deepcopy(schema)
                    output = artifact()
                    output['used_bullet_ids'] = [b['id'] for b in playbook]
                    response = {'done': True, 'response': json.dumps(output)}
                    with patch.object(app, 'http_json', return_value=response) as http:
                        client = app.Client(root, root/'packet', model, app.BASE_CONFIG, {'models': {model: 'x'}})
                        client.call('initial', 'proposer', {'task': task(), 'playbook': playbook}, schema)
                        bound = http.call_args.args[1]['format']
                        app.Draft202012Validator.check_schema(bound)
                        validator = app.Draft202012Validator(bound)
                        self.assertTrue(validator.is_valid(output))
                        output['used_bullet_ids'] = ['C1']
                        self.assertFalse(validator.is_valid(output))
                        self.assertEqual(schema, original)

    def test_exact_resume_and_changed_request_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = {'models': {'qwen3:8b': 'test_digest'}}
            response = {'done': True, 'done_reason': 'stop', 'response': json.dumps(artifact())}
            with patch.object(app, 'http_json', return_value=response) as http:
                client = app.Client(root, root/'packet', 'qwen3:8b', app.BASE_CONFIG, manifest)
                client.call('initial', 'proposer', {'task': task()}, app.schemas(task())[0])
                client.call('initial', 'proposer', {'task': task()}, app.schemas(task())[0])
                self.assertEqual(http.call_count, 1)
                with self.assertRaises(app.ContractError):
                    client.call('initial', 'methods', {'task': task()}, app.schemas(task())[0])

    def test_truncated_output_is_retained_without_semantic_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(app, 'http_json', return_value={'done': True, 'done_reason': 'length', 'response': '{}'}) as http:
                client = app.Client(root, root/'packet', 'qwen3:8b', app.BASE_CONFIG, {'models': {'qwen3:8b': 'x'}})
                with self.assertRaises(app.CallError):
                    client.call('initial', 'proposer', {}, app.schemas(task())[0])
                self.assertEqual(http.call_count, 1)
                saved = app.unseal(root/'packet/calls/initial.attempt0.json')
                self.assertEqual(saved['response']['done_reason'], 'length')

    def test_inflight_call_is_not_resubmitted_on_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            response = {'done': True, 'response': json.dumps(artifact())}
            with patch.object(app, 'http_json', return_value=response) as http:
                client = app.Client(root, root/'packet', 'qwen3:8b', app.BASE_CONFIG, {'models': {'qwen3:8b': 'x'}})
                client.call('initial', 'proposer', {}, app.schemas(task())[0])
                path = root/'packet/calls/initial.attempt0.json'
                saved = app.unseal(path)
                saved['status'] = 'in_flight'
                app.seal(path, saved)
                with self.assertRaises(app.CallError):
                    client.call('initial', 'proposer', {}, app.schemas(task())[0])
                self.assertEqual(http.call_count, 1)

    def test_denominators_and_fifty_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i in range(50):
                folder = root/'evaluation/dreaddit/qwen3_8b/generalist'/str(i)
                app.seal(folder/'result.json', {'status': 'complete', 'calls': 1})
                judgments = {k: {'verdict': True if i < 30 else False if i < 40 else None} for k in ['credibility','conformability','coverage']}
                app.seal(folder/'quality.json', {'status': 'complete', 'judgments': judgments})
            manifest = {'splits': {d: {'split_type': 'source_disjoint', 'development_n': 20} for d in app.BANKS}, 'blocked_cells': [], 'development_expected': 240}
            summary = app.export(root, manifest)
            self.assertEqual(summary['quality_binary_pairs'], 40)
            rows = app.read(root/'stats.json')['rows']
            row = rows[0]
            self.assertEqual(row['credibility_resolved_pct'], 75)
            self.assertEqual(row['credibility_binary_coverage_pct'], 80)
            self.assertEqual(row['credibility_pending'], 50)
            self.assertEqual(len(rows), 48)
            self.assertTrue((root/'checkpoints/dreaddit/qwen3_8b/generalist/050.json').exists())


if __name__ == '__main__':
    unittest.main()
