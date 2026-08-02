"""
tests/core/test_segments.py

Tests for immutable X12 segment and document models.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from x12.core.segments import X12Document, X12Segment
from x12.core.separators import X12Separators


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
    """Return a generic ISA segment."""
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
def st_segment() -> X12Segment:
    """Return a generic ST segment."""
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
def detail_segment() -> X12Segment:
    """Return a generic transaction detail segment."""
    return X12Segment(
        index=3,
        tag="N1",
        elements=(
            b"SH",
            b"SAMPLE-PARTY",
            b"",
            b"EXTRA",
        ),
        raw=b"N1*SH*SAMPLE-PARTY**EXTRA",
    )


@pytest.fixture
def iea_segment() -> X12Segment:
    """Return a generic IEA segment."""
    return X12Segment(
        index=6,
        tag="IEA",
        elements=(
            b"1",
            b"000000001",
        ),
        raw=b"IEA*1*000000001",
    )


@pytest.fixture
def document(
    separators: X12Separators,
    isa_segment: X12Segment,
    st_segment: X12Segment,
    detail_segment: X12Segment,
    iea_segment: X12Segment,
) -> X12Document:
    """Return a complete generic tokenized X12 document."""
    gs_segment = X12Segment(
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
    se_segment = X12Segment(
        index=4,
        tag="SE",
        elements=(
            b"3",
            b"0001",
        ),
        raw=b"SE*3*0001",
    )
    ge_segment = X12Segment(
        index=5,
        tag="GE",
        elements=(
            b"1",
            b"1",
        ),
        raw=b"GE*1*1",
    )

    segments = (
        isa_segment,
        gs_segment,
        st_segment,
        detail_segment,
        se_segment,
        ge_segment,
        iea_segment,
    )
    raw = b"~".join(segment.raw for segment in segments) + b"~"

    return X12Document(
        raw=raw,
        separators=separators,
        segments=segments,
    )


def test_segment_stores_structural_values(
    detail_segment: X12Segment,
) -> None:
    """A segment should preserve all supplied structural values."""
    assert detail_segment.index == 3
    assert detail_segment.tag == "N1"
    assert detail_segment.elements == (
        b"SH",
        b"SAMPLE-PARTY",
        b"",
        b"EXTRA",
    )
    assert detail_segment.raw == b"N1*SH*SAMPLE-PARTY**EXTRA"


def test_segment_preserves_empty_elements(
    detail_segment: X12Segment,
) -> None:
    """Empty elements should remain distinguishable from missing elements."""
    assert detail_segment.elements[2] == b""
    assert detail_segment.element(3) == b""


def test_segment_preserves_element_bytes_without_decoding(
    detail_segment: X12Segment,
) -> None:
    """Segment elements should remain in their original byte form."""
    assert all(isinstance(element, bytes) for element in detail_segment.elements)


@pytest.mark.parametrize(
    ("position", "expected"),
    [
        (1, b"SH"),
        (2, b"SAMPLE-PARTY"),
        (3, b""),
        (4, b"EXTRA"),
    ],
)
def test_segment_returns_elements_using_one_based_positions(
    detail_segment: X12Segment,
    position: int,
    expected: bytes,
) -> None:
    """Element lookup should follow one-based X12 numbering."""
    assert detail_segment.element(position) == expected


@pytest.mark.parametrize(
    "position",
    [
        5,
        10,
        100,
    ],
)
def test_segment_returns_none_for_missing_positive_position(
    detail_segment: X12Segment,
    position: int,
) -> None:
    """A positive position beyond the segment should return None."""
    assert detail_segment.element(position) is None


@pytest.mark.parametrize(
    "position",
    [
        0,
        -1,
        -10,
    ],
)
def test_segment_rejects_nonpositive_element_position(
    detail_segment: X12Segment,
    position: int,
) -> None:
    """Element positions less than one should be rejected."""
    with pytest.raises(
        ValueError,
        match="X12 element positions are one-based",
    ):
        detail_segment.element(position)


def test_segment_with_no_elements_returns_none_for_first_position() -> None:
    """A segment without elements should return None for position one."""
    segment = X12Segment(
        index=0,
        tag="IEA",
        elements=(),
        raw=b"IEA",
    )

    assert segment.element(1) is None


def test_segment_rejects_negative_index() -> None:
    """Segment indexes cannot be negative."""
    with pytest.raises(
        ValueError,
        match="segment index cannot be negative",
    ):
        X12Segment(
            index=-1,
            tag="N1",
            elements=(),
            raw=b"N1",
        )


def test_segment_requires_nonempty_tag() -> None:
    """A segment tag cannot be empty."""
    with pytest.raises(
        ValueError,
        match="segment tag cannot be empty",
    ):
        X12Segment(
            index=0,
            tag="",
            elements=(),
            raw=b"N1",
        )


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
def test_segment_requires_ascii_alphanumeric_tag(
    tag: str,
) -> None:
    """Segment tags must contain only ASCII alphanumeric characters."""
    with pytest.raises(
        ValueError,
        match="ASCII alphanumeric",
    ):
        X12Segment(
            index=0,
            tag=tag,
            elements=(),
            raw=b"N1",
        )


def test_segment_requires_nonempty_raw_data() -> None:
    """A segment must retain nonempty raw bytes."""
    with pytest.raises(
        ValueError,
        match="raw data cannot be empty",
    ):
        X12Segment(
            index=0,
            tag="N1",
            elements=(),
            raw=b"",
        )


def test_segment_is_immutable(
    detail_segment: X12Segment,
) -> None:
    """Segment fields should be immutable."""
    with pytest.raises(FrozenInstanceError):
        detail_segment.tag = "N2"  # type: ignore[misc]


def test_segment_elements_collection_is_immutable(
    detail_segment: X12Segment,
) -> None:
    """The segment element collection should be immutable."""
    with pytest.raises(TypeError):
        detail_segment.elements[0] = b"CN"  # type: ignore[index]


def test_equal_segments_compare_and_hash_equal() -> None:
    """Segments with identical values should compare and hash equally."""
    first = X12Segment(
        index=1,
        tag="ST",
        elements=(b"999", b"0001"),
        raw=b"ST*999*0001",
    )
    second = X12Segment(
        index=1,
        tag="ST",
        elements=(b"999", b"0001"),
        raw=b"ST*999*0001",
    )

    assert first == second
    assert hash(first) == hash(second)


@pytest.mark.parametrize(
    "different_segment",
    [
        X12Segment(
            index=2,
            tag="ST",
            elements=(b"999", b"0001"),
            raw=b"ST*999*0001",
        ),
        X12Segment(
            index=1,
            tag="SE",
            elements=(b"999", b"0001"),
            raw=b"ST*999*0001",
        ),
        X12Segment(
            index=1,
            tag="ST",
            elements=(b"998", b"0001"),
            raw=b"ST*999*0001",
        ),
        X12Segment(
            index=1,
            tag="ST",
            elements=(b"999", b"0001"),
            raw=b"ST*999*9999",
        ),
    ],
)
def test_segment_comparison_includes_all_fields(
    different_segment: X12Segment,
) -> None:
    """Every segment field should participate in equality comparison."""
    segment = X12Segment(
        index=1,
        tag="ST",
        elements=(b"999", b"0001"),
        raw=b"ST*999*0001",
    )

    assert segment != different_segment


def test_segment_is_hashable(
    st_segment: X12Segment,
) -> None:
    """Segments should be usable in sets and mapping keys."""
    segment_set = {st_segment}

    assert st_segment in segment_set


def test_document_stores_structural_values(
    document: X12Document,
    separators: X12Separators,
) -> None:
    """A document should preserve its raw bytes, separators, and segments."""
    assert document.separators is separators
    assert len(document.segments) == 7
    assert document.raw.startswith(b"ISA")
    assert document.raw.endswith(b"IEA*1*000000001~")


def test_document_preserves_exact_raw_bytes(
    document: X12Document,
) -> None:
    """The document should retain its supplied raw bytes object."""
    expected = document.raw

    assert document.raw is expected
    assert isinstance(document.raw, bytes)


def test_document_preserves_segment_order(
    document: X12Document,
) -> None:
    """Segments should remain in their supplied document order."""
    assert tuple(segment.tag for segment in document.segments) == (
        "ISA",
        "GS",
        "ST",
        "N1",
        "SE",
        "GE",
        "IEA",
    )
    assert tuple(segment.index for segment in document.segments) == (
        0,
        1,
        2,
        3,
        4,
        5,
        6,
    )


def test_document_first_segment_returns_first_stored_segment(
    document: X12Document,
    isa_segment: X12Segment,
) -> None:
    """first_segment should return the first stored segment."""
    assert document.first_segment is isa_segment


def test_document_last_segment_returns_last_stored_segment(
    document: X12Document,
    iea_segment: X12Segment,
) -> None:
    """last_segment should return the final stored segment."""
    assert document.last_segment is iea_segment


def test_document_len_returns_segment_count(
    document: X12Document,
) -> None:
    """len(document) should return the number of segments."""
    assert len(document) == 7


def test_document_iteration_preserves_segment_order(
    document: X12Document,
) -> None:
    """Iteration should yield segments in document order."""
    assert tuple(document) == document.segments


@pytest.mark.parametrize(
    ("tag", "expected_count"),
    [
        ("ISA", 1),
        ("GS", 1),
        ("ST", 1),
        ("N1", 1),
        ("SE", 1),
        ("GE", 1),
        ("IEA", 1),
        ("DTM", 0),
    ],
)
def test_document_finds_segments_by_exact_tag(
    document: X12Document,
    tag: str,
    expected_count: int,
) -> None:
    """find_segments should return all exact tag matches."""
    assert len(document.find_segments(tag)) == expected_count


def test_document_find_segments_returns_matching_segments_in_order(
    separators: X12Separators,
) -> None:
    """Matching segments should be returned in document order."""
    first = X12Segment(
        index=0,
        tag="N1",
        elements=(b"SH", b"PARTY-ONE"),
        raw=b"N1*SH*PARTY-ONE",
    )
    unrelated = X12Segment(
        index=1,
        tag="DTM",
        elements=(b"011", b"20260101"),
        raw=b"DTM*011*20260101",
    )
    second = X12Segment(
        index=2,
        tag="N1",
        elements=(b"CN", b"PARTY-TWO"),
        raw=b"N1*CN*PARTY-TWO",
    )

    document = X12Document(
        raw=(b"N1*SH*PARTY-ONE~DTM*011*20260101~N1*CN*PARTY-TWO~"),
        separators=separators,
        segments=(
            first,
            unrelated,
            second,
        ),
    )

    assert document.find_segments("N1") == (
        first,
        second,
    )


def test_document_find_segments_returns_empty_tuple_when_absent(
    document: X12Document,
) -> None:
    """An absent segment tag should return an empty tuple."""
    result = document.find_segments("R4")

    assert result == ()
    assert isinstance(result, tuple)


@pytest.mark.parametrize(
    "tag",
    [
        "n1",
        "N",
        "N10",
        "",
        " N1",
        "N1 ",
    ],
)
def test_document_find_segments_uses_exact_case_sensitive_match(
    document: X12Document,
    tag: str,
) -> None:
    """Tag matching should be exact and case-sensitive."""
    assert document.find_segments(tag) == ()


def test_document_find_segments_returns_new_tuple(
    document: X12Document,
) -> None:
    """Each find operation should return an independent tuple."""
    first_result = document.find_segments("N1")
    second_result = document.find_segments("N1")

    assert first_result == second_result
    assert first_result is not second_result


def test_document_find_segments_does_not_mutate_document(
    document: X12Document,
) -> None:
    """Finding segments should not replace or mutate stored segments."""
    original_segments = document.segments

    document.find_segments("N1")

    assert document.segments is original_segments


def test_document_requires_nonempty_raw_data(
    separators: X12Separators,
) -> None:
    """A document must retain nonempty raw bytes."""
    segment = X12Segment(
        index=0,
        tag="ISA",
        elements=(),
        raw=b"ISA",
    )

    with pytest.raises(
        ValueError,
        match="document raw data cannot be empty",
    ):
        X12Document(
            raw=b"",
            separators=separators,
            segments=(segment,),
        )


def test_document_requires_at_least_one_segment(
    separators: X12Separators,
) -> None:
    """A document cannot be created without segments."""
    with pytest.raises(
        ValueError,
        match="must contain at least one segment",
    ):
        X12Document(
            raw=b"ISA~",
            separators=separators,
            segments=(),
        )


@pytest.mark.parametrize(
    ("indexes", "expected_index", "found_index"),
    [
        ((1,), 0, 1),
        ((0, 2), 1, 2),
        ((0, 1, 3), 2, 3),
    ],
)
def test_document_requires_contiguous_matching_segment_indexes(
    separators: X12Separators,
    indexes: tuple[int, ...],
    expected_index: int,
    found_index: int,
) -> None:
    """Segment indexes should match contiguous document positions."""
    segments = tuple(
        X12Segment(
            index=index,
            tag=f"S{position}",
            elements=(),
            raw=f"S{position}".encode("ascii"),
        )
        for position, index in enumerate(indexes)
    )

    with pytest.raises(
        ValueError,
        match=(
            "segment indexes must be contiguous and match their "
            f"document positions; expected {expected_index}, found "
            f"{found_index}"
        ),
    ):
        X12Document(
            raw=b"~".join(segment.raw for segment in segments) + b"~",
            separators=separators,
            segments=segments,
        )


def test_document_is_immutable(
    document: X12Document,
) -> None:
    """Document fields should be immutable."""
    with pytest.raises(FrozenInstanceError):
        document.raw = b"changed"  # type: ignore[misc]


def test_document_segments_collection_is_immutable(
    document: X12Document,
) -> None:
    """The document segment collection should be immutable."""
    with pytest.raises(TypeError):
        document.segments[0] = document.segments[-1]  # type: ignore[index]


def test_document_is_hashable(
    document: X12Document,
) -> None:
    """Documents should be usable in sets and mapping keys."""
    document_set = {document}

    assert document in document_set


def test_equal_documents_compare_and_hash_equal(
    document: X12Document,
) -> None:
    """Documents with identical values should compare and hash equally."""
    copy = X12Document(
        raw=document.raw,
        separators=document.separators,
        segments=document.segments,
    )

    assert copy == document
    assert hash(copy) == hash(document)


def test_document_comparison_includes_raw_payload(
    document: X12Document,
) -> None:
    """Raw payload bytes should participate in document equality."""
    changed = X12Document(
        raw=document.raw + b"\r\n",
        separators=document.separators,
        segments=document.segments,
    )

    assert changed != document


def test_document_comparison_includes_separators(
    document: X12Document,
) -> None:
    """Separators should participate in document equality."""
    changed = X12Document(
        raw=document.raw,
        separators=X12Separators(
            element=b"|",
            repetition=b"^",
            component=b">",
            segment=b"!",
        ),
        segments=document.segments,
    )

    assert changed != document


def test_document_comparison_includes_segments(
    document: X12Document,
) -> None:
    """Stored segments should participate in document equality."""
    replacement = X12Segment(
        index=6,
        tag="IEA",
        elements=(b"2", b"000000001"),
        raw=b"IEA*2*000000001",
    )
    changed = X12Document(
        raw=document.raw,
        separators=document.separators,
        segments=(
            *document.segments[:-1],
            replacement,
        ),
    )

    assert changed != document
