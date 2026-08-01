"""
tests/test_envelopes.py

Tests for immutable X12 envelope models.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from x12.envelopes import (
    X12FunctionalGroup,
    X12Interchange,
    X12TransactionSet,
)
from x12.segments import X12Document, X12Segment
from x12.separators import X12Separators


@pytest.fixture
def separators() -> X12Separators:
    """Return a standard set of X12 separators."""
    return X12Separators(
        element=b"*",
        repetition=b"^",
        component=b":",
        segment=b"~",
    )


@pytest.fixture
def isa_segment() -> X12Segment:
    """Return a generic ISA interchange header."""
    return X12Segment(
        index=0,
        tag="ISA",
        elements=(
            b"00",
            b"          ",
            b"00",
            b"          ",
            b"ZZ",
            b"SENDER01       ",
            b"ZZ",
            b"RECEIVER01     ",
            b"260101",
            b"1200",
            b"^",
            b"00705",
            b"000000001",
            b"0",
            b"T",
            b":",
        ),
        raw=(
            b"ISA*00*          *00*          *ZZ*SENDER01       "
            b"*ZZ*RECEIVER01     *260101*1200*^*00705"
            b"*000000001*0*T*:"
        ),
    )


@pytest.fixture
def gs_segment() -> X12Segment:
    """Return a generic GS functional-group header."""
    return X12Segment(
        index=1,
        tag="GS",
        elements=(
            b"XX",
            b"SENDER01",
            b"RECEIVER01",
            b"20260101",
            b"1200",
            b"1",
            b"X",
            b"007050",
        ),
        raw=b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050",
    )


@pytest.fixture
def first_st_segment() -> X12Segment:
    """Return the first transaction-set header."""
    return X12Segment(
        index=2,
        tag="ST",
        elements=(
            b"999",
            b"0001",
        ),
        raw=b"ST*999*0001",
    )


@pytest.fixture
def first_body_segments() -> tuple[X12Segment, ...]:
    """Return the first transaction set's body segments."""
    return (
        X12Segment(
            index=3,
            tag="N1",
            elements=(
                b"SH",
                b"SAMPLE-PARTY",
                b"",
                b"EXTRA",
            ),
            raw=b"N1*SH*SAMPLE-PARTY**EXTRA",
        ),
        X12Segment(
            index=4,
            tag="DTM",
            elements=(
                b"011",
                b"20260101",
                b"1200",
            ),
            raw=b"DTM*011*20260101*1200",
        ),
    )


@pytest.fixture
def first_se_segment() -> X12Segment:
    """Return the first transaction-set trailer."""
    return X12Segment(
        index=5,
        tag="SE",
        elements=(
            b"4",
            b"0001",
        ),
        raw=b"SE*4*0001",
    )


@pytest.fixture
def first_transaction(
    first_st_segment: X12Segment,
    first_body_segments: tuple[X12Segment, ...],
    first_se_segment: X12Segment,
) -> X12TransactionSet:
    """Return a transaction set containing two body segments."""
    return X12TransactionSet(
        header=first_st_segment,
        segments=first_body_segments,
        trailer=first_se_segment,
    )


@pytest.fixture
def second_transaction() -> X12TransactionSet:
    """Return a transaction set without body segments."""
    return X12TransactionSet(
        header=X12Segment(
            index=6,
            tag="ST",
            elements=(
                b"999",
                b"0002",
            ),
            raw=b"ST*999*0002",
        ),
        segments=(),
        trailer=X12Segment(
            index=7,
            tag="SE",
            elements=(
                b"2",
                b"0002",
            ),
            raw=b"SE*2*0002",
        ),
    )


@pytest.fixture
def ge_segment() -> X12Segment:
    """Return a functional-group trailer."""
    return X12Segment(
        index=8,
        tag="GE",
        elements=(
            b"2",
            b"1",
        ),
        raw=b"GE*2*1",
    )


@pytest.fixture
def iea_segment() -> X12Segment:
    """Return an interchange trailer."""
    return X12Segment(
        index=9,
        tag="IEA",
        elements=(
            b"1",
            b"000000001",
        ),
        raw=b"IEA*1*000000001",
    )


@pytest.fixture
def functional_group(
    gs_segment: X12Segment,
    ge_segment: X12Segment,
    first_transaction: X12TransactionSet,
    second_transaction: X12TransactionSet,
) -> X12FunctionalGroup:
    """Return a functional group containing two transaction sets."""
    return X12FunctionalGroup(
        header=gs_segment,
        transactions=(
            first_transaction,
            second_transaction,
        ),
        trailer=ge_segment,
    )


