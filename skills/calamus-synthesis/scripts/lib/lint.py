"""Advisory style lint for writeups (spec 9.4, 9.6). Reports findings; never rewrites."""
import re

import base

NARRATIVE = ("overview.md", "phases.md", "pivots.md", "insights.md", "brief.md")
FENCE_RE = re.compile(r"^(`{3,}|~{3,})")
ID_RE = re.compile(r"\b\d{8}-\d{4}-[0-9a-z]{4,}\b")
CITE_RE = re.compile(r"\s*\[[^\]]*\d{8}-\d{4}-[0-9a-z]+[^\]]*\]")
CODE_SPAN = re.compile(r"`[^`]*`")
LIST_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
SENT_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\[(\"`])")
WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’-]*")
FIRST_PERSON = re.compile(r"\b(?:I|[Mm]e|[Mm]y|[Mm]ine|[Ww]e|[Uu]s|[Oo]ur|[Oo]urs)\b")
CONTRACTION = re.compile(r"\b\w+n['’]t\b|\b\w+['’](?:re|ve|ll|m|d)\b|\b(?:it|that|there|what|here|let)['’]s\b", re.I)
VAGUE = re.compile(r"^(?:This|It)\s+(?:is|was|means|meant|shows|showed|allows|allowed|makes|made|ensures|ensured|"
                   r"enables|enabled|helps|helped|provides|provided|has|had|will|would|can|could)\b")
CONTRAST = (re.compile(r"\bnot only\b.*\bbut also\b", re.I),
            re.compile(r"\bnot just\b[^.]*,\s*but\b", re.I),
            re.compile(r"\b(?:it['’]?s|it is) not\b[^.]*[,;]\s*(?:it['’]?s|it is)\b", re.I))
TAG_RE = re.compile(r"\b(?:CP|PI)-[A-Z][A-Z-]*\b")


def outside_code(md):
    """(line_no, line) for lines outside fenced blocks, excerpt markers, and excerpt captions."""
    out, fence, caption = [], None, False
    for n, line in enumerate(md.split("\n"), 1):
        s = line.strip()
        if fence:
            if s.startswith(fence) and not s.strip("`~"):
                fence = None
            continue
        m = FENCE_RE.match(s)
        if m:
            fence = m.group(1)
            continue
        if s.startswith("<!-- excerpt:"):
            caption = True
            continue
        if caption and s:
            caption = False
            continue
        out.append((n, line))
    return out


def units(md):
    """Prose paragraphs and list items: [{"line", "text", "list", "lines"}]."""
    out, cur, comment = [], None, False
    for n, line in outside_code(md):
        s = line.strip()
        if comment:
            comment = "-->" not in s
            continue
        if s.startswith("<!--"):
            comment = "-->" not in s
            cur = None
            continue
        if not s or s.startswith("#") or s.startswith("|"):
            cur = None
            continue
        is_list = bool(LIST_RE.match(line))
        if cur is None or is_list or cur["list"] != is_list and not line.startswith(" "):
            cur = {"line": n, "text": LIST_RE.sub("", line).strip(), "list": is_list, "lines": 1}
            out.append(cur)
        else:
            cur["text"] += "\n" + s
            cur["lines"] += 1
    return out


def sentences(us):
    out = []
    for u in us:
        text = u["text"]
        starts = [0] + [m.end() for m in SENT_END.finditer(text)]
        for a, b in zip(starts, starts[1:] + [len(text)]):
            s = text[a:b].strip()
            if s:
                out.append((u["line"] + text[:a].count("\n"), s, u))
    return out


def plain(s):
    return CODE_SPAN.sub("code", CITE_RE.sub("", s)).replace("\n", " ")


def _range(value):
    lo, _, hi = value.partition("-")
    return (float(lo), float(hi)) if hi else (None, float(lo))


def _words(s):
    return len(WORD_RE.findall(plain(s)))


