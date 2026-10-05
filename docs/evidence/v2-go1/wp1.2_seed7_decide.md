# WP1.2 evidence: seed-7 truth pairs before and after dictionary v2 (DEC-34)

SYNTHETIC DATA. Written by the team that wrote the rules; optimistic by construction; not a
measure of performance on real CPSE data. Truth pairs only (no candidate generation yet).

Command: `python -m app.cli generate --seed 7 --out /tmp/s7 && python -m app.cli decide --file /tmp/s7`

| Truth label \ verdict | before (v1, 4 Oct) | after (v2, 5 Oct) |
|---|---|---|
| EQUIVALENT → IDENTICAL | 108 | 178 |
| EQUIVALENT → EQUIVALENT | 789 | 1,166 |
| EQUIVALENT → INSUFFICIENT_DATA | 1,265 | 822 |
| EQUIVALENT → NOT_EQUIVALENT (false veto) | 4 | 0 |
| NOT_EQUIVALENT_HARD → EQUIVALENT / IDENTICAL (false merge) | 0 | 0 |
| NOT_EQUIVALENT_HARD → NOT_EQUIVALENT | 967 | 1,029 |
| NOT_EQUIVALENT_HARD → INSUFFICIENT_DATA | 250 | 188 |

Evidence rows without a rule ID or rule text: 0 (both runs).

Remaining missing core values on true-equivalent pairs (after): 979 not written in the text
(generator drops; only ask-don't-guess can fill them), 368 written but not read (mostly records
without a category word such as `25NB 300# WCB BW`: the ML classifier of Go 2).