@pytest.fixture
def document(
    separators: X12Separators,
    isa_segment: X12Segment,
    iea_segment: X12Segment,
    functional_group: X12FunctionalGroup,
) -> X12Document:
    """Return a complete tokenized document matching the envelope hierarchy."""
    segments = (
        isa_segment,
        *functional_group.all_segments,
        iea_segment,
    )
    raw = b"~".join(segment.raw for segment in segments) + b"~"

    return X12Document(
        raw=raw,
        separators=separators,
        segments=segments,
    )


@pytest.fixture
def interchange(
    document: X12Document,
    isa_segment: X12Segment,
    iea_segment: X12Segment,
    functional_group: X12FunctionalGroup,
) -> X12Interchange:
    """Return a complete interchange containing one functional group."""
    return X12Interchange(
        document=document,
        header=isa_segment,
        groups=(functional_group,),
        trailer=iea_segment,
    )


def test_transaction_set_stores_structural_values(
    first_transaction: X12TransactionSet,
    first_st_segment: X12Segment,
    first_body_segments: tuple[X12Segment, ...],
    first_se_segment: X12Segment,
) -> None:
    """A transaction set should preserve its supplied components."""
    assert first_transaction.header is first_st_segment
    assert first_transaction.segments is first_body_segments
    assert first_transaction.trailer is first_se_segment


def test_transaction_set_returns_header_values(
    first_transaction: X12TransactionSet,
) -> None:
    """Transaction-set properties should expose ST values."""
    assert first_transaction.transaction_set_code == b"999"
    assert first_transaction.control_number == b"0001"


def test_transaction_set_returns_trailer_control_number(
    first_transaction: X12TransactionSet,
) -> None:
    """trailer_control_number should expose SE02."""
    assert first_transaction.trailer_control_number == b"0001"


def test_transaction_set_returns_declared_segment_count(
    first_transaction: X12TransactionSet,
) -> None:
    """declared_segment_count should convert SE01 to an integer."""
    assert first_transaction.declared_segment_count == 4


def test_transaction_set_returns_actual_segment_count(
    first_transaction: X12TransactionSet,
) -> None:
    """actual_segment_count should include ST, body, and SE."""
    assert first_transaction.actual_segment_count == 4


def test_transaction_set_actual_count_includes_header_and_trailer() -> None:
    """A transaction without body segments should still contain two segments."""
    transaction = X12TransactionSet(
        header=X12Segment(
            index=0,
            tag="ST",
            elements=(b"999", b"0001"),
            raw=b"ST*999*0001",
        ),
        segments=(),
        trailer=X12Segment(
            index=1,
            tag="SE",
            elements=(b"2", b"0001"),
            raw=b"SE*2*0001",
        ),
    )

    assert transaction.actual_segment_count == 2


def test_transaction_set_all_segments_preserves_order(
    first_transaction: X12TransactionSet,
    first_st_segment: X12Segment,
    first_body_segments: tuple[X12Segment, ...],
    first_se_segment: X12Segment,
) -> None:
    """all_segments should return ST, body segments, and SE in order."""
    assert first_transaction.all_segments == (
        first_st_segment,
        *first_body_segments,
        first_se_segment,
    )


def test_transaction_set_all_segments_returns_tuple(
    first_transaction: X12TransactionSet,
) -> None:
    """all_segments should return an immutable tuple."""
    assert isinstance(first_transaction.all_segments, tuple)


def test_transaction_set_missing_header_elements_return_none() -> None:
    """Missing ST elements should be exposed as None."""
    transaction = X12TransactionSet(
        header=X12Segment(
            index=0,
            tag="ST",
            elements=(),
            raw=b"ST",
        ),
        segments=(),
        trailer=X12Segment(
            index=1,
            tag="SE",
            elements=(b"2", b"0001"),
            raw=b"SE*2*0001",
        ),
    )

    assert transaction.transaction_set_code is None
    assert transaction.control_number is None


def test_transaction_set_missing_trailer_control_number_returns_none() -> None:
    """Missing SE02 should be exposed as None."""
    transaction = X12TransactionSet(
        header=X12Segment(
            index=0,
            tag="ST",
            elements=(b"999", b"0001"),
            raw=b"ST*999*0001",
        ),
        segments=(),
        trailer=X12Segment(
            index=1,
            tag="SE",
            elements=(b"2",),
            raw=b"SE*2",
        ),
    )

    assert transaction.trailer_control_number is None


