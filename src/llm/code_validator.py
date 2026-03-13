import logging

logger = logging.getLogger(__name__)


class CodeValidator:
    """
    Validates and auto-fixes generated Python code.
    Responsibilities:
    - Detect and fix missing imports
    - Can be extended with more validation rules in Phase 2
    """

    # Map of usage pattern → import line
    IMPORT_FIXES = {
        # Data manipulation
        "pd.":              "import pandas as pd",
        "np.":              "import numpy as np",
        # Visualization
        "plt.":             "import matplotlib.pyplot as plt",
        "sns.":             "import seaborn as sns",
        "px.":              "import plotly.express as px",
        "go.":              "import plotly.graph_objects as go",
        # Machine learning
        "sklearn.":         "from sklearn import *",
        "tf.":              "import tensorflow as tf",
        "torch.":           "import torch",
        # Statistics
        "stats.":           "from scipy import stats",
        "scipy.":           "import scipy",
        # File handling
        "json.":            "import json",
        "os.":              "import os",
        "sys.":             "import sys",
        "Path(":            "from pathlib import Path",
        # Date handling
        "datetime.":        "import datetime",
        "timedelta(":       "from datetime import timedelta",
        # Other common
        "re.":              "import re",
        "math.":            "import math",
        "random.":          "import random",
        "collections.":     "import collections",
        "itertools.":       "import itertools",
        "functools.":       "import functools",
        "typing.":          "from typing import *",
        "dataclass":        "from dataclasses import dataclass",
        "defaultdict(":     "from collections import defaultdict",
        "Counter(":         "from collections import Counter",
        "openpyxl":         "import openpyxl",
    }

    @staticmethod
    def fix_missing_imports(code: str) -> str:
        """
        Scan generated code for common library usage patterns.
        If a library is used but not imported, auto-add the import at the top.
        """
        added_imports = []

        for usage_pattern, import_line in CodeValidator.IMPORT_FIXES.items():
            if usage_pattern in code:
                if import_line not in code:
                    added_imports.append(import_line)

        if added_imports:
            # Remove duplicates while preserving order
            added_imports = list(dict.fromkeys(added_imports))
            imports_block = "\n".join(added_imports)
            code = imports_block + "\n" + code
            for imp in added_imports:
                logger.warning(f"Auto-fixed missing import: {imp}")

        return code

    @staticmethod
    def is_valid_syntax(code: str) -> bool:
        """Check if the generated code is valid Python syntax."""
        try:
            compile(code, "<string>", "exec")
            return True
        except SyntaxError as e:
            logger.error(f"Syntax error in generated code: {e}")
            return False

    @staticmethod
    def validate(code: str) -> tuple[str, list[str]]:
        """
        Run all validations on generated code.
        Returns: (fixed_code, list of warnings)
        """
        warnings = []

        # Fix missing imports
        fixed_code = CodeValidator.fix_missing_imports(code)
        if fixed_code != code:
            warnings.append("Auto-fixed missing imports")

        # Check syntax
        if not CodeValidator.is_valid_syntax(fixed_code):
            warnings.append("WARNING: Generated code has syntax errors")

        return fixed_code, warnings