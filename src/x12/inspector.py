"""
src/x12/inspector.py

Build structural inspection summaries from validated ANSI X12 interchanges.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from .inspection import (
    X12FunctionalGroupInspection,
    X12InspectionResult,
    X12SegmentFrequency,
    X12TransactionInspection,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .envelopes import (
        X12FunctionalGroup,
        X12Interchange,
        X12TransactionSet,
    )


def inspect_x12_interchange(
    interchange: X12Interchange,
) -> X12InspectionResult:
    """Build a structural inventory of a validated X12 interchange.

    The inspection result summarizes envelope metadata, separators, segment
    frequencies, functional groups, and transaction sets without interpreting
    transaction-specific business data.

    Args:
        interchange: Parsed and validated X12 interchange.

    Returns:
        An immutable structural inspection result.
    """
    return X12InspectionResult(
        interchange_version=interchange.interchange_version,
        interchange_control_number=interchange.control_number,
        usage_indicator=interchange.usage_indicator,
        element_separator=interchange.document.separators.element,
        repetition_separator=interchange.document.separators.repetition,
        component_separator=interchange.document.separators.component,
        segment_terminator=interchange.document.separators.segment,
        declared_group_count=interchange.declared_group_count,
        actual_group_count=interchange.actual_group_count,
        total_transaction_count=sum(
            group.actual_transaction_count for group in interchange.groups
        ),
        total_segment_count=len(interchange.document),
        groups=tuple(
            _inspect_functional_group(
                group,
                index=index,
            )
            for index, group in enumerate(interchange.groups)
        ),
        segment_frequencies=_segment_frequencies(
            segment.tag for segment in interchange.document
        ),
    )


def _inspect_functional_group(
    group: X12FunctionalGroup,
    *,
    index: int,
) -> X12FunctionalGroupInspection:
    """Build a structural summary of one functional group."""
    return X12FunctionalGroupInspection(
        index=index,
        functional_identifier_code=group.functional_identifier_code,
        application_sender_code=group.application_sender_code,
        application_receiver_code=group.application_receiver_code,
        control_number=group.control_number,
        implementation_version=group.implementation_version,
        declared_transaction_count=group.declared_transaction_count,
        actual_transaction_count=group.actual_transaction_count,
        transactions=tuple(
            _inspect_transaction(
                transaction,
                index=transaction_index,
            )
            for transaction_index, transaction in enumerate(group.transactions)
        ),
    )


def _inspect_transaction(
    transaction: X12TransactionSet,
    *,
    index: int,
) -> X12TransactionInspection:
    """Build a structural summary of one transaction set."""
    segment_tags = tuple(segment.tag for segment in transaction.all_segments)

    return X12TransactionInspection(
        index=index,
        transaction_set_code=transaction.transaction_set_code,
        control_number=transaction.control_number,
        declared_segment_count=transaction.declared_segment_count,
        actual_segment_count=transaction.actual_segment_count,
        segment_tags=segment_tags,
        segment_frequencies=_segment_frequencies(segment_tags),
    )


def _segment_frequencies(
    tags: Iterable[str],
) -> tuple[X12SegmentFrequency, ...]:
    """Count segment tags while preserving first-appearance order."""
    ordered_tags = tuple(tags)
    counts = Counter(ordered_tags)

    return tuple(
        X12SegmentFrequency(
            tag=tag,
            count=counts[tag],
        )
        for tag in dict.fromkeys(ordered_tags)
    )


__all__ = [
    "inspect_x12_interchange",
]
