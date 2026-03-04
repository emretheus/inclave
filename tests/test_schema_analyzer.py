import pytest
from src.csv_engine.schema_analyzer import SchemaAnalyzer


@pytest.fixture
def analyzer():
    return SchemaAnalyzer()


def test_basic_analysis(analyzer):
    schema = analyzer.analyze("data/sample_csvs/sales_data.csv")
    assert schema.rows == 11
    assert schema.columns == 8
    assert schema.delimiter == ","


def test_detects_datetime_suggestion(analyzer):
    schema = analyzer.analyze("data/sample_csvs/sales_data.csv")
    date_col = next(c for c in schema.column_info if c.name == "date")
    assert date_col.suggested_type == "datetime"


def test_detects_nulls(analyzer):
    schema = analyzer.analyze("data/sample_csvs/sales_data.csv")
    discount_col = next(c for c in schema.column_info if c.name == "discount")
    assert discount_col.null_pct > 0


def test_detects_duplicates(analyzer):
    schema = analyzer.analyze("data/sample_csvs/sales_data.csv")
    assert any("duplicate" in issue.lower() for issue in schema.potential_issues)


def test_prompt_string_not_empty(analyzer):
    schema = analyzer.analyze("data/sample_csvs/sales_data.csv")
    prompt_str = schema.to_prompt_string()
    assert len(prompt_str) > 100
    assert "sales_data.csv" in prompt_str
