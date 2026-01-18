"""
TablePick - output.py

このモジュールは「converter.py が生成したテーブルを stdout / ファイルへ出力する」責務のみを持つ。

- 入力: List[TableData]（converter.convert の返り値）
- 出力:
  - 標準出力（stdout）
  - ファイル（テーブルごとに分割保存）

方針:
- 変換（CSV/JSON文字列化）は converter 側の責務。output は writer（出力）に徹する。
- デフォルトは「stdoutに出す」。out_dir 指定時はファイルにも保存でき、stdout併用も可能。
- 文字コードは UTF-8、改行は \n に統一して書き込む。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal, Optional

from .converter import HtmlTableConverter, TableData

# TablePick の例外は tablepick/error.py に集約される想定
# converter.py も tablepick.error を参照しているため同じ流儀に寄せる。
try:
    from tablepick.error import TablePickError
except Exception:  # pragma: no cover
    class TablePickError(Exception):
        pass


OutputFormat = Literal["csv", "json"]


@dataclass(frozen=True)
class OutputOptions:
    """
    出力オプション（CLI args から組み立てる想定）

    fmt:
      - "csv" or "json"

    out_dir:
      - None の場合はファイル保存しない（stdoutのみ想定）
      - 指定した場合はテーブルごとに分割して保存する

    base_name:
      - 出力ファイルのベース名（例: "wikipedia" -> wikipedia_table01.csv）

    stdout:
      - True の場合は stdout にも出力する（out_dir と併用可）

    ensure_ascii / indent:
      - JSON出力オプション（fmt="json" のときのみ有効）
    """
    fmt: OutputFormat = "csv"
    out_dir: Optional[str] = None
    base_name: str = "tablepick"
    stdout: bool = True
    ensure_ascii: bool = False
    indent: Optional[int] = None


class TableOutputWriter:
    """
    TableData の配列を stdout / ファイルへ出力する writer。
    """

    def __init__(self, *, converter: Optional[HtmlTableConverter] = None) -> None:
        self.converter = converter or HtmlTableConverter()

    def emit(self, tables: Iterable[TableData], opt: OutputOptions) -> list[Path]:
        """
        tables を opt に従って出力する。

        Returns:
            書き込んだファイルの Path リスト（stdout のみの場合は空）
        """
        tables_list = list(tables)
        if not tables_list:
            # converter 側では NoTableFoundError を投げる設計だが、
            # writer単体利用の保険としてここでも弾く。
            raise TablePickError("No tables to output.")

        fmt = self._normalize_format(opt.fmt)
        base = self._sanitize_stem(opt.base_name)

        written: list[Path] = []

        # (1) stdout 出力
        if opt.stdout:
            self._print_to_stdout(tables_list, fmt, opt)

        # (2) ファイル出力（テーブルごとに分割）
        if opt.out_dir is not None:
            out_dir = Path(opt.out_dir)
            out_dir.mkdir(parents=True, exist_ok=True)

            for idx, table in enumerate(tables_list, start=1):
                filename = f"{base}_table{idx:02d}.{fmt}"
                path = out_dir / filename
                payload = self._serialize(table, fmt, opt)
                self._write_text(path, payload)
                written.append(path)

        return written

    # ----------------------------
    # internal helpers
    # ----------------------------
    def _normalize_format(self, fmt: str) -> OutputFormat:
        f = (fmt or "").strip().lower()
        if f in ("csv", "json"):
            return f  # type: ignore[return-value]
        raise TablePickError(
            f"Unsupported output format: {fmt!r} (expected 'csv' or 'json')."
        )

    def _serialize(self, table: TableData, fmt: OutputFormat, opt: OutputOptions) -> str:
        if fmt == "csv":
            return self.converter.to_csv(table)
        # json
        return self.converter.to_json(
            table,
            ensure_ascii=opt.ensure_ascii,
            indent=opt.indent,
        )

    def _print_to_stdout(self, tables: list[TableData], fmt: OutputFormat, opt: OutputOptions) -> None:
        # 複数テーブルでも判別できるよう区切りを入れる
        for idx, table in enumerate(tables, start=1):
            print(f"===== table {idx:02d} ({fmt}) =====")
            print(self._serialize(table, fmt, opt))
            if idx != len(tables):
                print()

    def _write_text(self, path: Path, text: str) -> None:
        # 改行は \n に統一。末尾に改行が無ければ付ける（CLIで扱いやすくする）
        if not text.endswith("\n"):
            text += "\n"
        path.write_text(text, encoding="utf-8", newline="\n")

    def _sanitize_stem(self, s: str) -> str:
        """
        ファイル名として安全な stem を作る。
        - 空文字/ドットのみ等を避ける
        - OSに依存しやすい記号を '_' に寄せる
        """
        s = (s or "").strip()
        if not s:
            return "tablepick"

        # Windows/Unix で危険な文字を置換
        s = re.sub(r'[<>:"/\\\\|?*]+', "_", s)

        # 空白は '_' に寄せる
        s = re.sub(r"\s+", "_", s)

        # Windows対策: 先頭末尾のドット/スペースは避ける
        s = s.strip(" .")

        # 連続 '_' を潰す
        s = re.sub(r"_+", "_", s)

        return s or "tablepick"


def output_tables(
    tables: Iterable[TableData],
    *,
    fmt: OutputFormat = "csv",
    out_dir: Optional[str] = None,
    base_name: str = "tablepick",
    stdout: bool = True,
    ensure_ascii: bool = False,
    indent: Optional[int] = None,
) -> list[Path]:
    """
    converter.convert() の返り値をそのまま渡して出力できるヘルパ。

    Returns:
        書き込んだファイルの Path リスト（stdout のみの場合は空）
    """
    writer = TableOutputWriter()
    opt = OutputOptions(
        fmt=fmt,
        out_dir=out_dir,
        base_name=base_name,
        stdout=stdout,
        ensure_ascii=ensure_ascii,
        indent=indent,
    )
    return writer.emit(tables, opt)
