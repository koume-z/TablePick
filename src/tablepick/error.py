"""
TablePick - error.py

TablePick 全体で使用する例外クラスを集約するモジュール。

現状の既存コードとの整合:
- core/converter.py は NoTableFoundError / TableConversionError を import して raise する。
- core/output.py は TablePickError を import して raise している（現状は汎用）。
  将来的に OutputError / UnsupportedFormatError / NoTablesToOutputError に差し替え可能。

方針:
- 今すぐ使われている例外クラス（TablePickError / NoTableFoundError / TableConversionError）を確実に提供する。
- “概念として既に存在する” もの（Unsupported format / No tables to output）は、
  将来の置き換え先として例外クラスを先に定義しておく（互換性を壊さない拡張）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ============================================================
# Base
# ============================================================

class TablePickError(Exception):
    """TablePick 固有の基底例外（想定内エラーの受け皿）。"""
    pass


# ============================================================
# Conversion / Parsing
# ============================================================

class NoTableFoundError(TablePickError):
    """HTML 内に <table> が見つからない場合の例外。"""
    pass


class TableConversionError(TablePickError):
    """<table> は存在するが TableData へ変換できない場合の例外。"""
    pass


# ============================================================
# Fetch / Network (reserved for future wrapping)
# ============================================================

@dataclass(eq=False)
class FetchError(TablePickError):
    """
    HTML 取得失敗を TablePick の例外体系に統一するための例外（予約枠）。

    現状 core/get_html.py は requests の例外をそのまま送出しているため、
    本例外は未使用でも問題ない（互換性を壊さない拡張）。
    """
    url: Optional[str] = None
    reason: Optional[str] = None
    status_code: Optional[int] = None

    def __str__(self) -> str:
        parts: list[str] = []
        if self.url:
            parts.append(f"url={self.url}")
        if self.status_code is not None:
            parts.append(f"status={self.status_code}")
        if self.reason:
            parts.append(self.reason)
        return "FetchError" + (f" ({', '.join(parts)})" if parts else "")


# ============================================================
# Output (reserved for future specialization)
# ============================================================

class OutputError(TablePickError):
    """出力に関する例外の上位カテゴリ（予約枠）。"""
    pass


class UnsupportedFormatError(OutputError):
    """サポートされない出力フォーマット指定（例: fmt='md'）。"""
    pass


class NoTablesToOutputError(OutputError):
    """出力対象のテーブルが 0 件なのに出力を要求された場合の例外。"""
    pass