@pytest.mark.parametrize(
    "elements",
    [
        (),
        (b"",),
        (b"ABC",),
        (b"1.5",),
        (b"-1",),
        (b"+2",),
        (b" 4",),
        (b"4 ",),
    ],
)
def test_transaction_set_declared_count_returns_none_when_not_numeric(
    elements: tuple[bytes, ...],
) -> None:
    """Invalid or missing SE01 values should return None."""
    transaction = X12TransactionSet(
        header=X12Segment(
            index=0,
            tag="ST",
            elements=(b"999", b"0001"),
            raw=b"ST*999*0001",
        ),
        segments=(),
        trailer=X12Segment(
            index=1,
            tag="SE",
            elements=elements,
            raw=b"SE",
        ),
    )

    assert transaction.declared_segment_count is None


@pytest.mark.parametrize(
    ("raw_count", "expected"),
    [
        (b"0", 0),
        (b"2", 2),
        (b"00004", 4),
        (b"999999", 999999),
    ],
)
def test_transaction_set_declared_count_converts_ascii_digits(
    raw_count: bytes,
    expected: int,
) -> None:
    """Decimal SE01 values should be converted to integers."""
    transaction = X12TransactionSet(
        header=X12Segment(
            index=0,
            tag="ST",
            elements=(b"999", b"0001"),
            raw=b"ST*999*0001",
        ),
        segments=(),
        trailer=X12Segment(
            index=1,
            tag="SE",
            elements=(raw_count, b"0001"),
            raw=b"SE",
        ),
    )

    assert transaction.declared_segment_count == expected


@pytest.mark.parametrize(
    ("header_tag", "trailer_tag", "match"),
    [
        ("XX", "SE", "header must be an ST segment"),
        ("ST", "XX", "trailer must be an SE segment"),
    ],
)
def test_transaction_set_requires_correct_boundary_tags(
    header_tag: str,
    trailer_tag: str,
    match: str,
) -> None:
    """Transaction boundaries must use ST and SE tags."""
    with pytest.raises(
        ValueError,
        match=match,
    ):
        X12TransactionSet(
            header=X12Segment(
                index=0,
                tag=header_tag,
                elements=(),
                raw=header_tag.encode("ascii"),
            ),
            segments=(),
            trailer=X12Segment(
                index=1,
                tag=trailer_tag,
                elements=(),
                raw=trailer_tag.encode("ascii"),
            ),
        )


def test_transaction_set_requires_contiguous_segment_indexes() -> None:
    """Transaction-set segments must be contiguous."""
    with pytest.raises(
        ValueError,
        match="transaction set segments must be contiguous",
    ):
        X12TransactionSet(
            header=X12Segment(
                index=0,
                tag="ST",
                elements=(),
                raw=b"ST",
            ),
            segments=(
                X12Segment(
                    index=2,
                    tag="N1",
                    elements=(),
                    raw=b"N1",
                ),
            ),
            trailer=X12Segment(
                index=3,
                tag="SE",
                elements=(),
                raw=b"SE",
            ),
        )


def test_transaction_set_is_immutable(
    first_transaction: X12TransactionSet,
) -> None:
    """Transaction-set fields should be immutable."""
    with pytest.raises(FrozenInstanceError):
        first_transaction.segments = ()  # type: ignore[misc]


def test_transaction_set_collection_is_immutable(
    first_transaction: X12TransactionSet,
) -> None:
    """The transaction body collection should be immutable."""
    with pytest.raises(TypeError):
        first_transaction.segments[0] = first_transaction.header  # type: ignore[index]


def test_transaction_set_is_hashable(
    first_transaction: X12TransactionSet,
) -> None:
    """Transaction sets should be hashable."""
    transaction_sets = {first_transaction}

    assert first_transaction in transaction_sets


def test_equal_transaction_sets_compare_and_hash_equal(
    first_transaction: X12TransactionSet,
) -> None:
    """Equivalent transaction sets should compare and hash equally."""
    copy = X12TransactionSet(
        header=first_transaction.header,
        segments=first_transaction.segments,
        trailer=first_transaction.trailer,
    )

    assert copy == first_transaction
    assert hash(copy) == hash(first_transaction)


