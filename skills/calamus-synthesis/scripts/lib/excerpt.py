"""Verbatim code excerpts with provenance. Refuses paths outside the repository, binaries, and secrets."""
import ast
import datetime
import fnmatch
import os
import re
import subprocess

import base

LANG = {".py": ("python", "#"), ".sh": ("bash", "#"), ".bash": ("bash", "#"), ".js": ("javascript", "//"),
        ".mjs": ("javascript", "//"), ".ts": ("typescript", "//"), ".tsx": ("tsx", "//"), ".go": ("go", "//"),
        ".rs": ("rust", "//"), ".java": ("java", "//"), ".kt": ("kotlin", "//"), ".swift": ("swift", "//"),
        ".c": ("c", "//"), ".h": ("c", "//"), ".cpp": ("cpp", "//"), ".rb": ("ruby", "#"),
        ".json": ("json", None), ".yml": ("yaml", "#"), ".yaml": ("yaml", "#"), ".toml": ("toml", "#"),
        ".md": ("markdown", None), ".sql": ("sql", "--"), ".css": ("css", None), ".html": ("html", None)}
MARKER_RE = re.compile(r"^<!-- excerpt: (?P<spec>\S+) \[(?P<id>[^\]]+)\] -->$")
SPEC_RE = re.compile(r"^(?P<path>\S+)@(?P<rev>[^@:\s]+):(?:L(?P<a>\d+)-L(?P<b>\d+)|(?P<diff>diff)):max(?P<max>\d+)$")
JOURNAL_RE = re.compile(r"^journal:max(?P<max>\d+)$")
DEF_RE = (r"^(\s*)(?:export\s+)?(?:pub\s+)?(?:async\s+)?"
          r"(?:def|class|function|func|fn|struct|interface|type)\s+%s\b|^(\s*)(?:function\s+)?%s\s*\(\)")


class Refused(Exception):
    """Exit 4: the excerpt would leave the repository, be binary, or expose a secret."""


