# x12

A small, framework-independent Python library for lossless structural parsing of ANSI X12 Electronic Data Interchange documents.

`x12` discovers interchange separators, tokenizes raw messages, validates envelope structure, and produces immutable inspection summaries without interpreting transaction-specific business meaning.

## Status

`x12` is under active development.

The current release focuses on the structural layer of ANSI X12:

* separator discovery
* lossless tokenization
* immutable segment models
* ISA/GS/ST envelope parsing
* control-number validation
* declared-count validation
* structural inspection

The package currently has:

* no runtime dependencies
* 456 passing tests
* 100% statement coverage
* 100% branch coverage
* full inline type annotations

## Installation

The package is not yet published to PyPI.

For local development:

```bash
git clone https://github.com/fifoa-labs/x12.git
cd x12
uv sync --dev
```

When a published release becomes available, installation will use:

```bash
pip install x12
```

## Quick Start

```python
from pathlib import Path

from x12 import (
    inspect_x12_interchange,
    parse_x12_interchange,
    tokenize_x12,
)

payload = Path("message.x12").read_bytes()

document = tokenize_x12(payload)
interchange = parse_x12_interchange(document)
inspection = inspect_x12_interchange(interchange)
```

The resulting objects are immutable and preserve the original byte-oriented structure of the interchange.

## Core Design

The package is intentionally layered:

```text
Raw bytes
    │
    ▼
Separator discovery
    │
    ▼
Tokenizer
    │
    ▼
Immutable segment document
    │
    ▼
Envelope parser
    │
    ▼
Validated interchange
    │
    ▼
Structural inspector
```

Each layer has one responsibility and can be used independently.

## Design Goals

* ANSI X12 generic
* transaction-set agnostic
* trading-partner agnostic
* framework independent
* lossless
* deterministic
* immutable
* byte-oriented
* fully typed
* easy to audit
* thoroughly tested

## What `x12` Does

`x12` handles structural concerns common to ANSI X12 interchanges:

* Reads separator characters from the fixed-width ISA segment
* Supports custom element, repetition, component, and segment separators
* Preserves empty positional elements
* Preserves element values as raw bytes
* Preserves source segment order
* Builds immutable document and envelope models
* Parses ISA/IEA interchange envelopes
* Parses GS/GE functional groups
* Parses ST/SE transaction sets
* Validates envelope boundary ordering
* Validates matching control numbers
* Validates declared group, transaction, and segment counts
* Produces structural inventories and segment-frequency summaries

## What `x12` Does Not Do

`x12` intentionally does not interpret business semantics.

It does not:

* interpret specific transaction sets
* map application fields
* understand industry workflows
* persist data
* perform database operations
* depend on Django, Flask, FastAPI, or another framework
* validate implementation-guide-specific business rules
* convert transaction content into domain models

For example, `x12` can identify and validate a transaction set whose ST01 value is `322`, but it does not interpret the meaning of its `Q5`, `N7`, `R4`, or other business segments.

Higher-level packages should build transaction-specific behavior on top of the structural models provided here.

## Package Layout

```text
x12/
├── src/
│   └── x12/
│       ├── __init__.py
│       ├── envelopes.py
│       ├── exceptions.py
│       ├── inspection.py
│       ├── inspector.py
│       ├── parser.py
│       ├── py.typed
│       ├── segments.py
│       ├── separators.py
│       └── tokenizer.py
├── tests/
│   ├── fixtures/
│   │   └── sample_message
│   ├── test_envelopes.py
│   ├── test_exceptions.py
│   ├── test_init.py
│   ├── test_inspection.py
│   ├── test_inspector.py
│   ├── test_parser.py
│   ├── test_sample_message.py
│   ├── test_segments.py
│   ├── test_separators.py
│   └── test_tokenizer.py
├── LICENSE
├── Makefile
├── README.md
├── pyproject.toml
└── uv.lock
```

## Module Responsibilities

### `separators.py`

Discovers control characters from the fixed-width ISA header.