def test_functional_group_stores_structural_values(
    functional_group: X12FunctionalGroup,
    gs_segment: X12Segment,
    ge_segment: X12Segment,
    first_transaction: X12TransactionSet,
    second_transaction: X12TransactionSet,
) -> None:
    """A group should preserve its supplied structural values."""
    assert functional_group.header is gs_segment
    assert functional_group.transactions == (
        first_transaction,
        second_transaction,
    )
    assert functional_group.trailer is ge_segment


def test_functional_group_returns_header_values(
    functional_group: X12FunctionalGroup,
) -> None:
    """Functional-group properties should expose GS values."""
    assert functional_group.functional_identifier_code == b"XX"
    assert functional_group.application_sender_code == b"SENDER01"
    assert functional_group.application_receiver_code == b"RECEIVER01"
    assert functional_group.control_number == b"1"
    assert functional_group.implementation_version == b"007050"


def test_functional_group_returns_trailer_control_number(
    functional_group: X12FunctionalGroup,
) -> None:
    """trailer_control_number should expose GE02."""
    assert functional_group.trailer_control_number == b"1"


def test_functional_group_returns_declared_transaction_count(
    functional_group: X12FunctionalGroup,
) -> None:
    """declared_transaction_count should convert GE01."""
    assert functional_group.declared_transaction_count == 2


def test_functional_group_returns_actual_transaction_count(
    functional_group: X12FunctionalGroup,
) -> None:
    """actual_transaction_count should count transaction sets."""
    assert functional_group.actual_transaction_count == 2


def test_functional_group_all_segments_flattens_transactions_in_order(
    functional_group: X12FunctionalGroup,
    first_transaction: X12TransactionSet,
    second_transaction: X12TransactionSet,
) -> None:
    """all_segments should flatten transaction sets in document order."""
    assert functional_group.all_segments == (
        functional_group.header,
        *first_transaction.all_segments,
        *second_transaction.all_segments,
        functional_group.trailer,
    )


def test_functional_group_with_no_transactions_has_two_segments() -> None:
    """A group without transactions should contain only GS and GE."""
    header = X12Segment(
        index=0,
        tag="GS",
        elements=(),
        raw=b"GS",
    )
    trailer = X12Segment(
        index=1,
        tag="GE",
        elements=(b"0", b"1"),
        raw=b"GE*0*1",
    )
    group = X12FunctionalGroup(
        header=header,
        transactions=(),
        trailer=trailer,
    )

    assert group.actual_transaction_count == 0
    assert group.declared_transaction_count == 0
    assert group.all_segments == (
        header,
        trailer,
    )


def test_functional_group_missing_header_elements_return_none() -> None:
    """Missing GS elements should be exposed as None."""
    group = X12FunctionalGroup(
        header=X12Segment(
            index=0,
            tag="GS",
            elements=(),
            raw=b"GS",
        ),
        transactions=(),
        trailer=X12Segment(
            index=1,
            tag="GE",
            elements=(b"0", b"1"),
            raw=b"GE*0*1",
        ),
    )

    assert group.functional_identifier_code is None
    assert group.application_sender_code is None
    assert group.application_receiver_code is None
    assert group.control_number is None
    assert group.implementation_version is None


def test_functional_group_missing_trailer_control_number_returns_none() -> None:
    """Missing GE02 should be exposed as None."""
    group = X12FunctionalGroup(
        header=X12Segment(
            index=0,
            tag="GS",
            elements=(),
            raw=b"GS",
        ),
        transactions=(),
        trailer=X12Segment(
            index=1,
            tag="GE",
            elements=(b"0",),
            raw=b"GE*0",
        ),
    )

    assert group.trailer_control_number is None


@pytest.mark.parametrize(
    "elements",
    [
        (),
        (b"",),
        (b"ABC",),
        (b"-1",),
        (b"+1",),
        (b"1.0",),
    ],
)
def test_functional_group_declared_count_returns_none_when_not_numeric(
    elements: tuple[bytes, ...],
) -> None:
    """Invalid or missing GE01 values should return None."""
    group = X12FunctionalGroup(
        header=X12Segment(
            index=0,
            tag="GS",
            elements=(),
            raw=b"GS",
        ),
        transactions=(),
        trailer=X12Segment(
            index=1,
            tag="GE",
            elements=elements,
            raw=b"GE",
        ),
    )

    assert group.declared_transaction_count is None