def bands(us, sents, style):
    out = []
    num = lambda k: base.num(style, k)
    prose = [x for x in sents if not x[2]["list"]]
    if len(prose) >= num("band_min_sentences"):
        lengths = [_words(s) for _, s, _ in prose]
        n = float(len(lengths))
        mean = sum(lengths) / n
        lo, hi = _range(style["band_mean_len"][-1])
        if not lo <= mean <= hi:
            out.append((1, "band-mean-length", "mean %.1f words; band %g-%g" % (mean, lo, hi)))
        long_pct = 100 * sum(1 for x in lengths if x > num("long_words")) / n
        if long_pct > num("band_long_pct_max"):
            out.append((1, "band-long-sentences", "%.0f%% over %d words" % (long_pct, num("long_words"))))
        lo, hi = _range(style["band_short_pct"][-1])
        short_pct = 100 * sum(1 for x in lengths if x <= num("short_words")) / n
        if not lo <= short_pct <= hi:
            out.append((1, "band-short-sentences", "%.0f%% at or under %d words; band %g-%g%%"
                        % (short_pct, num("short_words"), lo, hi)))
        paras = [u for u in us if not u["list"]]
        per = sum(1 for x in prose) / float(len(paras))
        lo, hi = _range(style["band_para_sents"][-1])
        if not lo <= per <= hi:
            out.append((1, "band-paragraph-length", "%.1f sentences per paragraph; band %g-%g" % (per, lo, hi)))
    for rule, key, count in (("band-em-dash", "band_em_dash_max", lambda s: s.count("—")),
                             ("band-exclamation", "band_exclaim_max", lambda s: plain(s).count("!")),
                             ("band-first-person", "band_first_person_max", lambda s: len(FIRST_PERSON.findall(plain(s)))),
                             ("band-contraction", "band_contraction_max", lambda s: len(CONTRACTION.findall(plain(s))))):
        hits = [(line, s) for line, s, _ in sents if count(s)]
        if sum(count(s) for _, s in hits) > num(key):
            out += [(line, rule, s) for line, s in hits]
    return out


def lint(md, fname, style):
    us = units(md)
    sents = sentences(us)
    found = []
    add = lambda line, rule, text: found.append({"file": fname, "line": line, "rule": rule, "text": text[:80]})
    hedges = base.items(style, "hedge")
    for line, s, _ in sents:
        p = plain(s)
        low = p.lower()
        for phrase in base.items(style, "stock_phrase"):
            if re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(phrase.lower()), low):
                add(line, "stock-phrase", phrase)
        for t in base.items(style, "filler_transition"):
            if re.match(r"^%s\b" % re.escape(t), p):
                add(line, "filler-transition", t)
        if sum(len(re.findall(r"\b%s\b" % re.escape(h), low)) for h in hedges) >= 2:
            add(line, "stacked-hedge", p)
        if VAGUE.match(p):
            add(line, "vague-referent", p)
        if any(c.search(p) for c in CONTRAST):
            add(line, "contrast-frame", p)
        if not re.search(r"\d", p):
            for w in base.items(style, "intensifier"):
                if re.search(r"\b%s\b" % re.escape(w), low):
                    add(line, "empty-intensifier", w)
        m = TAG_RE.search(p)
        if m:
            add(line, "tag-leak", m.group(0))
        if len(ID_RE.findall(s)) > base.num(style, "max_citations"):
            add(line, "citation-clutter", "%d ids in one sentence" % len(ID_RE.findall(s)))
    firsts = [(line, (WORD_RE.findall(plain(s)) or [""])[0].lower()) for line, s, _ in sents]
    for i in range(2, len(firsts)):
        if firsts[i][1] and firsts[i][1] == firsts[i - 1][1] == firsts[i - 2][1]:
            add(firsts[i][0], "repeated-opener", firsts[i][1])
    if fname in NARRATIVE:
        total = sum(u["lines"] for u in us)
        listed = sum(u["lines"] for u in us if u["list"])
        if total and listed / float(total) > base.num(style, "bullet_ratio_max"):
            add(1, "bullet-heavy", "%d of %d prose lines are list items" % (listed, total))
    for line, rule, text in bands(us, sents, style):
        add(line, rule, text)
    return sorted(found, key=lambda f: (f["line"], f["rule"], f["text"]))
