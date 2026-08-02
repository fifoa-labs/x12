"""
src/x12/core/__init__.py

Generic ANSI X12 syntax and envelope infrastructure.

This package contains the transaction-neutral foundation for tokenizing,
parsing, inspecting, validating, and eventually serializing X12 documents.
It understands separators, segments, envelopes, and structural relationships
without interpreting the business meaning of specific transaction sets.

Higher-level transaction support belongs in :mod:`x12.transactions` and builds
on the generic models exposed here.
"""
