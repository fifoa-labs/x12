"""
tests/test_inspection.py

Tests for immutable X12 structural inspection models.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Any, cast

import pytest

from x12.inspection import (
    X12FunctionalGroupInspection,
    X12InspectionResult,
    X12SegmentFrequency,
    X12TransactionInspection,
)


def make_minimal_transaction(
    *,
    index: int = 0,
    transaction_set_code: bytes | None = b"999",
    control_number: bytes | None = b"0001",
) -> X12TransactionInspection:
    """Build a valid transaction inspection containing only ST and SE."""
    return X12TransactionInspection(
        index=index,
        transaction_set_code=transaction_set_code,
        control_number=control_number,
        declared_segment_count=2,
        actual_segment_count=2,
        segment_tags=("ST", "SE"),
        segment_frequencies=(
            X12SegmentFrequency(tag="ST", count=1),
            X12SegmentFrequency(tag="SE", count=1),
        ),
    )


def make_empty_group(*, index: int = 0) -> X12FunctionalGroupInspection:
    """Build a valid functional-group inspection without transactions."""
    return X12FunctionalGroupInspection(
        index=index,
        functional_identifier_code=b"XX",
        application_sender_code=b"SENDER01",
        application_receiver_code=b"RECEIVER01",
        control_number=b"1",
        implementation_version=b"007050",
        declared_transaction_count=0,
        actual_transaction_count=0,
        transactions=(),
    )


@pytest.fixture
def transaction_inspection() -> X12TransactionInspection:
    """Return a generic transaction inspection with repeated segment tags."""
    return X12TransactionInspection(
        index=0,
        transaction_set_code=b"999",
        control_number=b"0001",
        declared_segment_count=7,
        actual_segment_count=7,
        segment_tags=(
            "ST",
            "N1",
            "REF",
            "DTM",
            "N1",
            "REF",
            "SE",
        ),
        segment_frequencies=(
            X12SegmentFrequency(tag="ST", count=1),
            X12SegmentFrequency(tag="N1", count=2),
            X12SegmentFrequency(tag="REF", count=2),
            X12SegmentFrequency(tag="DTM", count=1),
            X12SegmentFrequency(tag="SE", count=1),
        ),
    )


@pytest.fixture
def second_transaction_inspection() -> X12TransactionInspection:
    """Return a second generic transaction without repeated segment tags."""
    return X12TransactionInspection(
        index=1,
        transaction_set_code=b"998",
        control_number=b"0002",
        declared_segment_count=3,
        actual_segment_count=3,
        segment_tags=(
            "ST",
            "N1",
            "SE",
        ),
        segment_frequencies=(
            X12SegmentFrequency(tag="ST", count=1),
            X12SegmentFrequency(tag="N1", count=1),
            X12SegmentFrequency(tag="SE", count=1),
        ),
    )


@pytest.fixture
def group_inspection(
    transaction_inspection: X12TransactionInspection,
    second_transaction_inspection: X12TransactionInspection,
) -> X12FunctionalGroupInspection:
    """Return a generic group containing two transaction inspections."""
    return X12FunctionalGroupInspection(
        index=0,
        functional_identifier_code=b"XX",
        application_sender_code=b"SENDER01",
        application_receiver_code=b"RECEIVER01",
        control_number=b"1",
        implementation_version=b"007050",
        declared_transaction_count=2,
        actual_transaction_count=2,
        transactions=(
            transaction_inspection,
            second_transaction_inspection,
        ),
    )


@pytest.fixture
def inspection_result(
    group_inspection: X12FunctionalGroupInspection,
) -> X12InspectionResult:
    """Return a complete generic interchange inspection result."""
    return X12InspectionResult(
        interchange_version=b"00705",
        interchange_control_number=b"000000001",
        usage_indicator=b"T",
        element_separator=b"*",
        repetition_separator=b"^",
        component_separator=b":",
        segment_terminator=b"~",
        declared_group_count=1,
        actual_group_count=1,
        total_transaction_count=2,
        total_segment_count=14,
        groups=(group_inspection,),
        segment_frequencies=(
            X12SegmentFrequency(tag="ISA", count=1),
            X12SegmentFrequency(tag="GS", count=1),
            X12SegmentFrequency(tag="ST", count=2),
            X12SegmentFrequency(tag="N1", count=3),
            X12SegmentFrequency(tag="REF", count=2),
            X12SegmentFrequency(tag="DTM", count=1),
            X12SegmentFrequency(tag="SE", count=2),
            X12SegmentFrequency(tag="GE", count=1),
            X12SegmentFrequency(tag="IEA", count=1),
        ),
    )


def test_segment_frequency_stores_values() -> None:
    """A segment frequency should preserve its tag and count."""
    frequency = X12SegmentFrequency(tag="N1", count=2)

    assert frequency.tag == "N1"
    assert frequency.count == 2


def test_segment_frequency_requires_nonempty_tag() -> None:
    """A segment-frequency tag cannot be empty."""
    with pytest.raises(
        ValueError,
        match="segment-frequency tag cannot be empty",
    ):
        X12SegmentFrequency(tag="", count=1)


@pytest.mark.parametrize(
    "tag",
    [
        "N-1",
        "N_1",
        "N 1",
        "$N1",
        "Ñ1",
    ],
)
def test_segment_frequency_requires_ascii_alphanumeric_tag(
    tag: str,
) -> None:
    """Segment-frequency tags must be ASCII alphanumeric."""
    with pytest.raises(
        ValueError,
        match="segment-frequency tag must be ASCII alphanumeric",
    ):
        X12SegmentFrequency(tag=tag, count=1)


@pytest.mark.parametrize("count", [0, -1, -10])
def test_segment_frequency_requires_positive_count(count: int) -> None:
    """A segment frequency must contain at least one occurrence."""
    with pytest.raises(
        ValueError,
        match="segment-frequency count must be greater than zero",
    ):
        X12SegmentFrequency(tag="N1", count=count)


def test_segment_frequency_is_immutable() -> None:
    """Segment-frequency fields should be immutable."""
    frequency = X12SegmentFrequency(tag="N1", count=2)

    with pytest.raises(FrozenInstanceError):
        frequency.count = 3  # type: ignore[misc]


def test_equal_segment_frequencies_compare_and_hash_equal() -> None:
    """Equivalent segment frequencies should compare and hash equally."""
    first = X12SegmentFrequency(tag="N1", count=2)
    second = X12SegmentFrequency(tag="N1", count=2)

    assert first == second
    assert hash(first) == hash(second)
    assert first in {first}


@pytest.mark.parametrize(
    "changed",
    [
        X12SegmentFrequency(tag="REF", count=2),
        X12SegmentFrequency(tag="N1", count=1),
    ],
)
def test_segment_frequency_comparison_includes_all_fields(
    changed: X12SegmentFrequency,
) -> None:
    """Both tag and count should participate in equality."""
    frequency = X12SegmentFrequency(tag="N1", count=2)

    assert frequency != changed


def test_transaction_inspection_stores_values(
    transaction_inspection: X12TransactionInspection,
) -> None:
    """A transaction inspection should preserve all supplied values."""
    assert transaction_inspection.index == 0
    assert transaction_inspection.transaction_set_code == b"999"
    assert transaction_inspection.control_number == b"0001"
    assert transaction_inspection.declared_segment_count == 7
    assert transaction_inspection.actual_segment_count == 7
    assert transaction_inspection.segment_tags[0] == "ST"
    assert transaction_inspection.segment_tags[-1] == "SE"


def test_transaction_unique_segment_tags_preserve_first_appearance_order(
    transaction_inspection: X12TransactionInspection,
) -> None:
    """Unique transaction tags should preserve first-appearance order."""
    assert transaction_inspection.unique_segment_tags == (
        "ST",
        "N1",
        "REF",
        "DTM",
        "SE",
    )


def test_transaction_repeating_segment_tags_preserve_frequency_order(
    transaction_inspection: X12TransactionInspection,
) -> None:
    """Repeating tags should follow the stored frequency order."""
    assert transaction_inspection.repeating_segment_tags == (
        "N1",
        "REF",
    )


def test_transaction_without_repeating_tags_returns_empty_tuple(
    second_transaction_inspection: X12TransactionInspection,
) -> None:
    """A transaction without repeated tags should return an empty tuple."""
    assert second_transaction_inspection.repeating_segment_tags == ()


def test_transaction_inspection_allows_missing_optional_metadata() -> None:
    """Optional transaction metadata may be absent from an inspection."""
    inspection = make_minimal_transaction(
        transaction_set_code=None,
        control_number=None,
    )

    assert inspection.transaction_set_code is None
    assert inspection.control_number is None
    assert inspection.unique_segment_tags == ("ST", "SE")
    assert inspection.repeating_segment_tags == ()


def test_transaction_properties_return_tuples(
    transaction_inspection: X12TransactionInspection,
) -> None:
    """Derived transaction tag collections should be immutable tuples."""
    assert isinstance(transaction_inspection.unique_segment_tags, tuple)
    assert isinstance(transaction_inspection.repeating_segment_tags, tuple)


def test_transaction_inspection_rejects_negative_index() -> None:
    """Transaction-inspection indexes must be zero or greater."""
    with pytest.raises(
        ValueError,
        match="transaction-inspection index cannot be negative",
    ):
        make_minimal_transaction(index=-1)


@pytest.mark.parametrize("actual_segment_count", [0, 1])
def test_transaction_inspection_requires_st_and_se(
    actual_segment_count: int,
) -> None:
    """A transaction inspection must represent at least ST and SE."""
    with pytest.raises(
        ValueError,
        match="must include at least its ST and SE segments",
    ):
        X12TransactionInspection(
            index=0,
            transaction_set_code=None,
            control_number=None,
            declared_segment_count=None,
            actual_segment_count=actual_segment_count,
            segment_tags=(),
            segment_frequencies=(),
        )


def test_transaction_segment_tag_count_must_match_actual_count() -> None:
    """The ordered tag stream must match the observed segment count."""
    with pytest.raises(
        ValueError,
        match="segment-tag count must match the actual segment count",
    ):
        X12TransactionInspection(
            index=0,
            transaction_set_code=b"999",
            control_number=b"0001",
            declared_segment_count=3,
            actual_segment_count=3,
            segment_tags=("ST", "SE"),
            segment_frequencies=(
                X12SegmentFrequency(tag="ST", count=1),
                X12SegmentFrequency(tag="SE", count=1),
            ),
        )


@pytest.mark.parametrize(
    "frequencies",
    [
        (
            X12SegmentFrequency(tag="ST", count=1),
            X12SegmentFrequency(tag="N1", count=1),
            X12SegmentFrequency(tag="SE", count=1),
        ),
        (
            X12SegmentFrequency(tag="N1", count=2),
            X12SegmentFrequency(tag="ST", count=1),
            X12SegmentFrequency(tag="SE", count=1),
        ),
        (
            X12SegmentFrequency(tag="ST", count=1),
            X12SegmentFrequency(tag="N1", count=2),
        ),
        (
            X12SegmentFrequency(tag="ST", count=1),
            X12SegmentFrequency(tag="N1", count=2),
            X12SegmentFrequency(tag="SE", count=1),
            X12SegmentFrequency(tag="REF", count=1),
        ),
    ],
)
def test_transaction_frequencies_must_match_tag_stream(
    frequencies: tuple[X12SegmentFrequency, ...],
) -> None:
    """Transaction frequencies must match counts and appearance order."""
    with pytest.raises(
        ValueError,
        match=(
            "transaction segment frequencies must match the segment-tag "
            "stream and preserve first-appearance order"
        ),
    ):
        X12TransactionInspection(
            index=0,
            transaction_set_code=b"999",
            control_number=b"0001",
            declared_segment_count=4,
            actual_segment_count=4,
            segment_tags=("ST", "N1", "N1", "SE"),
            segment_frequencies=frequencies,
        )


def test_transaction_tag_stream_requires_valid_segment_tags() -> None:
    """Tags used to derive frequencies must be valid X12 identifiers."""
    with pytest.raises(
        ValueError,
        match="segment-frequency tag must be ASCII alphanumeric",
    ):
        X12TransactionInspection(
            index=0,
            transaction_set_code=b"999",
            control_number=b"0001",
            declared_segment_count=3,
            actual_segment_count=3,
            segment_tags=("ST", "N-1", "SE"),
            segment_frequencies=(),
        )


def test_transaction_inspection_is_immutable(
    transaction_inspection: X12TransactionInspection,
) -> None:
    """Transaction-inspection fields should be immutable."""
    with pytest.raises(FrozenInstanceError):
        transaction_inspection.index = 1  # type: ignore[misc]


def test_transaction_collections_are_immutable(
    transaction_inspection: X12TransactionInspection,
) -> None:
    """Transaction tag and frequency collections should be immutable."""
    with pytest.raises(TypeError):
        cast("Any", transaction_inspection.segment_tags)[0] = "GS"

    with pytest.raises(TypeError):
        cast("Any", transaction_inspection.segment_frequencies)[0] = (
            X12SegmentFrequency(
                tag="GS",
                count=1,
            )
        )


def test_equal_transaction_inspections_compare_and_hash_equal(
    transaction_inspection: X12TransactionInspection,
) -> None:
    """Equivalent transaction inspections should compare and hash equally."""
    copy = X12TransactionInspection(
        index=transaction_inspection.index,
        transaction_set_code=transaction_inspection.transaction_set_code,
        control_number=transaction_inspection.control_number,
        declared_segment_count=transaction_inspection.declared_segment_count,
        actual_segment_count=transaction_inspection.actual_segment_count,
        segment_tags=transaction_inspection.segment_tags,
        segment_frequencies=transaction_inspection.segment_frequencies,
    )

    assert copy == transaction_inspection
    assert hash(copy) == hash(transaction_inspection)
    assert transaction_inspection in {transaction_inspection}


def test_functional_group_inspection_stores_values(
    group_inspection: X12FunctionalGroupInspection,
    transaction_inspection: X12TransactionInspection,
    second_transaction_inspection: X12TransactionInspection,
) -> None:
    """A group inspection should preserve all supplied values."""
    assert group_inspection.index == 0
    assert group_inspection.functional_identifier_code == b"XX"
    assert group_inspection.application_sender_code == b"SENDER01"
    assert group_inspection.application_receiver_code == b"RECEIVER01"
    assert group_inspection.control_number == b"1"
    assert group_inspection.implementation_version == b"007050"
    assert group_inspection.declared_transaction_count == 2
    assert group_inspection.actual_transaction_count == 2
    assert group_inspection.transactions == (
        transaction_inspection,
        second_transaction_inspection,
    )


def test_functional_group_inspection_allows_missing_optional_values() -> None:
    """Optional functional-group metadata may be absent."""
    inspection = X12FunctionalGroupInspection(
        index=0,
        functional_identifier_code=None,
        application_sender_code=None,
        application_receiver_code=None,
        control_number=None,
        implementation_version=None,
        declared_transaction_count=None,
        actual_transaction_count=0,
        transactions=(),
    )

    assert inspection.functional_identifier_code is None
    assert inspection.application_sender_code is None
    assert inspection.application_receiver_code is None
    assert inspection.control_number is None
    assert inspection.implementation_version is None
    assert inspection.declared_transaction_count is None
    assert inspection.transactions == ()


def test_functional_group_inspection_rejects_negative_index() -> None:
    """Functional-group indexes must be zero or greater."""
    with pytest.raises(
        ValueError,
        match="functional-group inspection index cannot be negative",
    ):
        make_empty_group(index=-1)


def test_functional_group_rejects_negative_actual_transaction_count() -> None:
    """Observed transaction counts cannot be negative."""
    with pytest.raises(
        ValueError,
        match="actual transaction count cannot be negative",
    ):
        X12FunctionalGroupInspection(
            index=0,
            functional_identifier_code=None,
            application_sender_code=None,
            application_receiver_code=None,
            control_number=None,
            implementation_version=None,
            declared_transaction_count=None,
            actual_transaction_count=-1,
            transactions=(),
        )


def test_functional_group_transaction_count_must_match_collection() -> None:
    """The observed count must match the transaction collection length."""
    with pytest.raises(
        ValueError,
        match=(
            "functional-group transaction count must match the number of "
            "transaction inspections"
        ),
    ):
        X12FunctionalGroupInspection(
            index=0,
            functional_identifier_code=None,
            application_sender_code=None,
            application_receiver_code=None,
            control_number=None,
            implementation_version=None,
            declared_transaction_count=None,
            actual_transaction_count=1,
            transactions=(),
        )


@pytest.mark.parametrize(
    ("transactions", "expected_index", "found_index"),
    [
        (
            (make_minimal_transaction(index=1),),
            0,
            1,
        ),
        (
            (
                make_minimal_transaction(index=0, control_number=b"0001"),
                make_minimal_transaction(index=2, control_number=b"0002"),
            ),
            1,
            2,
        ),
    ],
)
def test_functional_group_requires_contiguous_transaction_indexes(
    transactions: tuple[X12TransactionInspection, ...],
    expected_index: int,
    found_index: int,
) -> None:
    """Transaction indexes should be contiguous and zero-based."""
    with pytest.raises(
        ValueError,
        match=(
            "transaction inspection indexes must be contiguous; "
            f"expected {expected_index}, found {found_index}"
        ),
    ):
        X12FunctionalGroupInspection(
            index=0,
            functional_identifier_code=b"XX",
            application_sender_code=b"SENDER01",
            application_receiver_code=b"RECEIVER01",
            control_number=b"1",
            implementation_version=b"007050",
            declared_transaction_count=len(transactions),
            actual_transaction_count=len(transactions),
            transactions=transactions,
        )


def test_functional_group_inspection_is_immutable(
    group_inspection: X12FunctionalGroupInspection,
) -> None:
    """Functional-group inspection fields should be immutable."""
    with pytest.raises(FrozenInstanceError):
        group_inspection.index = 1  # type: ignore[misc]


def test_functional_group_transaction_collection_is_immutable(
    group_inspection: X12FunctionalGroupInspection,
) -> None:
    """The transaction-inspection collection should be immutable."""
    with pytest.raises(TypeError):
        group_inspection.transactions[0] = (  # type: ignore[index]
            group_inspection.transactions[1]
        )


def test_equal_functional_group_inspections_compare_and_hash_equal(
    group_inspection: X12FunctionalGroupInspection,
) -> None:
    """Equivalent group inspections should compare and hash equally."""
    copy = X12FunctionalGroupInspection(
        index=group_inspection.index,
        functional_identifier_code=group_inspection.functional_identifier_code,
        application_sender_code=group_inspection.application_sender_code,
        application_receiver_code=group_inspection.application_receiver_code,
        control_number=group_inspection.control_number,
        implementation_version=group_inspection.implementation_version,
        declared_transaction_count=group_inspection.declared_transaction_count,
        actual_transaction_count=group_inspection.actual_transaction_count,
        transactions=group_inspection.transactions,
    )

    assert copy == group_inspection
    assert hash(copy) == hash(group_inspection)
    assert group_inspection in {group_inspection}


def test_inspection_result_stores_interchange_values(
    inspection_result: X12InspectionResult,
) -> None:
    """An inspection result should preserve interchange-level values."""
    assert inspection_result.interchange_version == b"00705"
    assert inspection_result.interchange_control_number == b"000000001"
    assert inspection_result.usage_indicator == b"T"
    assert inspection_result.element_separator == b"*"
    assert inspection_result.repetition_separator == b"^"
    assert inspection_result.component_separator == b":"
    assert inspection_result.segment_terminator == b"~"
    assert inspection_result.declared_group_count == 1
    assert inspection_result.actual_group_count == 1
    assert inspection_result.total_transaction_count == 2
    assert inspection_result.total_segment_count == 14


def test_inspection_result_stores_groups(
    inspection_result: X12InspectionResult,
    group_inspection: X12FunctionalGroupInspection,
) -> None:
    """The result should retain functional groups in document order."""
    assert inspection_result.groups == (group_inspection,)


def test_inspection_result_returns_transaction_codes_in_document_order(
    inspection_result: X12InspectionResult,
) -> None:
    """Transaction-set codes should be flattened in document order."""
    assert inspection_result.transaction_set_codes == (
        b"999",
        b"998",
    )


def test_inspection_result_transaction_codes_support_missing_values() -> None:
    """Missing transaction-set codes should remain visible as None."""
    transaction = make_minimal_transaction(
        transaction_set_code=None,
        control_number=None,
    )
    group = X12FunctionalGroupInspection(
        index=0,
        functional_identifier_code=None,
        application_sender_code=None,
        application_receiver_code=None,
        control_number=None,
        implementation_version=None,
        declared_transaction_count=None,
        actual_transaction_count=1,
        transactions=(transaction,),
    )
    result = X12InspectionResult(
        interchange_version=None,
        interchange_control_number=None,
        usage_indicator=None,
        element_separator=b"*",
        repetition_separator=None,
        component_separator=b":",
        segment_terminator=b"~",
        declared_group_count=None,
        actual_group_count=1,
        total_transaction_count=1,
        total_segment_count=6,
        groups=(group,),
        segment_frequencies=(
            X12SegmentFrequency(tag="ISA", count=1),
            X12SegmentFrequency(tag="GS", count=1),
            X12SegmentFrequency(tag="ST", count=1),
            X12SegmentFrequency(tag="SE", count=1),
            X12SegmentFrequency(tag="GE", count=1),
            X12SegmentFrequency(tag="IEA", count=1),
        ),
    )

    assert result.transaction_set_codes == (None,)


def test_inspection_result_unique_segment_tags_preserve_order(
    inspection_result: X12InspectionResult,
) -> None:
    """Document-wide unique tags should preserve frequency order."""
    assert inspection_result.unique_segment_tags == (
        "ISA",
        "GS",
        "ST",
        "N1",
        "REF",
        "DTM",
        "SE",
        "GE",
        "IEA",
    )


def test_inspection_result_repeating_segment_tags_preserve_order(
    inspection_result: X12InspectionResult,
) -> None:
    """Document-wide repeating tags should preserve frequency order."""
    assert inspection_result.repeating_segment_tags == (
        "ST",
        "N1",
        "REF",
        "SE",
    )


def test_inspection_result_without_groups_has_no_transaction_codes() -> None:
    """An interchange without groups should expose no transaction codes."""
    result = X12InspectionResult(
        interchange_version=b"00705",
        interchange_control_number=b"000000001",
        usage_indicator=b"T",
        element_separator=b"*",
        repetition_separator=b"^",
        component_separator=b":",
        segment_terminator=b"~",
        declared_group_count=0,
        actual_group_count=0,
        total_transaction_count=0,
        total_segment_count=2,
        groups=(),
        segment_frequencies=(
            X12SegmentFrequency(tag="ISA", count=1),
            X12SegmentFrequency(tag="IEA", count=1),
        ),
    )

    assert result.transaction_set_codes == ()
    assert result.unique_segment_tags == ("ISA", "IEA")
    assert result.repeating_segment_tags == ()


def test_inspection_result_properties_return_tuples(
    inspection_result: X12InspectionResult,
) -> None:
    """Derived result collections should be immutable tuples."""
    assert isinstance(inspection_result.transaction_set_codes, tuple)
    assert isinstance(inspection_result.unique_segment_tags, tuple)
    assert isinstance(inspection_result.repeating_segment_tags, tuple)


def test_inspection_result_rejects_negative_actual_group_count() -> None:
    """Observed functional-group counts cannot be negative."""
    with pytest.raises(
        ValueError,
        match="actual group count cannot be negative",
    ):
        X12InspectionResult(
            interchange_version=None,
            interchange_control_number=None,
            usage_indicator=None,
            element_separator=b"*",
            repetition_separator=None,
            component_separator=b":",
            segment_terminator=b"~",
            declared_group_count=None,
            actual_group_count=-1,
            total_transaction_count=0,
            total_segment_count=2,
            groups=(),
            segment_frequencies=(
                X12SegmentFrequency(tag="ISA", count=1),
                X12SegmentFrequency(tag="IEA", count=1),
            ),
        )


def test_inspection_result_rejects_negative_transaction_count() -> None:
    """Observed transaction counts cannot be negative."""
    with pytest.raises(
        ValueError,
        match="total transaction count cannot be negative",
    ):
        X12InspectionResult(
            interchange_version=None,
            interchange_control_number=None,
            usage_indicator=None,
            element_separator=b"*",
            repetition_separator=None,
            component_separator=b":",
            segment_terminator=b"~",
            declared_group_count=None,
            actual_group_count=0,
            total_transaction_count=-1,
            total_segment_count=2,
            groups=(),
            segment_frequencies=(
                X12SegmentFrequency(tag="ISA", count=1),
                X12SegmentFrequency(tag="IEA", count=1),
            ),
        )


@pytest.mark.parametrize("total_segment_count", [0, 1])
def test_inspection_result_requires_isa_and_iea(
    total_segment_count: int,
) -> None:
    """An interchange inventory must include at least ISA and IEA."""
    with pytest.raises(
        ValueError,
        match="must include at least ISA and IEA segments",
    ):
        X12InspectionResult(
            interchange_version=None,
            interchange_control_number=None,
            usage_indicator=None,
            element_separator=b"*",
            repetition_separator=None,
            component_separator=b":",
            segment_terminator=b"~",
            declared_group_count=None,
            actual_group_count=0,
            total_transaction_count=0,
            total_segment_count=total_segment_count,
            groups=(),
            segment_frequencies=(),
        )


def test_inspection_result_group_count_must_match_collection() -> None:
    """The observed group count must match the group collection length."""
    with pytest.raises(
        ValueError,
        match="actual group count must match the number of group inspections",
    ):
        X12InspectionResult(
            interchange_version=None,
            interchange_control_number=None,
            usage_indicator=None,
            element_separator=b"*",
            repetition_separator=None,
            component_separator=b":",
            segment_terminator=b"~",
            declared_group_count=None,
            actual_group_count=1,
            total_transaction_count=0,
            total_segment_count=2,
            groups=(),
            segment_frequencies=(
                X12SegmentFrequency(tag="ISA", count=1),
                X12SegmentFrequency(tag="IEA", count=1),
            ),
        )


def test_inspection_result_transaction_count_must_match_groups() -> None:
    """The total transaction count must equal the group-level counts."""
    group = make_empty_group()

    with pytest.raises(
        ValueError,
        match=(
            "total transaction count must match the transaction counts "
            "reported by its functional groups"
        ),
    ):
        X12InspectionResult(
            interchange_version=None,
            interchange_control_number=None,
            usage_indicator=None,
            element_separator=b"*",
            repetition_separator=None,
            component_separator=b":",
            segment_terminator=b"~",
            declared_group_count=None,
            actual_group_count=1,
            total_transaction_count=1,
            total_segment_count=4,
            groups=(group,),
            segment_frequencies=(
                X12SegmentFrequency(tag="ISA", count=1),
                X12SegmentFrequency(tag="GS", count=1),
                X12SegmentFrequency(tag="GE", count=1),
                X12SegmentFrequency(tag="IEA", count=1),
            ),
        )


@pytest.mark.parametrize(
    ("groups", "expected_index", "found_index"),
    [
        (
            (make_empty_group(index=1),),
            0,
            1,
        ),
        (
            (
                make_empty_group(index=0),
                make_empty_group(index=2),
            ),
            1,
            2,
        ),
    ],
)
def test_inspection_result_requires_contiguous_group_indexes(
    groups: tuple[X12FunctionalGroupInspection, ...],
    expected_index: int,
    found_index: int,
) -> None:
    """Functional-group indexes should be contiguous and zero-based."""
    total_segment_count = 2 + (2 * len(groups))
    frequencies = (
        X12SegmentFrequency(tag="ISA", count=1),
        X12SegmentFrequency(tag="GS", count=len(groups)),
        X12SegmentFrequency(tag="GE", count=len(groups)),
        X12SegmentFrequency(tag="IEA", count=1),
    )

    with pytest.raises(
        ValueError,
        match=(
            "functional-group inspection indexes must be contiguous; "
            f"expected {expected_index}, found {found_index}"
        ),
    ):
        X12InspectionResult(
            interchange_version=None,
            interchange_control_number=None,
            usage_indicator=None,
            element_separator=b"*",
            repetition_separator=None,
            component_separator=b":",
            segment_terminator=b"~",
            declared_group_count=len(groups),
            actual_group_count=len(groups),
            total_transaction_count=0,
            total_segment_count=total_segment_count,
            groups=groups,
            segment_frequencies=frequencies,
        )


def test_inspection_result_frequency_total_must_match_segment_count() -> None:
    """Frequency totals must account for every observed segment."""
    with pytest.raises(
        ValueError,
        match="segment-frequency totals must match the total segment count",
    ):
        X12InspectionResult(
            interchange_version=None,
            interchange_control_number=None,
            usage_indicator=None,
            element_separator=b"*",
            repetition_separator=None,
            component_separator=b":",
            segment_terminator=b"~",
            declared_group_count=0,
            actual_group_count=0,
            total_transaction_count=0,
            total_segment_count=3,
            groups=(),
            segment_frequencies=(
                X12SegmentFrequency(tag="ISA", count=1),
                X12SegmentFrequency(tag="IEA", count=1),
            ),
        )


def test_inspection_result_is_immutable(
    inspection_result: X12InspectionResult,
) -> None:
    """Inspection-result fields should be immutable."""
    with pytest.raises(FrozenInstanceError):
        inspection_result.total_segment_count = 15  # type: ignore[misc]


def test_inspection_result_collections_are_immutable(
    inspection_result: X12InspectionResult,
) -> None:
    """Group and frequency collections should be immutable."""
    with pytest.raises(TypeError):
        cast("Any", inspection_result.groups)[0] = inspection_result.groups[0]

    with pytest.raises(TypeError):
        cast("Any", inspection_result.segment_frequencies)[0] = X12SegmentFrequency(
            tag="ISA",
            count=2,
        )


def test_equal_inspection_results_compare_and_hash_equal(
    inspection_result: X12InspectionResult,
) -> None:
    """Equivalent inspection results should compare and hash equally."""
    copy = X12InspectionResult(
        interchange_version=inspection_result.interchange_version,
        interchange_control_number=inspection_result.interchange_control_number,
        usage_indicator=inspection_result.usage_indicator,
        element_separator=inspection_result.element_separator,
        repetition_separator=inspection_result.repetition_separator,
        component_separator=inspection_result.component_separator,
        segment_terminator=inspection_result.segment_terminator,
        declared_group_count=inspection_result.declared_group_count,
        actual_group_count=inspection_result.actual_group_count,
        total_transaction_count=inspection_result.total_transaction_count,
        total_segment_count=inspection_result.total_segment_count,
        groups=inspection_result.groups,
        segment_frequencies=inspection_result.segment_frequencies,
    )

    assert copy == inspection_result
    assert hash(copy) == hash(inspection_result)
    assert inspection_result in {inspection_result}
