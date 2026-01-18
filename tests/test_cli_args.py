import argparse

import pytest

from cli import args as cli_args


# 何をしているか: 正常なHTTPS URLを厳格バリデーションに通す。
# 何を確認しているか: 正しいURLがそのまま受理されるか。
# テスト結果の期待値: 入力と同じURL文字列が返る。
# テストコードの実行方法: pytest tests/test_cli_args.py
def test_validate_url_strict_accepts_https() -> None:
    assert cli_args._validate_url_strict("https://example.com") == "https://example.com"


# 何をしているか: scheme無しURLを厳格バリデーションに通す。
# 何を確認しているか: 不正URLがエラーとして扱われるか。
# テスト結果の期待値: argparse.ArgumentTypeError が送出される。
# テストコードの実行方法: pytest tests/test_cli_args.py
def test_validate_url_strict_rejects_missing_scheme() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        cli_args._validate_url_strict("example.com")


# 何をしているか: CLI引数から出力オプションを組み立てる。
# 何を確認しているか: format/filename/stdout/jsonオプションが正しく反映されるか。
# テスト結果の期待値: OutputOptions に指定値がそのままセットされる。
# テストコードの実行方法: pytest tests/test_cli_args.py
def test_make_output_options_from_args() -> None:
    ns = cli_args.parse_args(
        [
            "--url",
            "https://example.com",
            "--format",
            "json",
            "--filename-base",
            "base",
            "--no-stdout",
            "--json-indent",
            "2",
            "--ensure-ascii",
        ]
    )
    opt = cli_args.make_output_options(ns)
    assert opt.fmt == "json"
    assert opt.base_name == "base"
    assert opt.stdout is False
    assert opt.indent == 2
    assert opt.ensure_ascii is True