@pytest.mark.parametrize(
    ("header_tag", "trailer_tag", "match"),
    [
        ("XX", "GE", "header must be a GS segment"),
        ("GS", "XX", "trailer must be a GE segment"),
    ],
)
def test_functional_group_requires_correct_boundary_tags(
    header_tag: str,
    trailer_tag: str,
    match: str,
) -> None:
    """Functional-group boundaries must use GS and GE tags."""
    with pytest.raises(
        ValueError,
        match=match,
    ):
        X12FunctionalGroup(
            header=X12Segment(
                index=0,
                tag=header_tag,
                elements=(),
                raw=header_tag.encode("ascii"),
            ),
            transactions=(),
            trailer=X12Segment(
                index=1,
                tag=trailer_tag,
                elements=(),
                raw=trailer_tag.encode("ascii"),
            ),
        )


def test_functional_group_requires_contiguous_segment_indexes() -> None:
    """Functional-group segments must be contiguous."""
    transaction = X12TransactionSet(
        header=X12Segment(
            index=2,
            tag="ST",
            elements=(),
            raw=b"ST",
        ),
        segments=(),
        trailer=X12Segment(
            index=3,
            tag="SE",
            elements=(),
            raw=b"SE",
        ),
    )

    with pytest.raises(
        ValueError,
        match="functional group segments must be contiguous",
    ):
        X12FunctionalGroup(
            header=X12Segment(
                index=0,
                tag="GS",
                elements=(),
                raw=b"GS",
            ),
            transactions=(transaction,),
            trailer=X12Segment(
                index=4,
                tag="GE",
                elements=(),
                raw=b"GE",
            ),
        )


def test_functional_group_is_immutable(
    functional_group: X12FunctionalGroup,
) -> None:
    """Functional-group fields should be immutable."""
    with pytest.raises(FrozenInstanceError):
        functional_group.transactions = ()  # type: ignore[misc]


def test_functional_group_transactions_collection_is_immutable(
    functional_group: X12FunctionalGroup,
) -> None:
    """The transaction-set collection should be immutable."""
    with pytest.raises(TypeError):
        functional_group.transactions[0] = functional_group.transactions[1]  # type: ignore[index]


def test_functional_group_is_hashable(
    functional_group: X12FunctionalGroup,
) -> None:
    """Functional groups should be hashable."""
    groups = {functional_group}

    assert functional_group in groups


def test_interchange_stores_structural_values(
    interchange: X12Interchange,
    document: X12Document,
    isa_segment: X12Segment,
    iea_segment: X12Segment,
    functional_group: X12FunctionalGroup,
) -> None:
    """An interchange should preserve all supplied structural values."""
    assert interchange.document is document
    assert interchange.header is isa_segment
    assert interchange.groups == (functional_group,)
    assert interchange.trailer is iea_segment


def test_interchange_returns_header_values(
    interchange: X12Interchange,
) -> None:
    """Interchange properties should expose ISA values."""
    assert interchange.authorization_information_qualifier == b"00"
    assert interchange.security_information_qualifier == b"00"
    assert interchange.sender_qualifier == b"ZZ"
    assert interchange.sender_identifier == b"SENDER01       "
    assert interchange.receiver_qualifier == b"ZZ"
    assert interchange.receiver_identifier == b"RECEIVER01     "
    assert interchange.interchange_version == b"00705"
    assert interchange.control_number == b"000000001"
    assert interchange.usage_indicator == b"T"


def test_interchange_returns_trailer_control_number(
    interchange: X12Interchange,
) -> None:
    """trailer_control_number should expose IEA02."""
    assert interchange.trailer_control_number == b"000000001"


def test_interchange_preserves_fixed_width_identifier_padding(
    interchange: X12Interchange,
) -> None:
    """Fixed-width ISA identifiers should retain their padding."""
    assert interchange.sender_identifier == b"SENDER01       "
    assert interchange.receiver_identifier == b"RECEIVER01     "


def test_interchange_returns_declared_group_count(
    interchange: X12Interchange,
) -> None:
    """declared_group_count should convert IEA01."""
    assert interchange.declared_group_count == 1


def test_interchange_returns_actual_group_count(
    interchange: X12Interchange,
) -> None:
    """actual_group_count should count functional groups."""
    assert interchange.actual_group_count == 1


