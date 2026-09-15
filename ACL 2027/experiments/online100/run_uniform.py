"""Run the existing method implementations under a separately sealed fresh protocol."""
from pathlib import Path
import importlib.util
import os
import sys
import uniform_protocol as u


def main():
    assert u.enabled(), 'Uniform entry point requires its own output directories'
    if '--prepare-only' not in sys.argv:
        u.verify_seal()
    sys.path.insert(0, str(u.ROOT/'experiments/dreaddit_icl'))
    import comparison
    comparison.Native.chat = u.wrap_chat(comparison.Native.chat)
    # Disable DSPy's global disk/memory cache so a new run cannot reuse old generations.
    import dspy
    dspy.configure_cache(enable_disk_cache=False, enable_memory_cache=False)
    phase = os.environ['RECOVERY_PHASE']
    assert phase in ('online', 'offline')
    path = u.ROOT/'experiments'/('online100' if phase == 'online' else 'offline100')/'run.py'
    spec = importlib.util.spec_from_file_location('uniform_method_runner', path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    runner.main()


if __name__ == '__main__':
    main()
