# Atlas fixture author notes

Atlas helps an analyst reach one reproducible CSV result quickly. Its contextual
README guidance requires observing the real application before writing an input,
command, and output example. No resulting consumer README is supplied. Its
ordinary `trace-csv` skill supports changes to that application, with a small
input-case reference. It contains no standards adoption behavior.

Select publisher `atlas` and profile `full` for public contribution policy and
two-space editor configuration. Select `employer` for four-space editor
configuration and contextual guidance that points to the existing employer
contribution document. `employer` excludes the whole contribution declaration:
its target, source, fix, and check must all disappear from active operations.
The contribution fix would replace an employer document if wrongly executed,
and its public-policy check would reject that document. Trace records identify
both operations unambiguously.

Defaults use eight-space editor configuration and an intentionally failing
`atlas-obsolete-default-check`. Both profiles replace that complete declaration;
neither inherits the obsolete check. This makes shallow merging observable.
Absent profile entries inherit normally, including the whole CSV work skill.

The `data-contract` concern spans `.csv-summary.json` and
`docs/data-contract.md`. Its fix preserves unrelated configuration keys and
writes the owned transport assumptions and document; its check verifies both.
This concern describes file transport, not unobserved numeric application
behavior. Commands require Python 3 and assert the exact literal argument
`Atlas input; $(touch SHOULD_NOT_EXIST) & [literal]`. Each command consumes the
resolved-selection stdin envelope and appends `.author-trace.jsonl` in consumer
cwd. That trace is proof instrumentation rather than consumer policy.

`standards.yaml` is JSON text, a dependency-free YAML subset. All sources and
guidance paths are relative to this publisher directory. Command paths use the
shared `{inputs}` publisher root substitution. Profile resolution is complete
declaration replacement or exclusion, with default inheritance for absent IDs.
The defaults deliberately include a failing check to expose replacement errors;
normal example selections always name `full` or `employer`.
