"""
src/x12/core/inspection.py

Immutable structural inspection models for parsed ANSI X12 interchanges.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class X12SegmentFrequency:
    """Occurrence count for one X12 segment tag.

    Attributes:
        tag: Segment identifier, such as ``ISA``, ``GS``, or ``ST``.
        count: Number of occurrences.
    """

    tag: str
    count: int

    def __post_init__(self) -> None:
        """Validate the segment tag and occurrence count."""
        if not self.tag:
            msg = "X12 segment-frequency tag cannot be empty."
            raise ValueError(msg)

        if not self.tag.isascii() or not self.tag.isalnum():
            msg = "X12 segment-frequency tag must be ASCII alphanumeric."
            raise ValueError(msg)

        if self.count < 1:
            msg = "X12 segment-frequency count must be greater than zero."
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class X12TransactionInspection:
    """Structural summary of one X12 transaction set.

    Attributes:
        index: Zero-based transaction-set position within its functional group.
        transaction_set_code: ST01 transaction-set identifier.
        control_number: ST02 transaction-set control number.
        declared_segment_count: Segment count declared by SE01.
        actual_segment_count: Observed segment count from ST through SE.
        segment_tags: All transaction-set segment tags in document order.
        segment_frequencies: Segment frequencies in first-appearance order.
    """

    index: int
    transaction_set_code: bytes | None
    control_number: bytes | None
    declared_segment_count: int | None
    actual_segment_count: int
    segment_tags: tuple[str, ...]
    segment_frequencies: tuple[X12SegmentFrequency, ...]

    def __post_init__(self) -> None:
        """Validate transaction-inspection invariants."""
        if self.index < 0:
            msg = "X12 transaction-inspection index cannot be negative."
            raise ValueError(msg)

        if self.actual_segment_count < 2:  # noqa: PLR2004
            msg = (
                "X12 transaction inspection must include at least its "
                "ST and SE segments."
            )
            raise ValueError(msg)

        if len(self.segment_tags) != self.actual_segment_count:
            msg = (
                "X12 transaction segment-tag count must match the actual segment count."
            )
            raise ValueError(msg)

        _validate_frequencies(
            tags=self.segment_tags,
            frequencies=self.segment_frequencies,
            scope="transaction",
        )

    @property
    def unique_segment_tags(self) -> tuple[str, ...]:
        """Return segment tags in first-appearance order."""
        return tuple(frequency.tag for frequency in self.segment_frequencies)

    @property
    def repeating_segment_tags(self) -> tuple[str, ...]:
        """Return segment tags occurring more than once."""
        return tuple(
            frequency.tag
            for frequency in self.segment_frequencies
            if frequency.count > 1
        )


@dataclass(frozen=True, slots=True)
class X12FunctionalGroupInspection:
    """Structural summary of one X12 functional group.

    Attributes:
        index: Zero-based functional-group position within the interchange.
        functional_identifier_code: GS01 functional identifier code.
        application_sender_code: GS02 application sender code.
        application_receiver_code: GS03 application receiver code.
        control_number: GS06 functional-group control number.
        implementation_version: GS08 implementation version.
        declared_transaction_count: Transaction count declared by GE01.
        actual_transaction_count: Number of observed transaction sets.
        transactions: Ordered transaction-set inspections.
    """

    index: int
    functional_identifier_code: bytes | None
    application_sender_code: bytes | None
    application_receiver_code: bytes | None
    control_number: bytes | None
    implementation_version: bytes | None
    declared_transaction_count: int | None
    actual_transaction_count: int
    transactions: tuple[X12TransactionInspection, ...]

    def __post_init__(self) -> None:
        """Validate functional-group inspection invariants."""
        if self.index < 0:
            msg = "X12 functional-group inspection index cannot be negative."
            raise ValueError(msg)

        if self.actual_transaction_count < 0:
            msg = "X12 actual transaction count cannot be negative."
            raise ValueError(msg)

        if len(self.transactions) != self.actual_transaction_count:
            msg = (
                "X12 functional-group transaction count must match the "
                "number of transaction inspections."
            )
            raise ValueError(msg)

        for expected_index, transaction in enumerate(self.transactions):
            if transaction.index != expected_index:
                msg = (
                    "X12 transaction inspection indexes must be contiguous; "
                    f"expected {expected_index}, found {transaction.index}."
                )
                raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class X12InspectionResult:
    """Structural inventory for one complete X12 interchange.

    Attributes:
        interchange_version: ISA12 interchange-control version.
        interchange_control_number: ISA13 interchange control number.
        usage_indicator: ISA15 test or production indicator.
        element_separator: Element separator derived from ISA.
        repetition_separator: Repetition separator, when supported.
        component_separator: Component-element separator.
        segment_terminator: Segment terminator.
        declared_group_count: Functional-group count declared by IEA01.
        actual_group_count: Number of observed functional groups.
        total_transaction_count: Number of observed transaction sets.
        total_segment_count: Number of observed segments.
        groups: Ordered functional-group inspections.
        segment_frequencies: Document-wide segment frequencies in
            first-appearance order.
    """

    interchange_version: bytes | None
    interchange_control_number: bytes | None
    usage_indicator: bytes | None
    element_separator: bytes
    repetition_separator: bytes | None
    component_separator: bytes
    segment_terminator: bytes
    declared_group_count: int | None
    actual_group_count: int
    total_transaction_count: int
    total_segment_count: int
    groups: tuple[X12FunctionalGroupInspection, ...]
    segment_frequencies: tuple[X12SegmentFrequency, ...]

    def __post_init__(self) -> None:
        """Validate interchange-inspection invariants."""
        if self.actual_group_count < 0:
            msg = "X12 actual group count cannot be negative."
            raise ValueError(msg)

        if self.total_transaction_count < 0:
            msg = "X12 total transaction count cannot be negative."
            raise ValueError(msg)

        if self.total_segment_count < 2:  # noqa: PLR2004
            msg = "X12 inspection result must include at least ISA and IEA segments."
            raise ValueError(msg)

        if len(self.groups) != self.actual_group_count:
            msg = "X12 actual group count must match the number of group inspections."
            raise ValueError(msg)

        observed_transaction_count = sum(
            group.actual_transaction_count for group in self.groups
        )

        if observed_transaction_count != self.total_transaction_count:
            msg = (
                "X12 total transaction count must match the transaction "
                "counts reported by its functional groups."
            )
            raise ValueError(msg)

        for expected_index, group in enumerate(self.groups):
            if group.index != expected_index:
                msg = (
                    "X12 functional-group inspection indexes must be "
                    f"contiguous; expected {expected_index}, found "
                    f"{group.index}."
                )
                raise ValueError(msg)

        if (
            sum(frequency.count for frequency in self.segment_frequencies)
            != self.total_segment_count
        ):
            msg = "X12 segment-frequency totals must match the total segment count."
            raise ValueError(msg)

    @property
    def transaction_set_codes(self) -> tuple[bytes | None, ...]:
        """Return transaction-set codes in document order."""
        return tuple(
            transaction.transaction_set_code
            for group in self.groups
            for transaction in group.transactions
        )

    @property
    def unique_segment_tags(self) -> tuple[str, ...]:
        """Return segment tags in first-appearance order."""
        return tuple(frequency.tag for frequency in self.segment_frequencies)

    @property
    def repeating_segment_tags(self) -> tuple[str, ...]:
        """Return segment tags occurring more than once."""
        return tuple(
            frequency.tag
            for frequency in self.segment_frequencies
            if frequency.count > 1
        )


def _validate_frequencies(
    *,
    tags: tuple[str, ...],
    frequencies: tuple[X12SegmentFrequency, ...],
    scope: str,
) -> None:
    """Validate frequency order and counts against an ordered tag stream."""
    observed_counts: dict[str, int] = {}
    observed_order: list[str] = []

    for tag in tags:
        if tag not in observed_counts:
            observed_order.append(tag)
            observed_counts[tag] = 0

        observed_counts[tag] += 1

    expected_frequencies = tuple(
        X12SegmentFrequency(
            tag=tag,
            count=observed_counts[tag],
        )
        for tag in observed_order
    )

    if frequencies != expected_frequencies:
        msg = (
            f"X12 {scope} segment frequencies must match the segment-tag "
            "stream and preserve first-appearance order."
        )
        raise ValueError(msg)


__all__ = [
    "X12FunctionalGroupInspection",
    "X12InspectionResult",
    "X12SegmentFrequency",
    "X12TransactionInspection",
]
