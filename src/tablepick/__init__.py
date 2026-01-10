"""
tablepick package

公開方針:
- 例外クラスは tablepick.error に集約しており、ここからも再exportする。
- 実処理（変換・取得・出力）は core/cli にあり、ここでは公開APIを最小に保つ。
"""

from __future__ import annotations

# Version
__all__ = [
    "__version__",
    # errors (re-export)
    "TablePickError",
    "NoTableFoundError",
    "TableConversionError",
    "FetchError",
    "OutputError",
    "UnsupportedFormatError",
    "NoTablesToOutputError",
]

__version__ = "0.1.0"

# Re-export errors for convenient import: `from tablepick import TablePickError`
from .error import (  # noqa: E402
    FetchError,
    NoTableFoundError,
    NoTablesToOutputError,
    OutputError,
    TableConversionError,
    TablePickError,
    UnsupportedFormatError,
)
