"""
tests/core/test_separators.py

Tests for X12 separator discovery and validation.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from x12.core.exceptions import (
    X12EnvelopeError,
    X12SeparatorError,
)
from x12.core.separators import (
    ISA_COMPONENT_SEPARATOR_INDEX,
    ISA_ELEMENT_SEPARATOR_INDEX,
    ISA_ELEMENT_SEPARATOR_INDICES,
    ISA_REPETITION_SEPARATOR_INDEX,
    ISA_SEGMENT_LENGTH,
    ISA_SEGMENT_TERMINATOR_INDEX,
    ISA_VERSION_END_INDEX,
    ISA_VERSION_START_INDEX,
    X12Separators,
    derive_x12_separators,
)


def build_isa_segment(
    *,
    element: bytes = b"*",
    repetition: bytes = b"^",
    component: bytes = b":",
    terminator: bytes = b"~",
    version: bytes = b"00705",
) -> bytes:
    """Build a generic, valid, fixed-width ISA segment."""
    values = (
        b"00",
        b"".ljust(10),
        b"00",
        b"".ljust(10),
        b"ZZ",
        b"SENDER01".ljust(15),
        b"ZZ",
        b"RECEIVER01".ljust(15),
        b"260101",
        b"1200",
        repetition,
        version,
        b"000000001",
        b"0",
        b"T",
        component,
    )

    isa = b"ISA" + element + element.join(values) + terminator

    assert len(isa) == ISA_SEGMENT_LENGTH
    return isa


def test_isa_segment_length_matches_x12_fixed_width() -> None:
    """ISA should occupy exactly 106 bytes including its terminator."""
    assert ISA_SEGMENT_LENGTH == 106
    assert len(build_isa_segment()) == ISA_SEGMENT_LENGTH


def test_isa_separator_indices_point_to_expected_bytes() -> None:
    """ISA offsets should locate the expected separator bytes."""
    isa = build_isa_segment()

    assert isa[ISA_ELEMENT_SEPARATOR_INDEX : ISA_ELEMENT_SEPARATOR_INDEX + 1] == b"*"
    assert (
        isa[ISA_REPETITION_SEPARATOR_INDEX : ISA_REPETITION_SEPARATOR_INDEX + 1] == b"^"
    )
    assert (
        isa[ISA_COMPONENT_SEPARATOR_INDEX : ISA_COMPONENT_SEPARATOR_INDEX + 1] == b":"
    )
    assert isa[ISA_SEGMENT_TERMINATOR_INDEX : ISA_SEGMENT_TERMINATOR_INDEX + 1] == b"~"
    assert isa[ISA_VERSION_START_INDEX:ISA_VERSION_END_INDEX] == b"00705"


def test_all_fixed_width_element_positions_contain_separator() -> None:
    """Every fixed-width ISA element boundary should use the separator."""
    isa = build_isa_segment()

    assert all(
        isa[index : index + 1] == b"*" for index in ISA_ELEMENT_SEPARATOR_INDICES
    )


def test_separators_store_configured_values() -> None:
    """Separator values should remain available unchanged."""
    separators = X12Separators(
        element=b"*",
        repetition=b"^",
        component=b":",
        segment=b"~",
    )

    assert separators.element == b"*"
    assert separators.repetition == b"^"
    assert separators.component == b":"
    assert separators.segment == b"~"


def test_separators_allow_missing_repetition_separator() -> None:
    """Legacy interchanges may not define a repetition separator."""
    separators = X12Separators(
        element=b"*",
        repetition=None,
        component=b":",
        segment=b"~",
    )

    assert separators.repetition is None


def test_separators_are_immutable() -> None:
    """Separator objects should be immutable value objects."""
    separators = X12Separators(
        element=b"*",
        repetition=b"^",
        component=b":",
        segment=b"~",
    )

    with pytest.raises(FrozenInstanceError):
        separators.element = b"|"  # type: ignore[misc]


def test_equal_separators_compare_equal() -> None:
    """Equal separator values should compare and hash equally."""
    first = X12Separators(
        element=b"*",
        repetition=b"^",
        component=b":",
        segment=b"~",
    )
    second = X12Separators(
        element=b"*",
        repetition=b"^",
        component=b":",
        segment=b"~",
    )

    assert first == second
    assert hash(first) == hash(second)


@pytest.mark.parametrize(
    "changed",
    [
        X12Separators(
            element=b"|",
            repetition=b"^",
            component=b":",
            segment=b"~",
        ),
        X12Separators(
            element=b"*",
            repetition=b"+",
            component=b":",
            segment=b"~",
        ),
        X12Separators(
            element=b"*",
            repetition=b"^",
            component=b">",
            segment=b"~",
        ),
        X12Separators(
            element=b"*",
            repetition=b"^",
            component=b":",
            segment=b"!",
        ),
        X12Separators(
            element=b"*",
            repetition=None,
            component=b":",
            segment=b"~",
        ),
    ],
)
def test_separator_comparison_includes_all_fields(
    changed: X12Separators,
) -> None:
    """Every separator field should participate in equality comparison."""
    separators = X12Separators(
        element=b"*",
        repetition=b"^",
        component=b":",
        segment=b"~",
    )

    assert separators != changed


def test_separators_are_hashable() -> None:
    """Separator objects should be usable in sets and mapping keys."""
    separators = X12Separators(
        element=b"*",
        repetition=b"^",
        component=b":",
        segment=b"~",
    )

    separator_set = {separators}

    assert separators in separator_set


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("element", b""),
        ("component", b""),
        ("segment", b""),
        ("repetition", b""),
        ("element", b"**"),
        ("component", b"::"),
        ("segment", b"~~"),
        ("repetition", b"^^"),
    ],
)
def test_separators_require_exactly_one_byte(
    field: str,
    value: bytes,
) -> None:
    """Configured separators should contain exactly one byte."""
    values: dict[str, bytes | None] = {
        "element": b"*",
        "repetition": b"^",
        "component": b":",
        "segment": b"~",
    }
    values[field] = value

    with pytest.raises(
        X12SeparatorError,
        match="exactly one byte",
    ):
        X12Separators(
            element=values["element"],  # type: ignore[arg-type]
            repetition=values["repetition"],
            component=values["component"],  # type: ignore[arg-type]
            segment=values["segment"],  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("element", "*"),
        ("component", ":"),
        ("segment", "~"),
        ("repetition", "^"),
    ],
)
def test_separators_require_bytes(
    field: str,
    value: str,
) -> None:
    """Configured separators should reject non-bytes values."""
    values: dict[str, bytes | str | None] = {
        "element": b"*",
        "repetition": b"^",
        "component": b":",
        "segment": b"~",
    }
    values[field] = value

    with pytest.raises(
        TypeError,
        match="must be bytes",
    ):
        X12Separators(
            element=values["element"],  # type: ignore[arg-type]
            repetition=values["repetition"],  # type: ignore[arg-type]
            component=values["component"],  # type: ignore[arg-type]
            segment=values["segment"],  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("element", "component", "segment"),
    [
        (b"*", b"*", b"~"),
        (b"*", b":", b"*"),
        (b"*", b":", b":"),
    ],
)
def test_required_separators_must_be_distinct(
    element: bytes,
    component: bytes,
    segment: bytes,
) -> None:
    """Element, component, and segment separators must be distinct."""
    with pytest.raises(
        X12SeparatorError,
        match="Element, component, and segment separators must be distinct",
    ):
        X12Separators(
            element=element,
            repetition=b"^",
            component=component,
            segment=segment,
        )


@pytest.mark.parametrize(
    "repetition",
    [
        b"*",
        b":",
        b"~",
    ],
)
def test_repetition_separator_must_be_distinct_when_present(
    repetition: bytes,
) -> None:
    """A repetition separator must not overlap another separator."""
    with pytest.raises(
        X12SeparatorError,
        match="Repetition separator must be distinct",
    ):
        X12Separators(
            element=b"*",
            repetition=repetition,
            component=b":",
            segment=b"~",
        )


def test_derive_separators_from_valid_modern_isa() -> None:
    """A modern ISA should expose all four separators."""
    separators = derive_x12_separators(build_isa_segment())

    assert separators == X12Separators(
        element=b"*",
        repetition=b"^",
        component=b":",
        segment=b"~",
    )


def test_derive_separators_ignores_bytes_after_isa() -> None:
    """Separator discovery should inspect only the leading ISA segment."""
    payload = build_isa_segment() + (
        b"GS*XX*SENDER01*RECEIVER01*20260101*1200*1*X*007050~ST*999*0001~"
    )

    separators = derive_x12_separators(payload)

    assert separators.element == b"*"
    assert separators.repetition == b"^"
    assert separators.component == b":"
    assert separators.segment == b"~"


@pytest.mark.parametrize(
    ("element", "repetition", "component", "terminator"),
    [
        (b"|", b"^", b">", b"!"),
        (b"+", b"?", b":", b"'"),
        (b";", b"`", b"&", b"\n"),
    ],
)
def test_derive_separators_supports_valid_custom_delimiters(
    element: bytes,
    repetition: bytes,
    component: bytes,
    terminator: bytes,
) -> None:
    """Valid custom separator combinations should be discovered exactly."""
    separators = derive_x12_separators(
        build_isa_segment(
            element=element,
            repetition=repetition,
            component=component,
            terminator=terminator,
        )
    )

    assert separators == X12Separators(
        element=element,
        repetition=repetition,
        component=component,
        segment=terminator,
    )


@pytest.mark.parametrize(
    "version",
    [
        b"00402",
        b"00501",
        b"00602",
        b"00705",
    ],
)
def test_modern_versions_use_isa11_as_repetition_separator(
    version: bytes,
) -> None:
    """Version 00402 and later should interpret ISA11 as repetition."""
    separators = derive_x12_separators(
        build_isa_segment(
            version=version,
            repetition=b"^",
        )
    )

    assert separators.repetition == b"^"


@pytest.mark.parametrize(
    "version",
    [
        b"00000",
        b"00300",
        b"00400",
        b"00401",
    ],
)
def test_legacy_versions_do_not_expose_repetition_separator(
    version: bytes,
) -> None:
    """Versions before 00402 should not expose ISA11 as repetition."""
    separators = derive_x12_separators(
        build_isa_segment(
            version=version,
            repetition=b"U",
        )
    )

    assert separators.repetition is None
    assert separators.element == b"*"
    assert separators.component == b":"
    assert separators.segment == b"~"


def test_version_00402_is_repetition_separator_boundary() -> None:
    """Version 00402 should be the repetition-separator boundary."""
    before = derive_x12_separators(
        build_isa_segment(
            version=b"00401",
            repetition=b"U",
        )
    )
    boundary = derive_x12_separators(
        build_isa_segment(
            version=b"00402",
            repetition=b"^",
        )
    )

    assert before.repetition is None
    assert boundary.repetition == b"^"


def test_derive_separators_rejects_empty_payload() -> None:
    """An empty payload cannot contain a complete ISA segment."""
    with pytest.raises(
        X12EnvelopeError,
        match="too short",
    ):
        derive_x12_separators(b"")


@pytest.mark.parametrize(
    "payload",
    [
        b"I",
        b"IS",
        b"ISA",
        b"ISA*",
        build_isa_segment()[:-1],
    ],
)
def test_derive_separators_rejects_incomplete_isa(
    payload: bytes,
) -> None:
    """Payloads shorter than one complete ISA should be rejected."""
    with pytest.raises(
        X12EnvelopeError,
        match="too short",
    ):
        derive_x12_separators(payload)


@pytest.mark.parametrize(
    "prefix",
    [
        b"isa",
        b"ISB",
        b"GS*",
        b"\xef\xbb\xbf",
        b"\r\nI",
    ],
)
def test_derive_separators_requires_isa_at_first_byte(
    prefix: bytes,
) -> None:
    """ISA must start at byte zero without a BOM or leading whitespace."""
    payload = prefix + build_isa_segment()[len(prefix) :]

    with pytest.raises(
        X12EnvelopeError,
        match="must begin with an ISA",
    ):
        derive_x12_separators(payload)


@pytest.mark.parametrize(
    "separator_index",
    ISA_ELEMENT_SEPARATOR_INDICES,
)
def test_derive_separators_validates_every_fixed_width_separator_position(
    separator_index: int,
) -> None:
    """Every fixed-width ISA element separator should be validated."""
    payload = bytearray(build_isa_segment())
    payload[separator_index] = ord("|")

    with pytest.raises(
        X12EnvelopeError,
        match="required fixed-width layout",
    ):
        derive_x12_separators(bytes(payload))


def test_fixed_width_error_identifies_failing_offset() -> None:
    """A fixed-width-layout error should identify the failing byte offset."""
    payload = bytearray(build_isa_segment())
    failing_index = ISA_ELEMENT_SEPARATOR_INDICES[1]
    payload[failing_index] = ord("|")

    with pytest.raises(X12EnvelopeError) as exc_info:
        derive_x12_separators(bytes(payload))

    assert f"offset {failing_index}" in str(exc_info.value)


def test_derive_separators_allows_element_separator_to_change_consistently() -> None:
    """A custom element separator should work when used consistently."""
    separators = derive_x12_separators(
        build_isa_segment(
            element=b"|",
        )
    )

    assert separators.element == b"|"


@pytest.mark.parametrize(
    "invalid_version",
    [
        b"ABCDE",
        b"00A05",
        b"7.05 ",
        b"     ",
        b"+0705",
        b"-0705",
    ],
)
def test_derive_separators_rejects_non_numeric_isa_version(
    invalid_version: bytes,
) -> None:
    """ISA12 should contain five ASCII decimal digits."""
    payload = build_isa_segment(version=invalid_version)

    with pytest.raises(
        X12EnvelopeError,
        match="invalid interchange version",
    ):
        derive_x12_separators(payload)


def test_invalid_version_error_includes_raw_value() -> None:
    """Invalid-version errors should include the original ISA12 bytes."""
    payload = build_isa_segment(version=b"BAD!!")

    with pytest.raises(X12EnvelopeError) as exc_info:
        derive_x12_separators(payload)

    assert "b'BAD!!'" in str(exc_info.value)


def test_derive_separators_rejects_component_matching_element() -> None:
    """Derived component and element separators must differ."""
    payload = build_isa_segment(
        component=b"*",
    )

    with pytest.raises(
        X12SeparatorError,
        match="Element, component, and segment separators must be distinct",
    ):
        derive_x12_separators(payload)


def test_derive_separators_rejects_segment_matching_element() -> None:
    """Derived segment and element separators must differ."""
    payload = build_isa_segment(
        terminator=b"*",
    )

    with pytest.raises(
        X12SeparatorError,
        match="Element, component, and segment separators must be distinct",
    ):
        derive_x12_separators(payload)


def test_derive_separators_rejects_segment_matching_component() -> None:
    """Derived segment and component separators must differ."""
    payload = build_isa_segment(
        component=b":",
        terminator=b":",
    )

    with pytest.raises(
        X12SeparatorError,
        match="Element, component, and segment separators must be distinct",
    ):
        derive_x12_separators(payload)


@pytest.mark.parametrize(
    "repetition",
    [
        b"*",
        b":",
        b"~",
    ],
)
def test_modern_isa_rejects_repetition_matching_another_separator(
    repetition: bytes,
) -> None:
    """Modern ISA repetition separators must be distinct."""
    with pytest.raises(
        X12SeparatorError,
        match="Repetition separator must be distinct",
    ):
        derive_x12_separators(
            build_isa_segment(
                version=b"00705",
                repetition=repetition,
            )
        )


def test_legacy_isa_allows_isa11_to_match_other_separator() -> None:
    """Legacy ISA11 may overlap because it is not a repetition separator."""
    separators = derive_x12_separators(
        build_isa_segment(
            version=b"00401",
            repetition=b"*",
        )
    )

    assert separators.repetition is None


def test_derive_separators_returns_new_value_object_each_time() -> None:
    """Repeated discovery should return equal, independent value objects."""
    payload = build_isa_segment()

    first = derive_x12_separators(payload)
    second = derive_x12_separators(payload)

    assert first == second
    assert first is not second
