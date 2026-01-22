"""
cli/args.py

TablePick CLI の引数定義と、core 側で使う設定オブジェクトの組み立てを担当する。

方針:
- URLは --url で受け取り、scheme（http/https）必須。欠けていればエラーで中断する。
- --format はロングオプションのみ（-f は使わない）。
- --filename-base に名称変更。
- retry_interval は CLI から指定不可。core/__init__.py の FetchConfig デフォルト値を常に採用する。
- --debug は「デバッグ表示用の辞書を生成する」までを args.py で提供し、出力は main.py 側に委譲する。
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from typing import Optional, Sequence, Literal
from urllib.parse import urlparse

from tablepick import __version__
from tablepick.core import FetchConfig
from tablepick.core.output import OutputOptions

OutputFormat = Literal["csv", "json"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tablepick",
        description="Extract all <table> elements from a web page and output as CSV/JSON to stdout or files.",
    )

    # ---- required url (strict) ----
    parser.add_argument(
        "--url",
        required=True,
        type=_validate_url_strict,
        help="Target URL (scheme required: http/https). Example: --url https://example.com",
    )

    # ---- output options ----
    parser.add_argument(
        "--format",
        dest="fmt",
        choices=("csv", "json"),
        default="csv",
        help="Output format. (default: csv)",
    )
    parser.add_argument(
        "--out-dir",
        dest="out_dir",
        default=None,
        help="Directory to write output files. If omitted, files are not written.",
    )
    parser.add_argument(
        "--filename-base",
        dest="filename_base",
        default="tablepick",
        help="Base name for output files. (default: tablepick)",
    )
    parser.add_argument(
        "--stdout",
        dest="stdout",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Print tables to stdout. (default: --stdout)",
    )

    # ---- json options ----
    parser.add_argument(
        "--json-indent",
        dest="json_indent",
        type=int,
        default=None,
        help="Indent level for JSON output (format=json only).",
    )
    parser.add_argument(
        "--ensure-ascii",
        dest="ensure_ascii",
        action="store_true",
        help="Escape non-ASCII characters in JSON output (format=json only).",
    )

    # ---- fetch options (FetchConfig) ----
    parser.add_argument(
        "--timeout",
        dest="timeout",
        type=int,
        default=FetchConfig().timeout,
        help=f"HTTP request timeout in seconds. (default: {FetchConfig().timeout})",
    )
    parser.add_argument(
        "--retries",
        dest="retries",
        type=int,
        default=FetchConfig().retries,
        help=f"Number of retries on request failure. (default: {FetchConfig().retries})",
    )
    parser.add_argument(
        "--max-redirects",
        dest="max_redirects",
        type=int,
        default=FetchConfig().max_redirects,
        help=f"Maximum number of redirects to follow. (default: {FetchConfig().max_redirects})",
    )

    # ---- misc ----
    parser.add_argument(
        "--version",
        action="version",
        version=f"tablepick {__version__}",
        help="Show version and exit.",
    )
    parser.add_argument(
        "--debug",
        dest="debug",
        action="store_true",
        help="Dump parsed configs for debugging (printing is handled by main.py).",
    )

    return parser


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def make_fetch_config(ns: argparse.Namespace) -> FetchConfig:
    """
    argparse.Namespace から FetchConfig を生成する。

    NOTE:
    - retry_interval は CLI から変更不可。
      必ず core/__init__.py の FetchConfig デフォルト値を採用する。
    """
    default_retry_interval = FetchConfig().retry_interval
    return FetchConfig(
        timeout=int(ns.timeout),
        retries=int(ns.retries),
        retry_interval=default_retry_interval,
        max_redirects=int(ns.max_redirects),
    )


def make_output_options(ns: argparse.Namespace) -> OutputOptions:
    """
    argparse.Namespace から OutputOptions を生成する。
    """
    fmt: OutputFormat = _cast_format(ns.fmt)

    return OutputOptions(
        fmt=fmt,
        out_dir=ns.out_dir,
        base_name=str(ns.filename_base),
        stdout=bool(ns.stdout),
        ensure_ascii=bool(ns.ensure_ascii),
        indent=ns.json_indent,
    )


def debug_dump(ns: argparse.Namespace) -> dict:
    """
    main.py 側で --debug 時に利用するためのデバッグ情報を辞書で返す。
    （出力先は main.py 側で制御する）
    """
    fetch = make_fetch_config(ns)
    out = make_output_options(ns)
    return {
        "url": ns.url,
        "fetch_config": asdict(fetch),
        "output_options": asdict(out),
    }


def _validate_url_strict(value: str) -> str:
    """
    scheme 必須で URL を厳格に検証する。
    - http / https のみ許可
    - netloc 必須

    失敗時は argparse のエラーとして扱う。
    """
    v = (value or "").strip()
    parsed = urlparse(v)

    if not parsed.scheme:
        raise argparse.ArgumentTypeError(
            "URL scheme is missing. Please specify a full URL including scheme (e.g., https://example.com)."
        )
    if parsed.scheme not in ("http", "https"):
        raise argparse.ArgumentTypeError(
            "Unsupported URL scheme. Only http and https are allowed."
        )
    if not parsed.netloc:
        raise argparse.ArgumentTypeError(
            "Invalid URL: host is missing (netloc empty). Example: https://example.com"
        )

    return v


def _cast_format(fmt: str) -> OutputFormat:
    f = (fmt or "").strip().lower()
    if f == "csv":
        return "csv"
    if f == "json":
        return "json"
    # argparse choices により通常ここへ来ない
    raise ValueError(f"Invalid format: {fmt!r}")
