import pytest

from tablepick.core.converter import HtmlTableConverter, TableData
from tablepick.error import NoTableFoundError


# 何をしているか: テーブルが存在しないHTMLを変換する。
# 何を確認しているか: テーブル未検出時に適切な例外が発生するか。
# テスト結果の期待値: NoTableFoundError が送出される。
# テストコードの実行方法: pytest tests/test_converter.py
def test_convert_raises_when_no_table() -> None:
    html = "<html><body><p>No tables here.</p></body></html>"
    with pytest.raises(NoTableFoundError):
        HtmlTableConverter().convert(html)


# 何をしているか: 複数行ヘッダーのテーブルを変換する。
# 何を確認しているか: ヘッダーが行方向に結合され、空セルは補完されるか。
# テスト結果の期待値: ヘッダーが ["Top_Sub1", "Sub2"] になり、行が正しく抽出される。
# テストコードの実行方法: pytest tests/test_converter.py
def test_convert_multi_header_merges_columns() -> None:
    html = """
    <table>
      <tr><th>Top</th><th></th></tr>
      <tr><th>Sub1</th><th>Sub2</th></tr>
      <tr><td>A</td><td>B</td></tr>
    </table>
    """
    tables = HtmlTableConverter().convert(html)
    assert len(tables) == 1
    assert tables[0].header == ["Top_Sub1", "Sub2"]
    assert tables[0].rows == [["A", "B"]]


# 何をしているか: ヘッダー無しのテーブルを変換する。
# 何を確認しているか: デフォルトの列名と列数補完が適用されるか。
# テスト結果の期待値: ヘッダーが ["col1", "col2"]、不足列が空文字で埋まる。
# テストコードの実行方法: pytest tests/test_converter.py
def test_convert_no_header_defaults_to_col_names() -> None:
    html = """
    <table>
      <tr><td>A</td><td>B</td></tr>
      <tr><td>C</td></tr>
    </table>
    """
    table = HtmlTableConverter().convert(html)[0]
    assert table.header == ["col1", "col2"]
    assert table.rows == [["A", "B"], ["C", ""]]


# 何をしているか: セル内の脚注・リンク・改行を含むHTMLを変換する。
# 何を確認しているか: sup削除、aのunwrap、注釈削除、brの空白化が効くか。
# テスト結果の期待値: セル値が "Alpha Link Beta" になる。
# テストコードの実行方法: pytest tests/test_converter.py
def test_clean_cell_text_removes_notes_and_links() -> None:
    html = """
    <table>
      <tr><th>H1</th></tr>
      <tr><td>Alpha<sup>1</sup> <a href="#">Link</a>[2]<br>Beta</td></tr>
    </table>
    """
    table = HtmlTableConverter().convert(html)[0]
    assert table.rows == [["Alpha Link Beta"]]


# 何をしているか: CSVエスケープが必要な値を含む TableData をCSV化する。
# 何を確認しているか: カンマとダブルクォートがCSV仕様通りにエスケープされるか。
# テスト結果の期待値: "a,b" はクォートされ、"q" は ""q"" になる。
# テストコードの実行方法: pytest tests/test_converter.py
def test_to_csv_escapes_commas_and_quotes() -> None:
    table = TableData(
        header=["h"],
        rows=[["a,b"], ['"q"']],
        records=[{"h": "a,b"}, {"h": '"q"'}],
    )
    csv_text = HtmlTableConverter().to_csv(table)
    lines = csv_text.splitlines()
    assert lines[0] == "h"
    assert lines[1] == '"a,b"'
    assert lines[2] == '"""q"""'
