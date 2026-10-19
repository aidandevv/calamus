#!/usr/bin/env python3
"""Portable timeout: timeout.py SECONDS -- COMMAND [ARGS...]

Runs COMMAND in its own process group with inherited stdio. On timeout it
sends SIGTERM to the whole group, then SIGKILL after two seconds, and exits
124. If this process is itself terminated, the group is killed first.
"""
import os
import signal
import subprocess
import sys

GRACE = 2.0


def kill_group(proc):
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(proc.pid, sig)
        except (ProcessLookupError, PermissionError):
            return
        try:
            proc.wait(timeout=GRACE)
            return
        except subprocess.TimeoutExpired:
            continue


def main(argv):
    if len(argv) < 3 or argv[1] != "--":
        sys.stderr.write("usage: timeout.py SECONDS -- COMMAND [ARGS...]\n")
        return 125
    try:
        secs = float(argv[0])
    except ValueError:
        sys.stderr.write("timeout.py: bad duration %r\n" % argv[0])
        return 125
    try:
        proc = subprocess.Popen(argv[2:], start_new_session=True)
    except OSError as e:
        sys.stderr.write("timeout.py: %s\n" % e)
        return 127

    def on_term(signum, _frame):
        kill_group(proc)
        sys.exit(128 + signum)

    signal.signal(signal.SIGTERM, on_term)
    signal.signal(signal.SIGINT, on_term)
    try:
        return proc.wait(timeout=secs)
    except subprocess.TimeoutExpired:
        kill_group(proc)
        return 124


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
