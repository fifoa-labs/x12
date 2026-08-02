# ansi-x12

[![PyPI version](https://img.shields.io/pypi/v/ansi-x12.svg)](https://pypi.org/project/ansi-x12/)
[![Python versions](https://img.shields.io/pypi/pyversions/ansi-x12.svg)](https://pypi.org/project/ansi-x12/)
[![CI](https://github.com/fifoa-labs/x12/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/fifoa-labs/x12/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/fifoa-labs/x12/branch/main/graph/badge.svg)](https://codecov.io/gh/fifoa-labs/x12)
[![License](https://img.shields.io/pypi/l/ansi-x12.svg)](https://github.com/fifoa-labs/x12/blob/main/LICENSE)

A small, framework-independent Python library for generic ANSI X12 structure.

`ansi-x12` discovers interchange separators, tokenizes raw byte payloads,
validates X12 envelope structure, and produces immutable inspection models.
It deliberately stops at the syntax and envelope layer: it does not interpret
the business meaning of transaction sets, segments, qualifiers, or elements.

- **PyPI:** https://pypi.org/project/ansi-x12/
- **Source:** https://github.com/fifoa-labs/x12
- **License:** MIT

## Installation

Install the latest release from PyPI:

```bash
pip install ansi-x12
```

The distribution name is `ansi-x12`; the Python import package is `x12`:

```python
import x12
```

The package has no runtime dependencies.

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

print(interchange.control_number)
print(inspection.transaction_set_codes)
print(inspection.total_segment_count)
```

The parser accepts `bytes`, preserves the original source payload on
`X12Document.raw`, and returns immutable structural models.

## Scope

The current package provides the generic structural layer of ANSI X12:

- separator discovery from the fixed-width ISA segment;
- byte-oriented tokenization;
- immutable segment and document models;
- ISA/IEA interchange parsing;
- TA1 interchange acknowledgment support;
- GS/GE functional-group parsing;
- ST/SE transaction-set parsing;
- envelope ordering and nesting validation;
- control-number validation;
- declared-count validation;
- structural inspection and segment inventories;
- inline type information through `py.typed`.

It remains transaction-set agnostic and trading-partner agnostic.

## What `x12` Does

`x12` handles concerns that are common to X12 interchanges regardless of the
transaction-set type:

- derives the element, repetition, component, and segment separators;
- supports non-default separator bytes;
- preserves empty positional elements;
- preserves element values as raw bytes;
- retains original document bytes and source segment order;
- assigns contiguous, zero-based segment indexes;
- exposes one-based X12 element access;
- organizes a flat segment stream into immutable envelope models;
- validates envelope boundaries and nesting;
- validates matching ISA13/IEA02, GS06/GE02, and ST02/SE02 values;
- validates IEA01, GE01, and SE01 declared counts;
- preserves optional ST03 and ST04 references;
- supports TA1-only interchanges and TA1 segments before functional groups;
- rejects empty functional groups;
- produces transaction, group, segment, and frequency summaries.

## What `x12` Does Not Do

`x12` does not interpret business semantics.

It does not:

- decide that transaction set `850` is a purchase order;
- interpret transaction-specific segment or qualifier meanings;
- validate implementation-guide or companion-guide rules;
- map X12 data into application or database models;
- manage trading-partner profiles;
- persist data;
- send messages through AS2, SFTP, APIs, or another transport;
- depend on Django, Flask, FastAPI, or another application framework.

A future transaction layer may understand an X12 `850`, `810`, or `856`.
That layer will build on the generic structures in `x12.core` and live under
`x12.transactions`.

## Architecture

The package is organized into distinct layers:

```text
Raw X12 bytes
    │
    ▼
Separator discovery
    │
    ▼
Tokenizer
    │
    ▼
X12Document and X12Segment
    │
    ▼
Envelope parser and structural validation
    │
    ▼
X12Interchange
    │
    ▼
Structural inspection
```

The Python package mirrors that separation:

```text
x12
├── __init__.py          Curated public API
├── py.typed             PEP 561 type marker
├── core/                Generic X12 syntax and envelope infrastructure
└── transactions/        Reserved transaction-specific layer
```

Dependency direction is intentional:

```text
x12.transactions  →  x12.core
x12.core          ✕  x12.transactions
```

The core must remain usable without loading or understanding transaction
definitions.

## Core Models

### Separators

`derive_x12_separators()` reads the separator bytes from the fixed-width ISA
segment:

```python
from x12 import derive_x12_separators

separators = derive_x12_separators(payload)

print(separators.element)
print(separators.repetition)
print(separators.component)
print(separators.segment)
```

`X12Separators` contains:

- `element`
- `repetition`
- `component`
- `segment`

For interchange version `00402` and later, ISA11 is exposed as the repetition
separator. Earlier versions expose `None` for `repetition`.

### Segments and Documents

`tokenize_x12()` converts raw bytes into an immutable `X12Document`:

```python
from x12 import tokenize_x12

document = tokenize_x12(payload)
```

Each `X12Segment` contains:

- a zero-based source index;
- an ASCII segment tag;
- ordered raw-byte elements;
- the raw segment bytes.

Element access uses one-based X12 positions:

```python
segment = document.find_segments("ST")[0]

assert segment.element(1) == b"999"
assert segment.element(2) == b"0001"
assert segment.element(3) is None
```

Empty and missing values remain distinct:

```python
assert segment.element(1) == b""
assert segment.element(20) is None
```

Documents support iteration and length:

```python
for segment in document:
    print(segment.index, segment.tag)

print(len(document))
```

The tokenizer ignores permitted formatting whitespace between segments while
retaining the complete original payload in `document.raw`.

### Envelopes

`parse_x12_interchange()` converts a tokenized document into a validated
envelope hierarchy:

```python
from x12 import parse_x12_interchange

interchange = parse_x12_interchange(document)
```

The resulting hierarchy is:

```text
ISA
├── TA1, when present
├── GS
│   ├── ST
│   │   ├── transaction body
│   │   └── SE
│   └── GE
└── IEA
```

The immutable envelope models are:

- `X12TransactionSet`
- `X12FunctionalGroup`
- `X12Interchange`

They expose common structural values such as control numbers, versions,
declared counts, actual counts, ordered segment collections, and transaction
set codes. They do not interpret transaction-specific content.

### Structural Validation

The parser validates:

- ISA as the first segment;
- IEA as the final segment;
- valid TA1 placement;
- GS/GE functional-group boundaries;
- ST/SE transaction-set boundaries;
- required envelope elements;
- envelope element counts;
- invalid nested envelope segments;
- matching ST02 and SE02 values;
- matching GS06 and GE02 values;
- matching ISA13 and IEA02 values;
- SE01 transaction segment counts;
- GE01 transaction-set counts;
- IEA01 functional-group counts;
- at least one transaction set in each functional group;
- at least one TA1 acknowledgment or functional group in an interchange.

### Inspection

`inspect_x12_interchange()` builds an immutable
`X12InspectionResult` from a validated interchange:

```python
from x12 import inspect_x12_interchange

inspection = inspect_x12_interchange(interchange)

print(inspection.transaction_set_codes)
print(inspection.total_segment_count)
print(inspection.unique_segment_tags)
print(inspection.repeating_segment_tags)
```

Inspection models include:

- `X12SegmentFrequency`
- `X12TransactionInspection`
- `X12FunctionalGroupInspection`
- `X12InspectionResult`

Inspection reports structural metadata only. They do not interpret business
content.

## Public API

Normal users should import from the package root:

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

Implementation modules are organized under `x12.core`. The root `x12` package
is the curated public surface and should be preferred by application code.

## Exception Hierarchy

```text
X12Error
├── X12EnvelopeError
│   └── X12SeparatorError
└── X12TokenizerError
    └── X12SegmentError
```

Catch `X12Error` when all structural failures should be handled together:

```python
from x12 import X12Error

try:
    document = tokenize_x12(payload)
    interchange = parse_x12_interchange(document)
except X12Error as exc:
    print(f"Invalid X12 document: {exc}")
```

Use a specialized subclass when the caller must distinguish separator,
tokenizer, segment, or envelope failures.

## Byte-Oriented API

The parsing API accepts `bytes`, not text strings:

```python
payload = Path("message.x12").read_bytes()
document = tokenize_x12(payload)
```

This is intentional. X12 separators are single-byte structural values, and
the ISA separator positions are fixed byte offsets. A byte-oriented API avoids
accidental decoding, normalization, or whitespace changes before structural
processing is complete.

Applications may decode individual element values later using the character
encoding required by their implementation guide or trading partner.

## Immutability

Core and inspection models are frozen dataclasses with slots.

Immutability makes parsed results:

- deterministic;
- hashable;
- safe to share;
- resistant to accidental modification;
- easier to validate, test, and audit.

Construction and serialization will use explicit APIs rather than mutating
parsed objects in place.

## Type Information

The wheel includes a `py.typed` marker and inline annotations. Type checkers can
consume the installed package directly:

```python
from x12 import X12Interchange, parse_x12_interchange
```

The project is checked with mypy in strict mode.

## Package Layout

```text
.
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── publish.yml
├── docs/
├── src/
│   └── x12/
│       ├── __init__.py
│       ├── py.typed
│       ├── core/
│       │   ├── __init__.py
│       │   ├── envelopes.py
│       │   ├── exceptions.py
│       │   ├── inspection.py
│       │   ├── inspector.py
│       │   ├── parser.py
│       │   ├── segments.py
│       │   ├── separators.py
│       │   └── tokenizer.py
│       └── transactions/
│           └── __init__.py
├── tests/
│   ├── core/
│   │   ├── fixtures/
│   │   │   └── sample_message
│   │   ├── test_envelopes.py
│   │   ├── test_exceptions.py
│   │   ├── test_inspection.py
│   │   ├── test_inspector.py
│   │   ├── test_parser.py
│   │   ├── test_sample_message.py
│   │   ├── test_segments.py
│   │   ├── test_separators.py
│   │   └── test_tokenizer.py
│   └── test_public_api.py
├── LICENSE
├── Makefile
├── README.md
├── RELEASING.md
├── pyproject.toml
└── uv.lock
```

## Current Limitations

The project is intentionally focused and does not yet provide:

- serialization of structured models back to X12 bytes;
- builders for creating new interchanges;
- automatic envelope or control-number generation;
- streaming tokenization;
- length-aware BIN segment parsing;
- ISX release-character support;
- transaction-specific models;
- implementation-guide or trading-partner validation.

These are explicit boundaries, not hidden behavior. Features will be added only
when they can preserve the package's generic and deterministic core.

## Development

The project uses:

- uv
- pytest
- pytest-cov
- pytest-xdist
- Ruff
- mypy
- build
- Twine

Clone and install development dependencies:

```bash
git clone https://github.com/fifoa-labs/x12.git
cd x12
make sync
```

Common commands:

```bash
make format          # Apply formatting and safe fixes
make format-check    # Check formatting
make lint            # Run Ruff linting
make typecheck       # Run strict mypy checks
make test            # Run the test suite
make test-fast       # Run tests in parallel
make coverage        # Run statement and branch coverage
make check           # Run normal local validation
make release-check   # Run full release validation and build checks
```

## Testing and Quality

The test suite covers:

- separator extraction and separator invariants;
- custom separators;
- legacy and modern ISA versions;
- malformed fixed-width ISA segments;
- byte-oriented tokenization;
- empty positional elements;
- inter-segment formatting whitespace;
- invalid segment identifiers;
- immutable model invariants;
- envelope ordering and nesting;
- TA1 interchange acknowledgments;
- optional ST03 and ST04 references;
- missing envelope boundaries;
- empty functional-group rejection;
- control-number matching;
- declared-count validation;
- inspection summaries;
- segment-frequency ordering;
- complete synthetic interchange fixtures;
- public API exports;
- runtime type-hint resolution;
- wheel-safe type metadata.

The project requires 100% statement and branch coverage. The fixture corpus is
synthetic and generic; it contains no production customer, carrier, shipment,
location, phone, or equipment information.

## Building and Releasing

Build the source distribution and wheel:

```bash
make build
```

Validate distribution metadata:

```bash
make check-dist
```

Inspect the wheel:

```bash
make wheel-contents
```

Install the wheel into a temporary clean environment:

```bash
make install-wheel
```

Run the complete release validation:

```bash
make release-check
```

The wheel should contain:

```text
x12/__init__.py
x12/py.typed
x12/core/
x12/transactions/
```

It should not contain tests, development caches, coverage files, local
configuration, private fixtures, or application-specific code.

Releases are published through GitHub Actions using PyPI Trusted Publishing.
See [RELEASING.md](docs/RELEASING.md) for the complete procedure.

## Roadmap

Near-term core improvements:

1. serialize validated interchanges back to X12 bytes;
2. guarantee parse/serialize round trips;
3. add explicit builders for segments, transactions, groups, and interchanges;
4. calculate envelope counts and control values during construction;
5. add structured validation reports and richer diagnostics;
6. add length-aware BIN support;
7. add streaming support where real workloads require it.

Transaction-specific models will be added under `x12.transactions` only after
they are driven by real implementation guides and trading-partner usage.

## Extension Rules

A contribution to `x12.core` should remain:

- generic;
- structural;
- deterministic;
- framework independent;
- transaction-set agnostic;
- trading-partner agnostic.

If a feature requires knowing what a transaction, segment, qualifier, or
element means, it belongs in `x12.transactions` or a higher application layer.

## Guiding Principle

> The core library understands X12 structure. Higher layers understand meaning.

## License

MIT

---

Built and maintained by **FIFOA Labs**.
