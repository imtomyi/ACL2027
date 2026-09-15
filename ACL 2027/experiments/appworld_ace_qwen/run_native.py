"""Run the unmodified AppWorld CLI with only the language-model call routed to local Qwen3-8B."""
import sys, traceback
import native_bridge

native_bridge.install()

from appworld.cli import app

try:
    # Standalone mode can report an internal exception with exit status 0; propagate every failure.
    app(standalone_mode=False)
except SystemExit as exit:
    raise
except BaseException:
    traceback.print_exc()
    sys.exit(1)
