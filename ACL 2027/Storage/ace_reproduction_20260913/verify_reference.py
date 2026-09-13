#!/usr/bin/env python3
"""Read-only reference preflight. Uses metadata and hashes; never runs inference."""

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
import urllib.request


def sha256(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--tokenizer-dir", required=True, type=Path)
    parser.add_argument("--check-server", action="store_true")
    args = parser.parse_args()
    bundle = Path(__file__).resolve().parent
    manifest = json.loads((bundle / "reference_manifest.json").read_text())
    failures = []
    warnings = []
    checks = 0

    def equal(label, actual, expected, show_values=True):
        nonlocal checks
        checks += 1
        if actual != expected:
            detail = f": expected {expected!r}, found {actual!r}" if show_values else ""
            failures.append(label + detail)

    def check_files(label, root, entries):
        for relative, expected in sorted(entries.items()):
            path = root / relative
            try:
                actual = sha256(path)
            except OSError as error:
                actual = f"unreadable ({type(error).__name__})"
            equal(f"{label}: {relative}", actual, expected)

    equal("Python version", platform.python_version(), manifest["python"])
    for name, expected in sorted(manifest["packages"].items()):
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            actual = "not installed"
        equal(f"Package {name}", actual, expected)

    check_files("Bundled snapshot", bundle / "snapshot", manifest["source_and_config_sha256"])
    check_files("Repository", args.repo_root, manifest["source_and_config_sha256"])
    check_files("Data", args.repo_root, manifest["required_data_sha256"])
    check_files("Tokenizer", args.tokenizer_dir, manifest["tokenizer_files_sha256"])

    current_platform = platform.platform()
    if current_platform != manifest["platform"]:
        warnings.append(f"Platform differs: {current_platform}; reference: {manifest['platform']}")
    if sys.platform == "darwin":
        for key, expected in manifest["hardware"].items():
            try:
                actual = subprocess.check_output(["/usr/sbin/sysctl", "-n", key], text=True).strip()
            except (OSError, subprocess.CalledProcessError):
                actual = "unavailable"
            if actual != expected:
                warnings.append(f"Hardware {key}: {actual}; reference: {expected}")
    else:
        warnings.append("Reference Apple hardware cannot be matched on this platform.")

    if args.check_server:
        def api(route, body=None):
            request = urllib.request.Request(
                "http://127.0.0.1:11434/api/" + route,
                data=None if body is None else json.dumps(body).encode(),
                headers={"Content-Type": "application/json"},
            )
            # Explicitly bypass proxies for the local-only metadata requests.
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(request, timeout=30) as response:
                return json.load(response)

        try:
            equal("Ollama version", api("version").get("version"), manifest["ollama_version"])
            models = api("tags").get("models", [])
            matching = [m for m in models if m.get("name") == "qwen3:8b"]
            digest = matching[0].get("digest") if len(matching) == 1 else "missing or ambiguous"
            equal("Model digest", digest, manifest["model_digest"])
            observed = api("show", {"model": "qwen3:8b"})
            expected = json.loads((bundle / "model_runtime.json").read_text())
            for key in ("parameters", "template", "details", "capabilities"):
                equal(f"Model {key}", observed.get(key), expected[key], show_values=False)
        except (OSError, ValueError, KeyError) as error:
            failures.append(f"Ollama metadata check failed ({type(error).__name__}).")
    else:
        warnings.append("Ollama metadata was not checked; use --check-server before inference.")

    warnings.append("Tokenizer bytes checked; ensure the adapter's HF cache resolves this revision.")
    warnings.append("Reference annotations were not sealed at capture; fixed-reference replay is unavailable.")
    for warning in warnings:
        print(f"NOTE: {warning}")
    for failure in failures:
        print(f"FAIL: {failure}")
    print(f"{'FAIL' if failures else 'PASS'}: {checks} comparisons; {len(failures)} failures.")
    print("This checks recorded inputs and metadata, not identical generation or completed ACE benchmarks.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
