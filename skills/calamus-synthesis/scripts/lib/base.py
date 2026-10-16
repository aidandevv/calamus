"""Shared setup for calamus-synth: sibling import, config parsing, entry times."""
import datetime
import os
import re
import sys

LIB = os.path.dirname(os.path.realpath(__file__))
SKILL = os.path.dirname(os.path.dirname(LIB))
ASSETS = os.path.join(SKILL, "assets")
CALAMUS_LIB = os.path.join(os.path.dirname(SKILL), "calamus", "scripts", "lib")
ID_RE = re.compile(r"^(\d{8})-(\d{4})-[0-9a-z]+$")


class MissingSibling(Exception):
    """Exit 2: the calamus skill is not installed next to this one."""


class UsageError(Exception):
    """Exit 2: bad arguments or unreadable input."""


def use_calamus():
    """Put the sibling calamus engine on sys.path, or raise MissingSibling."""
    if not os.path.isfile(os.path.join(CALAMUS_LIB, "records.py")):
        raise MissingSibling("the calamus skill is missing; install it next to calamus-synthesis")
    if CALAMUS_LIB not in sys.path:
        sys.path.insert(0, CALAMUS_LIB)


def load_conf(path):
    """Parse `key = value` lines into {key: [values]}. Never sourced or evaluated."""
    conf = {}
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise UsageError("%s:%d: expected key = value" % (os.path.basename(path), n))
            key, value = (part.strip() for part in line.split("=", 1))
            conf.setdefault(key, []).append(value)
    return conf


def num(conf, key):
    return float(conf[key][-1])


def items(conf, key):
    return list(conf.get(key, []))


def default_conf(name):
    return load_conf(os.path.join(ASSETS, name))


def entry_time(rec_id, date, legacy=False):
    """When an entry was logged; legacy and timeless ids resolve to the end of their date."""
    m = ID_RE.match(rec_id or "")
    if m and not legacy and m.group(2) != "0000":
        return datetime.datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M")
    return datetime.datetime.strptime(date, "%Y-%m-%d").replace(hour=23, minute=59)
