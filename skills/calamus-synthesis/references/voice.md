# Voice

A voice profile is the author's own description of how their writing
sounds. It is optional and never stored in the repository.

## Locate

First match wins:

1. `--voice <path>` given to `calamus-synth check`.
2. `.calamus/voice.md` in the project.
3. `$XDG_CONFIG_HOME/calamus/voice.md`, or `~/.config/calamus/voice.md`.

No profile: write neutral, plain prose in the default bands and skip the
voice pass.

## Format

Copy `assets/voice.template.md`. The front matter holds `key: value`
lines that the lint reads as data:

- `band_*` keys override the default bands.
- `stock_phrase`, `filler_transition`, `hedge`, `intensifier` add to the
  lint lists. Repeat a key to add several.

The body holds sections for the model, not the lint:

- `## Register: engineering` and `## Register: product`: rules,
  preferred vocabulary, and short exemplars of the author's own text.
- `## Spoken`: reserved for talk outlines; unused.

Never copy third-party text into a profile.

## Apply

1. Finish the neutral draft and its revision passes first.
2. Run `calamus-synth snapshot <dir>`.
3. Rewrite prose only, following the profile's register for each file.
   Leave untouched: headings, tables, citations, dates, numbers,
   backticked paths, markers, excerpt blocks, and diagram blocks.
4. Run `calamus-synth check <dir> --voice <profile>`. A `fidelity` failure
   means the rewrite changed a fact. Restore the snapshot copy of that
   file from `.calamus/state/synth/<slug>/` and report the failure.