```python
from x12 import derive_x12_separators

separators = derive_x12_separators(payload)

print(separators.element)
print(separators.repetition)
print(separators.component)
print(separators.segment)
```

The returned `X12Separators` object contains:

* `element`
* `repetition`
* `component`
* `segment`

For interchange version `00402` and later, ISA11 is exposed as the repetition separator. Earlier versions return `None` for `repetition`.

### `tokenizer.py`

Converts raw X12 bytes into an immutable `X12Document`.

```python
from x12 import tokenize_x12

document = tokenize_x12(payload)
```

The tokenizer:

* derives separators from ISA
* splits the payload into segments
* preserves empty elements
* preserves raw element bytes
* preserves segment order
* assigns contiguous zero-based segment indexes
* ignores permitted formatting whitespace between segments
* rejects malformed segment identifiers
* rejects incomplete documents

It performs no transaction-specific interpretation.

### `segments.py`

Defines the core tokenized models:

* `X12Segment`
* `X12Document`

A segment exposes its elements using one-based X12 positions:

```python
segment = document.find_segments("ST")[0]

assert segment.element(1) == b"999"
assert segment.element(2) == b"0001"
assert segment.element(3) is None
```

Empty and missing elements are distinct:

```python
assert segment.element(1) == b""
assert segment.element(20) is None
```

`X12Document` supports direct iteration and length:

```python
for segment in document:
    print(segment.index, segment.tag)

print(len(document))
```

### `envelopes.py`

Defines immutable envelope models:

* `X12TransactionSet`
* `X12FunctionalGroup`
* `X12Interchange`

These objects organize the flat token stream into the standard X12 envelope hierarchy:

```text
ISA
└── GS
    └── ST
        ├── transaction body
        └── SE
    └── GE
└── IEA
```

They expose convenience properties for common envelope values, including:

* transaction-set code
* envelope control numbers
* implementation version
* declared counts
* actual counts
* complete ordered segment collections

### `parser.py`

Converts an `X12Document` into a validated `X12Interchange`.

```python
from x12 import parse_x12_interchange

interchange = parse_x12_interchange(document)
```

Validation includes:

* ISA as the first segment
* IEA as the final segment
* GS/GE functional-group boundaries
* ST/SE transaction-set boundaries
* exact envelope element counts
* required envelope elements
* matching ST02 and SE02
* matching GS06 and GE02
* matching ISA13 and IEA02
* SE01 transaction segment count
* GE01 transaction-set count
* IEA01 functional-group count
* invalid nested envelope segments

The parser validates envelope structure only.

### `inspection.py`

Defines immutable inspection result models:

* `X12SegmentFrequency`
* `X12TransactionInspection`
* `X12FunctionalGroupInspection`
* `X12InspectionResult`

These models provide a stable representation of structural metadata and document inventories.

### `inspector.py`

Builds an `X12InspectionResult` from a validated interchange.

```python
from x12 import inspect_x12_interchange

inspection = inspect_x12_interchange(interchange)
```

Inspection data includes:

* interchange version
* interchange control number
* usage indicator
* separators
* functional groups
* transaction-set codes
* transaction counts
* segment counts
* ordered segment tags
* unique segment tags
* repeating segment tags
* segment frequencies

Example:

```python
print(inspection.transaction_set_codes)
print(inspection.total_segment_count)
print(inspection.unique_segment_tags)
print(inspection.repeating_segment_tags)
```

## Public API

The main package-level imports are:

```python
from x12 import (
    X12Document,
    X12EnvelopeError,
    X12Error,
    X12FunctionalGroup,
    X12FunctionalGroupInspection,
    X12InspectionResult,
    X12Interchange,
    X12Segment,
    X12SegmentError,
    X12SegmentFrequency,
    X12SeparatorError,
    X12Separators,
    X12TokenizerError,
    X12TransactionInspection,
    X12TransactionSet,
    derive_x12_separators,
    inspect_x12_interchange,
    parse_x12_interchange,
    tokenize_x12,
)
```

Most applications only need:

