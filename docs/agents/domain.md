# Domain docs

## Layout and reading rules

This project uses a single domain context:

- `GLOSSARY.md` at the repository root defines domain terminology.
- `docs/adr/` holds architecture decision records.

Before exploring, read the glossary and ADRs relevant to the area.
If they do not exist, proceed silently. The domain-modeling skill
creates them when terms or decisions are actually resolved.

## Vocabulary

Use glossary terms consistently in issues, proposals, tests, and code.
Raise ambiguous or missing terms during domain modeling.
Keep implementation details out of the glossary.

## Decisions

If a proposal conflicts with an ADR, identify the conflict and explain
why the decision may need reopening instead of silently overriding it.
