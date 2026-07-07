# Rete Algorithm — Python Implementation

A Python implementation of the [Rete algorithm](https://en.wikipedia.org/wiki/Rete_algorithm) for production-rule systems, using Google's [Common Expression Language](https://cel.dev/) (CEL) for conditions and [JSON Schema](https://json-schema.org/) for fact validation.

## Technologies

- **Python 3.14** — type-hinted throughout with native `type` alias syntax
- **[Common Expression Language](https://python-common-expression-language.readthedocs.io/)** (`common-expression-language` ≥0.7.0) — Rust-backed CEL evaluation via `cel.compile()` and `Program.variables()`
- **[JSON Schema](https://python-jsonschema.readthedocs.io/)** (`jsonschema` ≥4.26) — validates input facts against per-type schemas on `assert_fact`
- **argparse** — CLI for loading rules, actions, schemas, and facts from JSON files

## Features

- **Alpha network** — `RootNode` → `SelectorNode` (type filter) → `AlphaNode` (intra-fact CEL conditions). Facts that pass all assigned CELs propagate to the beta network.
- **Beta network** — `BetaNode`s chain linearly, each joining tokens from the left memory with facts from the right memory via an optional CEL join expression. Unconditional joins succeed for every pairing.
  - N fact types → N−1 joiner `BetaNode`s
  - Single-type rules → 1 pass-through `BetaNode` (no right input)
- **Schema validation** — every asserted fact is validated against its type's JSON Schema before entering the network. Rejected facts are caught and reported.
- **External file loading** — rules, actions, schemas, and test facts are loaded from JSON files:
  - `rules.json` — array of rule objects with CEL expressions in an `"all"` conjunction
  - `actions.json` — array of action descriptors keyed by `id`
  - `schemas.json` — top-level properties referencing `$defs` per fact type
  - `test-facts.json` — array of `{ fact_type, fact_data }` objects
- **CLI** — `--rules`, `--schemas`, `--actions`, `--facts` flags with sensible defaults

## Quick Start

```bash
uv sync                        # install dependencies (common-expression-language, jsonschema)
uv pip install -e .            # install the rete package in editable mode
uv run python rete/main.py     # run with default data/ files
```

Only the matching fact combinations fire rules. Invalid facts (schema violations, unknown types) are reported without crashing.

## Rule Format

```json
[
  {
    "id": "senior-ca-review",
    "description": "Senior beneficiaries treated in California require review.",
    "expression": {
      "all": [
        {"cel": "beneficiary.age >= 65"},
        {"cel": "doctor.state == 'CA'"}
      ]
    },
    "action": "flag-manual-review"
  }
]
```

Each CEL expression is a **single binary test** — either a field-vs-literal filter (`beneficiary.age >= 65`) or a field-vs-field join condition (`claim.beneficiary_id == beneficiary.id`). The `all` array is a conjunction: every CEL must pass.

### Expression Classification

| References | Classification | Placed on |
|---|---|---|
| 1 fact type | Intra-fact filter | `AlphaNode` for that type |
| 2+ fact types | Cross-fact join | `BetaNode` at the join point |

## Architecture

```
Fact → RootNode → SelectorNode (by type) → AlphaNode (CEL filters)
                                                  ↓
                                         DummyTopNode / BetaRightAdapter
                                                  ↓
                                            BetaNode chain
                                          (joins via CEL or unconditional)
                                                  ↓
                                            TerminalNode (fires)
```

- **AlphaNode** evaluates intra-fact CEL conditions. A fact only passes if it satisfies all assigned expressions.
- **BetaNode** joins left-memory tokens with right-memory facts using an optional join CEL. Joiner nodes (`has_right_input=True`) wait for both sides before propagating. Single-type rules use a pass-through beta (`has_right_input=False`).
- **SchemaValidator** resolves `$ref` → `$defs` from `schemas.json` and validates every fact at `assert_fact` time.

## Data Files

### `schemas.json`

Uses JSON Schema Draft 2020-12 with `$defs` referenced from top-level `properties`:

```json
{
  "properties": {
    "beneficiary": { "$ref": "#/$defs/beneficiary" }
  },
  "$defs": {
    "beneficiary": {
      "type": "object",
      "properties": { "age": { "type": "integer" } },
      "required": ["age"]
    }
  }
}
```

### `test-facts.json`

```json
[
  { "fact_type": "beneficiary", "fact_data": { "age": 70 } },
  { "fact_type": "doctor", "fact_data": { "state": "CA" } }
]
```

## CLI

```bash
uv run python rete/main.py \
  --rules data/rules.json \
  --schemas data/schemas.json \
  --actions data/actions.json \
  --facts data/test-facts.json
```

All flags default to `data/*.json` and can be omitted.
