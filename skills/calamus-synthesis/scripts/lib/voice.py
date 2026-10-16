"""Locate and parse a voice profile (spec 9.1, 9.2). Profiles are data; nothing in them runs."""
import os

import base

SCALARS = ("long_words", "short_words", "bullet_ratio_max", "max_citations")
LISTS = ("stock_phrase", "filler_transition", "hedge", "intensifier")


def locate(root, explicit=None, env=None):
    env = os.environ if env is None else env
    if explicit:
        if not os.path.isfile(explicit):
            raise base.UsageError("voice profile not found: %s" % explicit)
        return explicit
    xdg = env.get("XDG_CONFIG_HOME") or os.path.join(env.get("HOME", ""), ".config")
    for path in (os.path.join(root, ".calamus", "voice.md"), os.path.join(xdg, "calamus", "voice.md")):
        if os.path.isfile(path):
            return path
    return None


def front_matter(path):
    """Parse the leading --- block of `key: value` lines into {key: [values]}."""
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    if not lines or lines[0].strip() != "---":
        return {}
    out = {}
    for n, line in enumerate(lines[1:], 2):
        s = line.strip()
        if s == "---":
            return out
        if not s or s.startswith("#"):
            continue
        if ":" not in s:
            raise base.UsageError("%s:%d: expected key: value" % (os.path.basename(path), n))
        key, value = (part.strip() for part in s.split(":", 1))
        out.setdefault(key, []).append(value)
    raise base.UsageError("%s: front matter is not closed with ---" % os.path.basename(path))


def merged_style(style, profile_path):
    """Style conf with the profile's bands overriding and its phrase lists appended.
    Secret patterns and unknown keys are never taken from a profile."""
    out = {k: list(v) for k, v in style.items()}
    if not profile_path:
        return out
    for key, values in front_matter(profile_path).items():
        if key.startswith("band_") or key in SCALARS:
            out[key] = values[-1:]
        elif key in LISTS:
            out[key] = out.get(key, []) + values
    return out
