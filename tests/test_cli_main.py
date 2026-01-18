from pathlib import Path
import importlib

cli_main = importlib.import_module("tablepick.cli.main")


class _DummyResponse:
    def __init__(self, url: str) -> None:
        self.url = url
        self.headers = {"Content-Type": "text/html"}
        self.status_code = 200


class _DummyFetcher:
    def __init__(self, config, headers=None) -> None:
        self.config = config
        self.headers = headers

    def fetch(self, url: str):
        html = """
        <table>
          <tr><th>H</th></tr>
          <tr><td>V</td></tr>
        </table>
        """
        return html, url, _DummyResponse(url)


# 何をしているか: ダミーFetcherでCLIメインを実行し、出力ファイル生成まで流す。
# 何を確認しているか: 正常系で exit code が 0 になり、CSVファイルが作られるか。
# テスト結果の期待値: code == 0、"base_table01.csv" が存在し内容が "H\nV\n"。
# テストコードの実行方法: pytest tests/test_cli_main.py
def test_main_happy_path_writes_output(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(cli_main, "HtmlFetcher", _DummyFetcher)

    out_dir = tmp_path / "out"
    argv = [
        "--url",
        "https://example.com",
        "--format",
        "csv",
        "--out-dir",
        str(out_dir),
        "--filename-base",
        "base",
        "--no-stdout",
    ]

    code = cli_main.main(argv)
    assert code == 0

    out_path = out_dir / "base_table01.csv"
    assert out_path.exists()
    assert out_path.read_text(encoding="utf-8") == "H\nV\n"
