# White-paper scaffold

`writeup-scaffold.md` is an outline with cited material under each
heading, ready for a person to expand. It is not a finished paper.

## Sections

| Section | Holds | Register |
|---|---|---|
| Abstract | Four sentences: problem, approach, main finding, main limitation | engineering |
| Problem | What needed solving and for whom, from the earliest entries | product if product entries state it |
| Background | Constraints and prior state that shaped the approach | engineering |
| Approach | The design as it ended, by epoch; excerpts allowed | engineering |
| Findings | One `###` subsection per finding | per finding |
| Discussion | What the findings mean together; reversals and their cost | engineering |
| Limitations | Every `<!-- gap -->` in the document, plus thin spots | engineering |
| Conclusion | Three sentences: what holds, what does not, what is next | engineering |
| Evidence appendix | Table of every cited entry: id, date, tag, title | none |

## Findings subsections

Each subsection:

1. States the finding in its first sentence.
2. Gives the evidence with citations; excerpts allowed.
3. Ends its prose with the consequence of the finding.
4. Closes with `**Cost:**`, `**Complexity:**`, `**Risk:**`, one sentence
   each.

`check` warns on any Findings paragraph with no citation and no
`(inferred)` label.

## Register

- Impersonal third person. No "we", "I", or "you".
- Past tense for events; present tense for what still holds.
- No contractions.
- Numbers with units as the entries give them. Do not round or convert.

## Gaps

Mark each gap where it occurs, `<!-- gap: no measurement of X after the
change -->`, and list it under Limitations. A section with nothing to say
keeps its heading and one gap marker.
