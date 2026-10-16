"""Generate Mermaid diagrams from facts.json and analysis.json. Same inputs, same bytes."""
import collections

import base

ENTITIES = {'"': "#34;", ";": "#59;", "#": "#35;", "`": "#96;", "<": "#60;", ">": "#62;"}


def label(text, max_chars, timeline=False):
    """Collapse, truncate at a word boundary, and entity-escape Mermaid syntax characters."""
    text = " ".join(str(text).split())
    if len(text) > max_chars:
        cut = text[:max_chars - 1]
        text = (cut.rsplit(" ", 1)[0] if " " in cut else cut) + "…"
    table = dict(ENTITIES, **({":": "#58;"} if timeline else {}))
    return "".join(table.get(ch, ch) for ch in text)


class _Ids(object):
    def __init__(self):
        self.n = 0

    def __call__(self):
        self.n += 1
        return "n%d" % self.n


def _finish(ids, lines):
    seen = []
    for i in ids:
        if i and i not in seen:
            seen.append(i)
    return "\n".join(["%% sources: " + " ".join(seen)] + lines) + "\n"


def _phases(f, a):
    recs = {r["id"]: r for r in f["records"]}
    order = {rid: n for n, rid in enumerate(f["sequence"])}
    out = []
    for p in a.get("phases") or []:
        members = [recs[rid] for rid in f["sequence"][order[p["first"]]:order[p["last"]] + 1]]
        out.append(dict(p, members=members, start=members[0]["date"], end=members[-1]["date"]))
    return recs, out


def _n(conf, key):
    return int(base.num(conf, key))


def timeline(f, a, conf):
    recs, phases = _phases(f, a)
    maxc, cap = _n(conf, "label_max_chars"), _n(conf, "timeline_max_events")
    if not phases:
        phases = [{"name": "All entries", "members": list(f["records"])}]
    prio = {p["id"] for p in a.get("pivots") or []} | {c["id"] for c in f["candidates"]}
    lines, used = ["timeline", "    title Project timeline"], []
    for p in phases:
        lines.append("    section " + label(p["name"], maxc, timeline=True))
        members = p["members"]
        chosen = [r for r in members if r["id"] in prio][:cap]
        chosen += [r for r in members if r not in chosen][:cap - len(chosen)]
        chosen.sort(key=members.index)
        for r in chosen:
            lines.append("        %s : %s" % (r["date"], label(r["title"], maxc, timeline=True)))
            used.append(r["id"])
        if len(members) > cap:
            lines.append("        %s : and %d more" % (members[-1]["date"], len(members) - cap))
    return _finish(used, lines)


def _phase_label(p, maxc):
    return "%s<br/>%s to %s" % (label(p["name"], maxc), p["start"], p["end"])


def phases(f, a, conf):
    _, ph = _phases(f, a)
    maxc = _n(conf, "label_max_chars")
    epochs = [e for e in a.get("epochs") or [] if e.get("phases")]
    by_key = {p["key"]: p for p in ph}
    in_epoch = {k for e in epochs for k in e["phases"]}
    groups = [(e, [by_key[k] for k in e["phases"]]) for e in epochs]
    groups += [(None, [p]) for p in ph if p["key"] not in in_epoch]
    groups.sort(key=lambda g: ph.index(g[1][0]))
    collapse = len(ph) + len(epochs) > _n(conf, "max_nodes")
    pivot_label = {p["id"]: p.get("label") or p["id"] for p in a.get("pivots") or []}
    nid, used, chain = _Ids(), [], []
    lines = ["flowchart LR", "    accTitle: Phases and epochs",
             "    accDescr: %d phases in %d epochs, in order." % (len(ph), len(epochs))]
    for e, members in groups:
        used += [m for p in members for m in (p["first"], p["last"])]
        if e is None:
            n = nid()
            lines.append('    %s["%s"]' % (n, _phase_label(members[0], maxc)))
            chain.append((n, n, None))
        elif collapse:
            n = nid()
            lines.append('    %s["%s"]' % (n, label("%s (%d phase%s)" % (e["name"], len(members), "" if len(members) == 1 else "s"), maxc)))
            chain.append((n, n, e.get("ended_by")))
        else:
            lines.append('    subgraph %s["%s"]' % (nid(), label(e["name"], maxc)))
            inner = []
            for p in members:
                inner.append(nid())
                lines.append('        %s["%s"]' % (inner[-1], _phase_label(p, maxc)))
            lines += ["        %s --> %s" % pair for pair in zip(inner, inner[1:])]
            lines.append("    end")
            chain.append((inner[0], inner[-1], e.get("ended_by")))
    for (_, a_last, ended), (b_first, _, _) in zip(chain, chain[1:]):
        if ended in pivot_label:
            lines.append('    %s -->|"%s"| %s' % (a_last, label(pivot_label[ended], maxc), b_first))
            used.append(ended)
        else:
            lines.append("    %s --> %s" % (a_last, b_first))
    return _finish(used, lines)


