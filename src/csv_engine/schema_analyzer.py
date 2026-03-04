"""
CSV Schema Analyzer.
Takes a CSV file and produces structured schema info for LLM prompt injection.
"""
import pandas as pd
from pathlib import Path
from dataclasses import dataclass, field
import csv as csv_module


@dataclass
class ColumnInfo:
    name: str
    dtype: str
    null_pct: float
    unique_count: int
    sample_values: list
    # Numeric columns only
    min_val: float | None = None
    max_val: float | None = None
    mean_val: float | None = None
    # Type suggestion
    suggested_type: str | None = None


@dataclass
class CSVSchema:
    filename: str
    rows: int
    columns: int
    encoding: str
    delimiter: str
    column_info: list[ColumnInfo]
    potential_issues: list[str] = field(default_factory=list)

    def to_prompt_string(self) -> str:
        """Format schema as a string for LLM prompt injection."""
        lines = [
            f"File: {self.filename} ({self.rows:,} rows, {self.columns} columns)",
            f"Encoding: {self.encoding}, Delimiter: '{self.delimiter}'",
            "",
            "Columns:",
        ]
        for col in self.column_info:
            parts = [f"  - {col.name} ({col.dtype}"]
            if col.suggested_type:
                parts[0] += f" → {col.suggested_type} recommended"
            parts[0] += f", null: {col.null_pct:.1f}%"
            parts[0] += f", {col.unique_count} unique"
            if col.min_val is not None:
                parts[0] += f", range: {col.min_val}-{col.max_val}, mean: {col.mean_val:.1f}"
            parts[0] += ")"
            samples = ", ".join(str(v) for v in col.sample_values[:3])
            parts.append(f"    examples: [{samples}]")
            lines.extend(parts)

        if self.potential_issues:
            lines.append("")
            lines.append("Potential issues:")
            for issue in self.potential_issues:
                lines.append(f"  ⚠ {issue}")

        return "\n".join(lines)


class SchemaAnalyzer:
    """Analyzes a CSV file and extracts structured schema information."""

    def analyze(self, file_path: str | Path, sample_rows: int = 5) -> CSVSchema:
        path = Path(file_path)
        encoding = self._detect_encoding(path)
        delimiter = self._detect_delimiter(path, encoding)

        df = pd.read_csv(path, encoding=encoding, delimiter=delimiter)

        columns = []
        issues = []

        for col_name in df.columns:
            col = df[col_name]
            null_pct = (col.isna().sum() / len(df)) * 100
            unique_count = col.nunique()
            sample_vals = col.dropna().head(sample_rows).tolist()

            col_info = ColumnInfo(
                name=col_name,
                dtype=str(col.dtype),
                null_pct=round(null_pct, 1),
                unique_count=unique_count,
                sample_values=sample_vals,
            )

            # Numeric stats
            if pd.api.types.is_numeric_dtype(col):
                col_info.min_val = float(col.min()) if not col.isna().all() else None
                col_info.max_val = float(col.max()) if not col.isna().all() else None
                col_info.mean_val = float(col.mean()) if not col.isna().all() else None

            # Type suggestions
            if col.dtype == "object":
                suggestion = self._suggest_type(col)
                if suggestion:
                    col_info.suggested_type = suggestion
                    issues.append(f"Column '{col_name}' is string but looks like {suggestion}")

            # Null warning
            if 0 < null_pct <= 50:
                issues.append(f"Column '{col_name}' has {null_pct:.1f}% null values")
            elif null_pct > 50:
                issues.append(f"Column '{col_name}' has {null_pct:.1f}% null values — consider dropping")

            columns.append(col_info)

        # Duplicate check
        dup_count = df.duplicated().sum()
        if dup_count > 0:
            issues.append(f"{dup_count} duplicate rows found")

        return CSVSchema(
            filename=path.name,
            rows=len(df),
            columns=len(df.columns),
            encoding=encoding,
            delimiter=delimiter,
            column_info=columns,
            potential_issues=issues,
        )

    def _detect_encoding(self, path: Path) -> str:
        """Try utf-8 first, fall back to latin-1."""
        for enc in ["utf-8", "latin-1", "cp1252"]:
            try:
                with open(path, encoding=enc) as f:
                    f.read(1024)
                return enc
            except (UnicodeDecodeError, Exception):
                continue
        return "utf-8"

    def _detect_delimiter(self, path: Path, encoding: str) -> str:
        """Detect delimiter by checking first line."""
        with open(path, encoding=encoding) as f:
            sample = f.read(4096)
            sniffer = csv_module.Sniffer()
            try:
                dialect = sniffer.sniff(sample)
                return dialect.delimiter
            except csv_module.Error:
                return ","

    def _suggest_type(self, col: pd.Series) -> str | None:
        """Check if a string column might actually be datetime or numeric."""
        sample = col.dropna().head(20)
        if len(sample) == 0:
            return None

        # Try datetime
        try:
            pd.to_datetime(sample)
            return "datetime"
        except (ValueError, TypeError):
            pass

        # Try numeric
        try:
            pd.to_numeric(sample)
            return "numeric"
        except (ValueError, TypeError):
            pass

        return None