```python
from x12 import (
    inspect_x12_interchange,
    parse_x12_interchange,
    tokenize_x12,
)
```

## Exception Hierarchy

```text
X12Error
├── X12EnvelopeError
│   └── X12SeparatorError
└── X12TokenizerError
    └── X12SegmentError
```

Example:

```python
from x12 import X12Error

try:
    document = tokenize_x12(payload)
    interchange = parse_x12_interchange(document)
except X12Error as exc:
    print(f"Invalid X12 document: {exc}")
```

Use the specialized exception types when callers need to distinguish between separator, tokenizer, segment, and envelope failures.

## Byte-Oriented API

The public parsing API accepts `bytes`, not text strings.

```python
payload = path.read_bytes()
document = tokenize_x12(payload)
```

This is intentional.

X12 separators are single-byte structural values, and fixed-width ISA offsets are defined at the byte level. Keeping the parser byte-oriented avoids accidental decoding, normalization, or whitespace changes before structural parsing is complete.

Applications may decode individual elements later using the encoding appropriate for their trading partner or implementation guide.

## Immutability

All core models are frozen dataclasses with slots.

This includes:

* separators
* segments
* documents
* transaction sets
* functional groups
* interchanges
* inspection results

Immutability makes parsed results:

* deterministic
* hashable
* safe to share
* difficult to modify accidentally
* easier to reason about during validation and testing

## Type Information

The package ships with a `py.typed` marker and inline type annotations.

Type checkers can use the installed package directly:

```python
from x12 import X12Interchange, parse_x12_interchange
```

The project is checked with mypy in strict mode.

## Development

This project uses:

* uv
* pytest
* pytest-cov
* pytest-xdist
* Ruff
* mypy
* build
* Twine

Install development dependencies:

```bash
make sync
```

Run the test suite:

```bash
make test
```

Run tests in parallel:

```bash
make test-fast
```

Run coverage:

```bash
make coverage
```

Run linting:

```bash
make lint
```

Check formatting:

```bash
make format-check
```

Apply formatting and safe fixes:

```bash
make format
```

Run type checking:

```bash
make typecheck
```

Run the complete local validation suite:

```bash
make check
```

## Testing

The test suite covers:

* separator extraction
* custom separators
* legacy and modern ISA versions
* malformed fixed-width ISA segments
* lossless tokenization
* empty positional elements
* inter-segment formatting whitespace
* invalid segment identifiers
* immutable model invariants
* envelope ordering
* missing envelope boundaries
* nested envelope failures
* envelope control-number matching
* declared-count validation
* inspection summaries
* segment-frequency ordering
* generic complete-message fixture parsing
* package public API exports
* wheel-safe type metadata

Current results:

```text
456 tests passed
597 statements covered
158 branches covered
100% statement coverage
100% branch coverage
```

The test fixture is synthetic and generic. It contains no production customer, carrier, location, phone, shipment, or equipment information.

## Building the Package

Build both the source distribution and wheel:

```bash
make build
```

Validate distribution metadata:

```bash
make check-dist
```

Inspect the wheel contents:

```bash
make wheel-contents
```

Install the wheel into a temporary clean environment:

```bash
make install-wheel
```

The built wheel should include:

```text
x12/__init__.py
x12/envelopes.py
x12/exceptions.py
x12/inspection.py
x12/inspector.py
x12/parser.py
x12/py.typed
x12/segments.py
x12/separators.py
x12/tokenizer.py
```

It should not include tests, development caches, coverage data, or application-specific code.

## Extension Guidelines

Future additions may include:

* serialization
* message builders
* diagnostic formatting
* pretty printing
* streaming tokenization
* implementation-guide extension interfaces

Any addition to the core package should remain:

* generic
* structural
* deterministic
* framework independent
* transaction-set agnostic

Transaction-specific parsers should live in separate packages or higher-level application layers.

## Guiding Principle

If a feature requires knowing what a segment means, it does not belong in the core `x12` package.

The core library understands structure.

Higher-level integrations understand meaning.

## License

MIT