def pivots(f, a, conf):
    maxc = _n(conf, "label_max_chars")
    ps = sorted(a.get("pivots") or [], key=lambda p: p["rank"])[:_n(conf, "max_pivots")]
    nid, used = _Ids(), []
    lines = ["flowchart TD", "    accTitle: Pivots",
             "    accDescr: %d pivots ranked by effect on later work." % len(ps)]
    for p in ps:
        s, b, t = nid(), nid(), nid()
        lines.append('    subgraph %s["%s"]' % (s, label("%d. %s" % (p["rank"], p.get("label") or p["id"]), maxc)))
        lines.append('        %s["%s"]' % (b, label("Before: " + p.get("before", ""), maxc)))
        lines.append('        %s["%s"]' % (t, label("After: " + p.get("after", ""), maxc)))
        lines.append('        %s -->|"%s"| %s' % (b, label(p.get("trigger") or "change", maxc), t))
        lines.append("    end")
        used += [p["id"]] + list(p.get("sources") or [])
    return _finish(used, lines)


def mindmap(f, a, conf):
    maxc, cap = _n(conf, "label_max_chars"), _n(conf, "max_leaves")
    recs = {r["id"]: r for r in f["records"]}
    nid, used = _Ids(), []
    lines = ["mindmap", '  %s(("Journal map"))' % nid()]
    for jname, title in (("engineering", "Engineering"), ("product", "Product")):
        mine = [r for r in f["records"] if r["journal"] == jname]
        if not mine:
            continue
        lines.append('    %s["%s"]' % (nid(), title))
        groups = collections.OrderedDict()
        for r in mine:
            groups.setdefault(r["tag"], []).append(r)
        tags = sorted(groups, key=lambda t: (-len(groups[t]), t))
        for tag in tags[:cap]:
            lines.append('      %s["%s"]' % (nid(), label(tag, maxc)))
            for r in groups[tag][:cap]:
                lines.append('        %s["%s"]' % (nid(), label(r["title"], maxc)))
                used.append(r["id"])
            if len(groups[tag]) > cap:
                lines.append('        %s["+%d more"]' % (nid(), len(groups[tag]) - cap))
        if len(tags) > cap:
            lines.append('      %s["+%d more tags"]' % (nid(), len(tags) - cap))
    links = [r for r in f["records"] if r["crosslog"]]
    if links:
        lines.append('    %s["Cross-log links"]' % nid())
        for r in links[:cap]:
            other = recs.get(r["crosslog"], {}).get("title", r["crosslog"])
            lines.append('      %s["%s"]' % (nid(), label("%s / %s" % (r["title"], other), maxc)))
            used += [r["id"], r["crosslog"]]
        if len(links) > cap:
            lines.append('      %s["+%d more"]' % (nid(), len(links) - cap))
    return _finish(used, lines)


def generate(f, a, conf):
    if a.get("mode") == "focus":
        return {"brief.mmd": pivots(f, a, conf)}
    out = {"timeline.mmd": timeline(f, a, conf), "mindmap.mmd": mindmap(f, a, conf)}
    if a.get("phases"):
        out["phases.mmd"] = phases(f, a, conf)
    if a.get("pivots"):
        out["pivots.mmd"] = pivots(f, a, conf)
    return out