def test_interchange_all_segments_flattens_groups_in_order(
    interchange: X12Interchange,
    functional_group: X12FunctionalGroup,
) -> None:
    """all_segments should flatten groups in document order."""
    assert interchange.all_segments == (
        interchange.header,
        *functional_group.all_segments,
        interchange.trailer,
    )


def test_interchange_all_segments_matches_document_segments(
    interchange: X12Interchange,
) -> None:
    """The envelope hierarchy should match its source document."""
    assert interchange.all_segments == interchange.document.segments


def test_interchange_with_no_groups_has_two_segments(
    separators: X12Separators,
) -> None:
    """An interchange without groups should contain ISA and IEA."""
    header = X12Segment(
        index=0,
        tag="ISA",
        elements=(),
        raw=b"ISA",
    )
    trailer = X12Segment(
        index=1,
        tag="IEA",
        elements=(b"0", b"000000001"),
        raw=b"IEA*0*000000001",
    )
    document = X12Document(
        raw=b"ISA~IEA*0*000000001~",
        separators=separators,
        segments=(
            header,
            trailer,
        ),
    )
    interchange = X12Interchange(
        document=document,
        header=header,
        groups=(),
        trailer=trailer,
    )

    assert interchange.actual_group_count == 0
    assert interchange.declared_group_count == 0
    assert interchange.all_segments == (
        header,
        trailer,
    )


def test_interchange_missing_header_elements_return_none(
    separators: X12Separators,
) -> None:
    """Missing ISA elements should be exposed as None."""
    header = X12Segment(
        index=0,
        tag="ISA",
        elements=(),
        raw=b"ISA",
    )
    trailer = X12Segment(
        index=1,
        tag="IEA",
        elements=(b"0", b"000000001"),
        raw=b"IEA*0*000000001",
    )
    document = X12Document(
        raw=b"ISA~IEA*0*000000001~",
        separators=separators,
        segments=(
            header,
            trailer,
        ),
    )
    interchange = X12Interchange(
        document=document,
        header=header,
        groups=(),
        trailer=trailer,
    )

    assert interchange.authorization_information_qualifier is None
    assert interchange.security_information_qualifier is None
    assert interchange.sender_qualifier is None
    assert interchange.sender_identifier is None
    assert interchange.receiver_qualifier is None
    assert interchange.receiver_identifier is None
    assert interchange.interchange_version is None
    assert interchange.control_number is None
    assert interchange.usage_indicator is None


def test_interchange_missing_trailer_control_number_returns_none(
    separators: X12Separators,
) -> None:
    """Missing IEA02 should be exposed as None."""
    header = X12Segment(
        index=0,
        tag="ISA",
        elements=(),
        raw=b"ISA",
    )
    trailer = X12Segment(
        index=1,
        tag="IEA",
        elements=(b"0",),
        raw=b"IEA*0",
    )
    document = X12Document(
        raw=b"ISA~IEA*0~",
        separators=separators,
        segments=(
            header,
            trailer,
        ),
    )
    interchange = X12Interchange(
        document=document,
        header=header,
        groups=(),
        trailer=trailer,
    )

    assert interchange.trailer_control_number is None


@pytest.mark.parametrize(
    "elements",
    [
        (),
        (b"",),
        (b"ABC",),
        (b"-1",),
        (b"+1",),
        (b"1.0",),
    ],
)
def test_interchange_declared_count_returns_none_when_not_numeric(
    elements: tuple[bytes, ...],
    separators: X12Separators,
) -> None:
    """Invalid or missing IEA01 values should return None."""
    header = X12Segment(
        index=0,
        tag="ISA",
        elements=(),
        raw=b"ISA",
    )
    trailer = X12Segment(
        index=1,
        tag="IEA",
        elements=elements,
        raw=b"IEA",
    )
    document = X12Document(
        raw=b"ISA~IEA~",
        separators=separators,
        segments=(
            header,
            trailer,
        ),
    )
    interchange = X12Interchange(
        document=document,
        header=header,
        groups=(),
        trailer=trailer,
    )

    assert interchange.declared_group_count is None


