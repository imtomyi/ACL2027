"""Write Qwen3-8B copies of the released ACE AppWorld configs.

Only the model name/provider and the playbook output paths change; every prompt, agent setting,
sampling parameter, step and cost limit is copied from the released config. Trained playbooks are
written under the run root so the authors' released DeepSeek playbooks are never read or overwritten.
"""
from pathlib import Path
import argparse, copy, json
import _jsonnet

MODEL = 'qwen3:8b'
PROVIDER = 'local-ollama-qwen3-8b-q4_k_m'
SPLITS = ['test_normal', 'test_challenge']


def load(source, name):
    text = _jsonnet.evaluate_file(str(source/'experiments/configs'/f'{name}.jsonnet'),
                                  ext_vars={'APPWORLD_PROJECT_PATH': str(source)})
    return json.loads(text)


def swap(config):
    agent = config['config']['agent']
    for role in ['generator_model_config', 'reflector_model_config', 'curator_model_config']:
        if role in agent:
            agent[role] = dict(agent[role], name=MODEL, provider=PROVIDER)
    return config


def experiments(source, playbooks):
    prompts, initial = source/'experiments/prompts', source/'experiments/playbooks/appworld_initial_playbook.txt'
    result = {}
    for split in SPLITS:
        # The official ReAct prompt carries no playbook block; the evaluation agent still requires a file.
        config = swap(load(source, 'ACE_offline_no_GT_evaluation'))
        agent = config['config']['agent']
        agent['generator_prompt_file_path'] = str(prompts/'react.txt')
        agent['trained_playbook_file_path'] = str(initial)
        config['config']['dataset'] = split
        result[f'qwen3_8b_ReAct_{split}'] = dict(config=config, kind='evaluation', split=split, depends=[])
    for gt in ['with_GT', 'no_GT']:
        adaptation = f'qwen3_8b_ACE_offline_{gt}_adaptation'
        config = swap(load(source, f'ACE_offline_{gt}_adaptation'))
        config['config']['agent']['trained_playbook_file_path'] = str(playbooks/f'offline_{gt}'/'playbook.txt')
        result[adaptation] = dict(config=config, kind='adaptation', split='train', depends=[],
                                  final_playbook=str(playbooks/f'offline_{gt}'/'final.txt'))
        for split in SPLITS:
            config = swap(load(source, f'ACE_offline_{gt}_evaluation'))
            config['config']['agent']['trained_playbook_file_path'] = str(playbooks/f'offline_{gt}'/'final.txt')
            config['config']['dataset'] = split
            result[f'qwen3_8b_ACE_offline_{gt}_evaluation_{split}'] = dict(config=config, kind='evaluation',
                                                                          split=split, depends=[adaptation])
    for split in SPLITS:
        config = swap(load(source, 'ACE_online_no_GT'))
        config['config']['agent']['trained_playbook_file_path'] = str(playbooks/f'online_no_GT_{split}'/'playbook.txt')
        config['config']['dataset'] = split
        result[f'qwen3_8b_ACE_online_no_GT_{split}'] = dict(config=config, kind='online', split=split, depends=[],
                                                          final_playbook=str(playbooks/f'online_no_GT_{split}'/'final.txt'))
    return result


def differences(original, derived, path=''):
    """List every leaf that differs between a released config and its derived copy."""
    if isinstance(original, dict) and isinstance(derived, dict):
        out = []
        for k in sorted(set(original) | set(derived)):
            out += differences(original.get(k), derived.get(k), f'{path}.{k}' if path else k)
        return out
    return [] if original == derived else [path]


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    plan = experiments(args.source, args.root/'playbooks')
    released = {'ReAct': 'ACE_offline_no_GT_evaluation', 'online': 'ACE_online_no_GT'}
    audit = {}
    for name, job in plan.items():
        # Upstream curation writes the playbook file directly; its directory must already exist.
        Path(job['config']['config']['agent']['trained_playbook_file_path']).parent.mkdir(parents=True, exist_ok=True)
        (args.source/'experiments/configs'/f'{name}.jsonnet').write_text(json.dumps(job['config'], indent=2)+'\n')
        origin = (released['ReAct'] if 'ReAct' in name else released['online'] if 'online' in name
                  else name.replace('qwen3_8b_', '').rsplit('_test_', 1)[0])
        audit[name] = dict(released_config=origin, changed_fields=differences(load(args.source, origin), job['config']))
    (args.root/'jobs.json').write_text(json.dumps({k: {x: y for x, y in v.items() if x != 'config'} for k, v in plan.items()}, indent=2)+'\n')
    (args.root/'config_audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    print(json.dumps({k: v['changed_fields'] for k, v in audit.items()}, indent=1))
