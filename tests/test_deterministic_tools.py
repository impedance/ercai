import os
import sys

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
)

from deterministic_tools import parse_structured_data


def test_parse_json_object():
    response = parse_structured_data('{"foo": "bar"}', fmt="json")
    assert response.parsed == [{"foo": "bar"}]
    assert response.warnings == []


def test_parse_csv_with_header():
    csv_text = "name,price\napple,10\nbanana,20"
    response = parse_structured_data(csv_text, fmt="csv")
    assert response.parsed[0]["name"] == "apple"
    assert response.parsed[1]["price"] == "20"
    assert not response.warnings


def test_parse_with_schema_warning():
    csv_text = "name,price\napple,\n"
    response = parse_structured_data(csv_text, fmt="csv", schema=["name", "price"])
    assert "missing fields" in response.warnings[0]


def test_parse_lines_format_defaults():
    response = parse_structured_data("alpha\nbeta", fmt="lines")
    assert response.parsed[0]["line"] == "alpha"
    assert response.parsed[1]["line"] == "beta"


def test_parse_lines_with_column_names_yields_objects():
    response = parse_structured_data(
        "alpha|beta",
        fmt="lines",
        delimiter="|",
        column_names=["value"],
    )
    assert response.parsed[0]["value"] == "alpha"
    assert response.parsed[1]["value"] == "beta"


def test_parse_json_schema_warning_for_missing_fields():
    response = parse_structured_data('{"name":"apple"}', fmt="json", schema=["name", "price"])
    assert any("missing fields" in warning for warning in response.warnings)


def run_all_tests():
    test_parse_json_object()
    test_parse_csv_with_header()
    test_parse_with_schema_warning()
    test_parse_lines_format_defaults()


if __name__ == "__main__":
    run_all_tests()