@pytest.mark.parametrize(
    ("header_tag", "trailer_tag", "match"),
    [
        ("XX", "IEA", "header must be an ISA segment"),
        ("ISA", "XX", "trailer must be an IEA segment"),
    ],
)
def test_interchange_requires_correct_boundary_tags(
    separators: X12Separators,
    header_tag: str,
    trailer_tag: str,
    match: str,
) -> None:
    """Interchange boundaries must use ISA and IEA tags."""
    header = X12Segment(
        index=0,
        tag=header_tag,
        elements=(),
        raw=header_tag.encode("ascii"),
    )
    trailer = X12Segment(
        index=1,
        tag=trailer_tag,
        elements=(),
        raw=trailer_tag.encode("ascii"),
    )
    document = X12Document(
        raw=header.raw + b"~" + trailer.raw + b"~",
        separators=separators,
        segments=(
            header,
            trailer,
        ),
    )

    with pytest.raises(
        ValueError,
        match=match,
    ):
        X12Interchange(
            document=document,
            header=header,
            groups=(),
            trailer=trailer,
        )


def test_interchange_requires_contiguous_segment_indexes(
    separators: X12Separators,
) -> None:
    """Interchange envelope segments must be contiguous."""
    header = X12Segment(
        index=0,
        tag="ISA",
        elements=(),
        raw=b"ISA",
    )
    group = X12FunctionalGroup(
        header=X12Segment(
            index=2,
            tag="GS",
            elements=(),
            raw=b"GS",
        ),
        transactions=(),
        trailer=X12Segment(
            index=3,
            tag="GE",
            elements=(),
            raw=b"GE",
        ),
    )
    trailer = X12Segment(
        index=4,
        tag="IEA",
        elements=(),
        raw=b"IEA",
    )
    document = X12Document(
        raw=b"ISA~GS~GE~IEA~",
        separators=separators,
        segments=(
            header,
            X12Segment(
                index=1,
                tag="GS",
                elements=(),
                raw=b"GS",
            ),
            X12Segment(
                index=2,
                tag="GE",
                elements=(),
                raw=b"GE",
            ),
            X12Segment(
                index=3,
                tag="IEA",
                elements=(),
                raw=b"IEA",
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="interchange segments must be contiguous",
    ):
        X12Interchange(
            document=document,
            header=header,
            groups=(group,),
            trailer=trailer,
        )


def test_interchange_requires_source_document_consistency(
    separators: X12Separators,
) -> None:
    """The envelope hierarchy must exactly match its source document."""
    header = X12Segment(
        index=0,
        tag="ISA",
        elements=(),
        raw=b"ISA",
    )
    expected_trailer = X12Segment(
        index=1,
        tag="IEA",
        elements=(b"0", b"000000001"),
        raw=b"IEA*0*000000001",
    )
    document = X12Document(
        raw=b"ISA~IEA*0*000000001~",
        separators=separators,
        segments=(
            header,
            expected_trailer,
        ),
    )
    different_trailer = X12Segment(
        index=1,
        tag="IEA",
        elements=(b"1", b"000000001"),
        raw=b"IEA*1*000000001",
    )

    with pytest.raises(
        ValueError,
        match="must exactly match the segments in its source document",
    ):
        X12Interchange(
            document=document,
            header=header,
            groups=(),
            trailer=different_trailer,
        )


def test_interchange_is_immutable(
    interchange: X12Interchange,
) -> None:
    """Interchange fields should be immutable."""
    with pytest.raises(FrozenInstanceError):
        interchange.groups = ()  # type: ignore[misc]


def test_interchange_groups_collection_is_immutable(
    interchange: X12Interchange,
) -> None:
    """The functional-group collection should be immutable."""
    with pytest.raises(TypeError):
        interchange.groups[0] = interchange.groups[0]  # type: ignore[index]


def test_interchange_is_hashable(
    interchange: X12Interchange,
) -> None:
    """Interchanges should be hashable."""
    interchanges = {interchange}

    assert interchange in interchanges


def test_equal_interchanges_compare_and_hash_equal(
    interchange: X12Interchange,
) -> None:
    """Equivalent interchanges should compare and hash equally."""
    copy = X12Interchange(
        document=interchange.document,
        header=interchange.header,
        groups=interchange.groups,
        trailer=interchange.trailer,
    )

    assert copy == interchange
    assert hash(copy) == hash(interchange)


def test_interchange_comparison_includes_document(
    interchange: X12Interchange,
) -> None:
    """The source document should participate in equality."""
    changed_document = X12Document(
        raw=interchange.document.raw + b"\r\n",
        separators=interchange.document.separators,
        segments=interchange.document.segments,
    )
    changed = X12Interchange(
        document=changed_document,
        header=interchange.header,
        groups=interchange.groups,
        trailer=interchange.trailer,
    )

    assert changed != interchange
