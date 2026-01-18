from pathlib import Path

import pytest

from core.converter import TableData
from core.output import OutputOptions, TableOutputWriter
from tablepick.error import TablePickError


def _make_table() -> TableData:
    return TableData(
        header=["col1"],
        rows=[["value"]],
        records=[{"col1": "value"}],
    )


# 何をしているか: CSV出力をファイルに書き出す処理を実行する。
# 何を確認しているか: base_name の空白が安全なファイル名に変換されるか、書き込みが成功するか。
# テスト結果の期待値: "my_table_table01.csv" が作成され、内容が "col1\nvalue\n" になる。
# テストコードの実行方法: pytest tests/test_output.py
def test_emit_writes_files_and_sanitizes_base_name(tmp_path: Path) -> None:
    writer = TableOutputWriter()
    opt = OutputOptions(
        fmt="csv",
        out_dir=str(tmp_path),
        base_name="my table",
        stdout=False,
    )

    written = writer.emit([_make_table()], opt)
    assert len(written) == 1

    out_path = tmp_path / "my_table_table01.csv"
    assert written[0] == out_path
    assert out_path.exists()
    assert out_path.read_text(encoding="utf-8") == "col1\nvalue\n"


# 何をしているか: 未対応フォーマットで出力を試みる。
# 何を確認しているか: サポート外フォーマットが例外として扱われるか。
# テスト結果の期待値: TablePickError が送出される。
# テストコードの実行方法: pytest tests/test_output.py
def test_emit_rejects_unsupported_format(tmp_path: Path) -> None:
    writer = TableOutputWriter()
    opt = OutputOptions(
        fmt="md",  # type: ignore[arg-type]
        out_dir=str(tmp_path),
        base_name="base",
        stdout=False,
    )
    with pytest.raises(TablePickError):
        writer.emit([_make_table()], opt)


# 何をしているか: テーブルが空の状態で writer.emit を呼ぶ。
# 何を確認しているか: 出力対象が空のときに例外になるか。
# テスト結果の期待値: TablePickError が送出される。
# テストコードの実行方法: pytest tests/test_output.py
def test_emit_rejects_empty_tables() -> None:
    writer = TableOutputWriter()
    opt = OutputOptions(fmt="csv", stdout=False)
    with pytest.raises(TablePickError):
        writer.emit([], opt)
