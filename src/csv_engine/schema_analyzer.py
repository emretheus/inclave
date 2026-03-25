import pandas as pd
from pathlib import Path
from dataclasses import dataclass, field
import json
import csv
import re
import hashlib


@dataclass
class ColumnInfo:
    name: str
    dtype: str
    null_pct: float
    unique_count: int
    sample_values: list
    # Sadece sayısal sütunlar için
    min_val: float | None = None
    max_val: float | None = None
    mean_val: float | None = None
    # Tip önerisi (Yapay zekaya yön göstermek için)
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
        """Şemayı, LLM promptuna (yapay zekaya) enjekte edilecek bir metin formatına çevirir."""
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

    def get_fingerprint(self) -> str:
        """
        Bu CSV'nin sütun isimlerini ve tiplerini alıp şifreler (hash).
        Böylece benzer soruların yanlış dosyalarda çalışması engellenir.
        """
        schema_string = "|".join(f"{col.name}:{col.dtype}" for col in self.column_info)
        return hashlib.md5(schema_string.encode()).hexdigest()[:12]

class SchemaAnalyzer:
    """Bir CSV dosyasını analiz eder ve yapılandırılmış şema bilgisini çıkarır."""

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

            # Sayısal istatistikler
            if pd.api.types.is_numeric_dtype(col):
                col_info.min_val = float(col.min()) if not col.isna().all() else None
                col_info.max_val = float(col.max()) if not col.isna().all() else None
                col_info.mean_val = float(col.mean()) if not col.isna().all() else None

            # Tip önerileri (object veya string olma durumunu Pandas API ile kontrol ediyoruz)
            if pd.api.types.is_object_dtype(col) or pd.api.types.is_string_dtype(col):
                suggestion = self._suggest_type(col)
                if suggestion:
                    col_info.suggested_type = suggestion
                    issues.append(f"Column '{col_name}' is string but looks like {suggestion}")

            # Boş veri (Null) uyarısı
            if 0 < null_pct <= 50:
                issues.append(f"Column '{col_name}' has {null_pct:.1f}% null values")
            elif null_pct > 50:
                issues.append(f"Column '{col_name}' has {null_pct:.1f}% null values — consider dropping")

            columns.append(col_info)

        # Tekrar eden (Duplicate) satır kontrolü
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
        """Önce utf-8 dener, başarısız olursa diğerlerine geçer."""
        for enc in ["utf-8", "latin-1", "cp1252"]:
            try:
                with open(path, encoding=enc) as f:
                    f.read(1024)
                return enc
            except (UnicodeDecodeError, Exception):
                continue
        return "utf-8"

    def _detect_delimiter(self, path: Path, encoding: str) -> str:
        """İlk satırı kontrol ederek ayracı (delimiter) tespit eder."""
        with open(path, encoding=encoding) as f:
            sample = f.read(4096)
            sniffer = csv.Sniffer()
            try:
                dialect = sniffer.sniff(sample)
                return dialect.delimiter
            except csv.Error:
                return ","

    def _suggest_type(self, col: pd.Series) -> str | None:
        """String bir sütunun aslında tarih veya sayı olup olmadığını kontrol eder (Kirli veri dahil)."""
        sample = col.dropna().head(20)
        if len(sample) == 0:
            return None

        # 1. Tarih kontrolü
        try:
            pd.to_datetime(sample, errors='coerce', format='mixed')
            return "datetime"
        except (ValueError, TypeError):
            pass

        # 2. Temiz sayı kontrolü
        try:
            pd.to_numeric(sample)
            return "numeric"
        except (ValueError, TypeError):
            pass

        # 3. Akıllı ve Katı Kirli Sayı Kontrolü (Para, Yüzde, Birim)
        # Sadece ve sadece TEK BİR sayı bloğu içerenleri yakala
        pattern = r'^[^\d]*(-?\d+(?:[.,]\d+)*)[^\d]*$'
        extracted = sample.astype(str).str.extract(pattern)
        
        # KURAL 1: Örneklerin tümü bu desene uymalı.
        # Eğer bir tane bile "12. Cadde No 5" (iki sayılık) veya "Sadece Metin" varsa, reddet!
        if extracted[0].isna().any():
            return None 
            
        # KURAL 2: Geriye kalan sembol/birim çok uzun olmamalı
        # Sayıları ve noktaları silip geriye kalan "birim" kısmının uzunluğuna bakıyoruz
        text_only = sample.astype(str).str.replace(r'[\d.,-]', '', regex=True).str.strip()
        
        # Eğer kalan metinlerin (harflerin) ortalama uzunluğu 5 karakterden büyükse,
        # bu muhtemelen bir adres veya normal cümledir, birim değildir.
        if text_only.str.len().mean() > 5:
            return None
            
        try:
            # Artık güvendeyiz, virgülleri (binlik ayraç) temizleyip sayıları test edebiliriz
            test_numbers = extracted[0].str.replace(',', '')
            pd.to_numeric(test_numbers)
            return "numeric (needs string cleaning/parsing)"
        except (ValueError, TypeError):
            pass

        return None