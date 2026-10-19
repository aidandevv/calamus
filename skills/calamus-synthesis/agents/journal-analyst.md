# Journal analyst brief

Task for a subagent with file access. The caller supplies three values:
the path to `facts.json`, the path to the calamus-synthesis skill
directory, and the mode (`full`, `focus <id or topic>`, or
`since <date>`).

1. Read `references/procedure.md` in the skill directory and follow it.
   It is the complete procedure.
2. Read `facts.json`. Open full entries only with the calamus skill's
   `calamus-query --id <id>`; do not read whole journals.
3. Write `analysis.json` next to `facts.json`, then run
   `calamus-synth diagrams <dir>` from the skill's `scripts/` directory
   until it exits 0.
4. Return: the path of `analysis.json`; each phase name with its dates;
   each pivot with rank, label, and one-sentence rationale; and every gap
   found. Do not draft the writeups and do not return journal text.

Never write to a journal. Never invent a pivot without cited sources.