def _git(root, *args):
    try:
        return subprocess.run(["git", "-C", root] + list(args), capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as e:
        raise base.UsageError("git failed: %s" % e)


def is_repo(root):
    try:
        p = subprocess.run(["git", "-C", root, "rev-parse", "--is-inside-work-tree"],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return False
    return p.returncode == 0 and p.stdout.strip() == "true"


def safe_path(root, path):
    norm = (path or "").replace("\\", "/")
    if (not norm or os.path.isabs(norm) or norm.startswith("~") or re.match(r"^[A-Za-z]:", norm)
            or ".." in norm.split("/") or re.search(r"\s", norm)):
        raise Refused("path must be repository-relative, without '..' or whitespace")
    real_root = os.path.realpath(root)
    if not os.path.realpath(os.path.join(real_root, norm)).startswith(real_root + os.sep):
        raise Refused("path leaves the repository")
    return norm


def resolve_commit(root, path, when, grace_hours):
    until = when + datetime.timedelta(hours=grace_hours)
    p = _git(root, "log", "-1", "--format=%H %cs", "--before=" + until.strftime("%Y-%m-%dT%H:%M:%S"),
             "HEAD", "--", path)
    out = p.stdout.decode("utf-8", "replace").split()
    if p.returncode != 0 or len(out) != 2:
        return None
    return {"commit": out[0][:12], "date": out[1]}


def _rev(root, rev):
    p = _git(root, "rev-parse", "--verify", "--quiet", rev + "^{commit}")
    if p.returncode != 0:
        raise base.UsageError("unknown revision %s" % rev)
    return p.stdout.decode().strip()[:12]


def _lang(path):
    return LANG.get(os.path.splitext(path)[1].lower(), ("", None))


def _split(text):
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _read(root, rev, path):
    if rev == "working-tree":
        full = os.path.join(root, path)
        if os.path.islink(full) or (os.path.exists(full) and not os.path.isfile(full)):
            raise Refused("%s is not a regular file" % path)
        if not os.path.isfile(full):
            raise Refused("%s not found in the working tree" % path)
        with open(full, "rb") as f:
            data = f.read()
    else:
        entry = _git(root, "ls-tree", rev, "--", path).stdout.decode("utf-8", "replace").split()
        if not entry:
            raise Refused("%s not found at commit %s" % (path, rev[:7]))
        if entry[1] != "blob" or entry[0] == "120000":
            raise Refused("%s is not a regular file at commit %s" % (path, rev[:7]))
        p = _git(root, "show", "%s:%s" % (rev, path))
        if p.returncode != 0:
            raise Refused("%s not found at commit %s" % (path, rev[:7]))
        data = p.stdout
    if b"\0" in data:
        raise Refused("%s is binary" % path)
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise Refused("%s is not UTF-8 text" % path)


def symbol_span(text, path, name):
    lines = _split(text)
    if path.endswith(".py"):
        try:
            tree = ast.parse(text)
        except (SyntaxError, ValueError) as e:
            raise base.UsageError("cannot parse %s for --symbol (%s); use --lines" % (path, e.__class__.__name__))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name:
                return min([node.lineno] + [d.lineno for d in node.decorator_list]), node.end_lineno
        raise base.UsageError("symbol %s not found in %s" % (name, path))
    pat = re.compile(DEF_RE % (re.escape(name), re.escape(name)))
    for i, line in enumerate(lines):
        m = pat.match(line)
        if not m:
            continue
        indent = len(m.group(1) if m.group(1) is not None else m.group(2))
        depth, opened, end = 0, False, len(lines)
        for j in range(i, len(lines)):
            depth += lines[j].count("{") - lines[j].count("}")
            opened = opened or "{" in lines[j]
            if opened and depth <= 0:
                end = j + 1
                break
            stripped = lines[j].strip()
            if not opened and j > i and stripped and len(lines[j]) - len(lines[j].lstrip()) <= indent:
                end = j
                break
        while end > i + 1 and not lines[end - 1].strip():
            end -= 1
        return i + 1, end
    raise base.UsageError("symbol %s not found in %s" % (name, path))


def _check_secret_file(path, text, style):
    name = os.path.basename(path)
    if any(fnmatch.fnmatch(name, pat) for pat in base.items(style, "secret_file")):
        raise Refused("%s is a key or environment file; excerpt withheld" % path)
    if any(re.search(m, text) for m in base.items(style, "secret_file_marker")):
        raise Refused("%s holds a private key; excerpt withheld" % path)


def _check_secrets(lines, style):
    pats = [re.compile(p) for p in base.items(style, "secret_pattern")]
    for n, line in enumerate(lines, 1):
        if any(p.search(line) for p in pats):
            raise Refused("line %d of the selection matches a secret pattern; excerpt withheld" % n)


def _elide(lines, max_lines, comment):
    if len(lines) <= max_lines:
        return lines
    head = max_lines // 2
    tail = max_lines - head - 1
    note = "... %d lines omitted ..." % (len(lines) - head - tail)
    indent = re.match(r"\s*", lines[head]).group(0)
    return lines[:head] + [indent + (comment + " " if comment else "") + note] + lines[len(lines) - tail:]


def _block(spec, rid, caption, lang, lines):
    body = "\n".join(lines)
    fence = "`" * max(3, max([len(r) for r in re.findall(r"`+", body)] or [0]) + 1)
    return "<!-- excerpt: %s [%s] -->\n%s\n\n%s%s\n%s\n%s\n" % (spec, rid, caption, fence, lang, body, fence)


def excerpt(root, rec, conf, style, path=None, symbol=None, lines=None, journaled=False,
            at=None, diff=False, frm=None, max_lines=None):
    max_lines = int(max_lines or base.num(conf, "excerpt_max_lines"))
    if max_lines < 3:
        raise base.UsageError("--max-lines must be at least 3")
    rid = rec["id"]
    if journaled:
        code = rec.get("code") or ""
        if not code:
            raise base.UsageError("entry %s has no code field" % rid)
        files = list((rec.get("impl") or {}).get("files") or rec.get("files") or [])
        lang, comment = _lang(files[0] if files else "")
        body = _split(code.replace("\r\n", "\n"))
        _check_secrets(body, style)
        return _block("journal:max%d" % max_lines, rid, "Code recorded with the entry [%s]" % rid,
                      lang, _elide(body, max_lines, comment))
    path = safe_path(root, path)
    lang, comment = _lang(path)
    if is_repo(root):
        if not at:
            when = base.entry_time(rid, rec["date"], rec.get("legacy"))
            found = resolve_commit(root, path, when, base.num(conf, "excerpt_grace_hours"))
            if not found:
                raise Refused("no commit touches %s by the entry's time" % path)
            at = found["commit"]
        rev = _rev(root, at)
    elif diff or at:
        raise base.UsageError("--diff and --at need a Git repository")
    else:
        rev = "working-tree"
    if diff:
        base_rev = _rev(root, frm or rev + "^")
        p = _git(root, "diff", "--no-color", "--no-ext-diff", base_rev, rev, "--", path)
        text = p.stdout.decode("utf-8", "replace")
        if b"\0" in p.stdout or "Binary files" in text:
            raise Refused("%s is binary" % path)
        body = _split(text)
        body = body[next((i for i, l in enumerate(body) if l.startswith("@@")), len(body)):]
        if p.returncode != 0 or not body:
            raise base.UsageError("no change to %s between %s and %s" % (path, base_rev[:7], rev[:7]))
        try:
            _check_secret_file(path, _read(root, rev, path), style)
        except Refused as e:
            if "withheld" in str(e):
                raise
        _check_secrets(body, style)
        return _block("%s@%s..%s:diff:max%d" % (path, base_rev, rev, max_lines), rid,
                      "`%s`, changes from `%s` to `%s` [%s]" % (path, base_rev[:7], rev[:7], rid),
                      "diff", _elide(body, max_lines, None))
    text = _read(root, rev, path)
    _check_secret_file(path, text, style)
    all_lines = _split(text)
    if symbol:
        a, b = symbol_span(text, path, symbol)
    elif lines:
        a, b = lines
    else:
        raise base.UsageError("give --symbol or --lines")
    if not 1 <= a <= b <= len(all_lines):
        raise base.UsageError("lines %d-%d are outside %s (%d lines)" % (a, b, path, len(all_lines)))
    body = all_lines[a - 1:b]
    _check_secrets(body, style)
    where = "in the working tree" if rev == "working-tree" else "at `%s`" % rev[:7]
    return _block("%s@%s:L%d-L%d:max%d" % (path, rev, a, b, max_lines), rid,
                  "`%s` %s, lines %d-%d [%s]" % (path, where, a, b, rid), lang, _elide(body, max_lines, comment))


def from_spec(root, spec, rec, conf, style):
    j = JOURNAL_RE.match(spec)
    if j:
        return excerpt(root, rec, conf, style, journaled=True, max_lines=int(j.group("max")))
    m = SPEC_RE.match(spec)
    if not m:
        raise base.UsageError("malformed excerpt marker %s" % spec)
    if m.group("diff"):
        frm, _, to = m.group("rev").partition("..")
        return excerpt(root, rec, conf, style, path=m.group("path"), at=to, diff=True, frm=frm,
                       max_lines=int(m.group("max")))
    at = None if m.group("rev") == "working-tree" else m.group("rev")
    return excerpt(root, rec, conf, style, path=m.group("path"), at=at,
                   lines=(int(m.group("a")), int(m.group("b"))), max_lines=int(m.group("max")))


def markers(md):
    out = []
    for n, line in enumerate(md.split("\n"), 1):
        m = MARKER_RE.match(line)
        if m:
            out.append((n, m))
    return out


def verify(md, root, conf, style, lookup):
    errs, lines = [], md.split("\n")
    for n, m in markers(md):
        try:
            fresh = from_spec(root, m.group("spec"), lookup(m.group("id")), conf, style)
        except (Refused, base.UsageError) as e:
            errs.append((n, "excerpt cannot be re-extracted: %s" % e))
            continue
        want = fresh.rstrip("\n").split("\n")
        if lines[n - 1:n - 1 + len(want)] != want:
            errs.append((n, "excerpt differs from its source; paste a fresh calamus-synth excerpt block"))
    return errs
