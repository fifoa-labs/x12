"""
src/x12/transactions/__init__.py

Transaction-level ANSI X12 models and mappings.

This namespace is reserved for transaction-set support such as 850 purchase
orders, 810 invoices, and 856 advance ship notices. Transaction modules may
interpret segment meaning and convert between typed transaction objects and
the generic structures provided by :mod:`x12.core`.

Keeping this layer separate allows the core package to remain focused on X12
syntax, envelopes, parsing, validation, and serialization.
"""
