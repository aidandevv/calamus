"""Shared helpers for the calamus-* command entry points."""
import os
import subprocess
import sys


def project_root(explicit=None):
    base = explicit or os.getcwd()
    try:
        out = subprocess.run(["git", "-C", base, "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=10)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return os.path.abspath(base)


def die(msg, code=1):
    sys.stderr.write(msg.rstrip("\n") + "\n")
    sys.exit(code)


def journals_arg(value):
    return ["engineering", "product"] if value in (None, "both") else [value]
