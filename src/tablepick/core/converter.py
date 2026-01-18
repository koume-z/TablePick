"""
TablePick - converter.py

このモジュールは「取得したHTML内の <table> を抽出し、CSV/JSON 用のデータ構造へ変換する」責務のみを持つ。
- 入力: HTML文字列
- 出力: 変換済みデータ（Pythonの list/dict / CSV文字列 / JSON文字列）
- ファイル保存は行わない（保存は output.py の責務）

要件（会話で確定した方針）
- <table> はすべて対象（ページ内の全テーブルを変換）
- 複数テーブルは全て変換し、出力は「テーブルごとにファイル分割」（= 返り値をテーブル単位で返す）
- テーブル名（見出しh2/h3）は扱わない。テーブルデータだけを扱う
- rowspan/colspan は考慮しない（= 構造保持しない）。列数は「最長列に合わせて空文字で埋める」
- ヘッダーが多段なら「同じ列位置のヘッダ文字を '_' で連結」
- JSONは A形式（行オブジェクト配列）: [ {col1:..., col2:...}, ... ]
- ヘッダーが無いテーブルは col1,col2,... を採用
- 余計な要素の除去:
  - <sup> の脚注番号・注釈は削除
  - <a> はリンクとしては削除（ただし値としてのテキストは保持するため unwrap）
  - 注釈表現 [1] 等は文字列として削除
  - <br> は空白扱い
  - <img> は空欄扱い（imgは削除）
- テーブルが見つからない場合は TablePickError 系の例外を投げる
- “変換不能”は原則作らない（空セルだらけでも、列数が不揃いでも、空文字埋めで続行）
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import List, Optional

from bs4 import BeautifulSoup, Tag

# TablePick の例外は error.py に集約し、意味のある例外型を投げる
# ※ error.py 側で以下のような定義を想定：
#   class TablePickError(Exception): ...
#   class NoTableFoundError(TablePickError): ...
#   class TableConversionError(TablePickError): ...
from tablepick.error import NoTableFoundError, TableConversionError


@dataclass(frozen=True)
class TableData:
    """
    1つのHTMLテーブルを変換した結果を保持する。
    - header: 列名（ヘッダー無しなら col1,col2,...）
    - rows: 2次元配列（文字列のみ、列数は最長列に合わせて空文字で埋める）
    - records: JSON(A形式) 用の行オブジェクト配列
    """
    header: List[str]
    rows: List[List[str]]
    records: List[dict]


class HtmlTableConverter:
    """
    HTML文字列からテーブルを抽出し、CSV/JSONに変換可能なデータ構造へ整形する。
    """

    # 次のメソッド:
    # - HTML文字列から全ての <table> を抽出し、テーブル単位の TableData 配列を返す
    def convert(self, html: str) -> List[TableData]:
        # 要素1: HTMLをパースする
        soup = BeautifulSoup(html, "html.parser")

        # 要素2: 全テーブルを抽出する（<table> はすべて対象）
        tables = soup.find_all("table")

        # 要素3: テーブルが無ければ TablePick 固有例外（上位で exit code を決める）
        if not tables:
            raise NoTableFoundError("No <table> elements found in the provided HTML.")

        # 要素4: 各テーブルを TableData に変換する
        results: List[TableData] = []
        for table in tables:
            results.append(self._convert_single_table(table))

        return results

    # 次のメソッド:
    # - 1つの <table> を header / rows / records に変換する
    def _convert_single_table(self, table: Tag) -> TableData:
        # 要素1: テーブル内の行を抽出する
        tr_list = table.find_all("tr")

        # 要素2: 行ごとにセル配列（文字列）へ変換する
        raw_rows: List[List[str]] = []
        row_is_header: List[bool] = []
        for tr in tr_list:
            # 行内のセルは th/td 両方対象（row header が th の場合があるため）
            cells = tr.find_all(["th", "td"])
            if not cells:
                continue

            # セルをクレンジングして文字列化
            row_values = [self._clean_cell_text(td_or_th) for td_or_th in cells]
            raw_rows.append(row_values)

            # “この行がヘッダー行か”の判定（thが含まれるならヘッダー行）
            row_is_header.append(bool(tr.find_all("th")))

        # 要素3: 変換対象の実データが無い場合は変換失敗として例外
        if not raw_rows:
            raise TableConversionError("A <table> was found but contains no readable rows/cells.")

        # 要素4: 先頭から連続するヘッダー行を切り出す
        header_rows, data_rows = self._split_header_and_body(raw_rows, row_is_header)

        # 要素5: テーブル全体の最長列数を確定する（不足は空文字で埋める）
        max_cols = self._max_columns(header_rows + data_rows)
        if max_cols <= 0:
            # ここは通常到達しないが、保険として TablePick 固有例外
            raise TableConversionError("Failed to determine table column count.")

        # 要素6: ヘッダーを構築（多段ヘッダーは '_' で連結）
        header = self._build_header(header_rows, max_cols)

        # 要素7: データ行を列数 max_cols に揃える（不足は空文字で埋める）
        normalized_rows = [self._pad_row(r, max_cols) for r in data_rows]

        # 要素8: JSON(A形式) の records を作る（ヘッダー無しでも col1.. があるので必ず作れる）
        records = [dict(zip(header, row)) for row in normalized_rows]

        return TableData(header=header, rows=normalized_rows, records=records)

    # 次のメソッド:
    # - ヘッダー行とデータ行を分割する（先頭から連続する th 行をヘッダーとして扱う）
    def _split_header_and_body(
        self,
        rows: List[List[str]],
        row_is_header: List[bool],
    ) -> tuple[List[List[str]], List[List[str]]]:
        # 要素1: 先頭から「ヘッダー行が続く」範囲を探索する
        header_end = 0
        for i, is_header in enumerate(row_is_header):
            if is_header:
                header_end = i + 1
            else:
                break

        # 要素2: 分割する
        header_rows = rows[:header_end]
        data_rows = rows[header_end:]

        # 要素3: データが1行も無い場合でも「空テーブルを許容」する（例外にしない）
        return header_rows, data_rows

    # 次のメソッド:
    # - 複数行ヘッダーを '_' 連結して1行のヘッダー配列を作る
    # - ヘッダー行が無ければ col1,col2,... を採用する
    def _build_header(self, header_rows: List[List[str]], max_cols: int) -> List[str]:
        # 要素1: ヘッダー行が存在しない場合は col1.. を返す
        if not header_rows:
            return [f"col{i}" for i in range(1, max_cols + 1)]

        # 要素2: ヘッダー行も列数を揃えてから連結処理する
        padded_header_rows = [self._pad_row(r, max_cols) for r in header_rows]

        # 要素3: 列ごとに「上から順に非空を '_' 連結」してヘッダー名を作る
        header: List[str] = []
        for col_idx in range(max_cols):
            parts: List[str] = []
            for row in padded_header_rows:
                v = row[col_idx].strip()
                if v:
                    parts.append(v)

            name = "_".join(parts).strip()

            # 要素4: 連結結果が空なら colN を採用（ヘッダーの穴埋め）
            if not name:
                name = f"col{col_idx + 1}"

            header.append(name)

        return header

    # 次のメソッド:
    # - 1セル(<td>/<th>)から文字列を抽出し、不要要素や注釈を除去する
    def _clean_cell_text(self, cell: Tag) -> str:
        # 要素1: 画像は空欄扱い（imgタグは削除）
        for img in cell.find_all("img"):
            img.decompose()

        # 要素2: sup（脚注）を削除
        for sup in cell.find_all("sup"):
            sup.decompose()

        # 要素3: a（リンク）は “リンクとしては削除” だが、値の文字は残したいので unwrap
        for a in cell.find_all("a"):
            a.unwrap()

        # 要素4: br は空白扱い（get_text の separator で空白にする）
        text = cell.get_text(separator=" ", strip=True)

        # 要素5: 典型的な注釈表現を削除（例: [1], [12]）
        text = re.sub(r"\[\s*\d+\s*\]", "", text)

        # 要素6: 空白の正規化（連続空白を1つに）
        text = re.sub(r"\s+", " ", text).strip()

        return text

    # 次のメソッド:
    # - 行の列数を max_cols に揃える（不足は空文字で埋める）
    #   ※最長列に合わせて不足を空文字で埋める（切り捨てなし）
    def _pad_row(self, row: List[str], max_cols: int) -> List[str]:
        # 要素1: 不足分は空文字で埋める
        if len(row) < max_cols:
            return row + [""] * (max_cols - len(row))

        # 要素2: 超過は通常発生しない（max_cols は最長列数）ため、
        #        念のため max_cols に丸める（records の zip を壊さないため）
        if len(row) > max_cols:
            return row[:max_cols]

        return row

    # 次のメソッド:
    # - 複数行の中で最も長い列数を返す（0の場合は0）
    def _max_columns(self, rows: List[List[str]]) -> int:
        # 要素: 空の場合は0
        if not rows:
            return 0
        return max(len(r) for r in rows)

    # 次のメソッド:
    # - TableData をCSV文字列に変換する（ファイル保存はしない）
    def to_csv(self, table: TableData) -> str:
        # 要素1: CSVエスケープ（カンマ/改行/ダブルクォートを含む場合はクォート）
        def escape_csv(value: str) -> str:
            needs_quote = ("," in value) or ("\n" in value) or ('"' in value) or ("\r" in value)
            if '"' in value:
                value = value.replace('"', '""')
            return f'"{value}"' if needs_quote else value

        # 要素2: ヘッダー行
        lines: List[str] = []
        lines.append(",".join(escape_csv(h) for h in table.header))

        # 要素3: データ行
        for row in table.rows:
            lines.append(",".join(escape_csv(v) for v in row))

        # 要素4: 改行で連結（UTF-8固定は output.py が書き込む際に担保）
        return "\n".join(lines)

    # 次のメソッド:
    # - TableData をJSON文字列に変換する（A形式: 行オブジェクト配列）
    def to_json(
        self,
        table: TableData,
        *,
        ensure_ascii: bool = False,
        indent: Optional[int] = None,
    ) -> str:
        # 要素: records をそのまま dumps
        return json.dumps(table.records, ensure_ascii=ensure_ascii, indent=indent)


# 便利関数（クラスを持ち回りたくない用途向け）
# ※必須ではないが、CLI側の記述を短くするために用意している

# 次のメソッド:
# - HTML文字列から全テーブルを抽出し、TableData 配列を返す（ワンショット関数）
def convert_html_tables(html: str) -> List[TableData]:
    return HtmlTableConverter().convert(html)


# 次のメソッド:
# - HTML文字列から全テーブルを抽出し、テーブルごとのCSV文字列配列を返す
def convert_html_to_csv_list(html: str) -> List[str]:
    converter = HtmlTableConverter()
    tables = converter.convert(html)
    return [converter.to_csv(t) for t in tables]


# 次のメソッド:
# - HTML文字列から全テーブルを抽出し、テーブルごとのJSON文字列配列を返す（A形式）
def convert_html_to_json_list(
    html: str,
    *,
    ensure_ascii: bool = False,
    indent: Optional[int] = None,
) -> List[str]:
    converter = HtmlTableConverter()
    tables = converter.convert(html)
    return [converter.to_json(t, ensure_ascii=ensure_ascii, indent=indent) for t in tables]
