"""
cli/prompt.py

CLI実行時に未指定の重要オプションを対話形式で補完する。

対象（args.pyで定義されたもののうち、対話で補完したいもの）:
- --url
- --format
- --out-dir
- --filename-base
- --stdout / --no-stdout

設計:
- 「指定されていない場合のみ」プロンプトを出すため、argv を参照して判定する。
- URLは strict（scheme必須・http/httpsのみ・host必須）で検証し、失敗したら再入力させる。
- out-dir は空入力を許可し、その場合は None（ファイル出力しない）とする。
- filename-base は空入力を許可し、その場合は "tablepick" を使う。
- stdout は Y/n で選択できるようにし、デフォルトは True。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Literal
from urllib.parse import urlparse

OutputFormat = Literal["csv", "json"]


@dataclass(frozen=True)
class PromptResult:
    url: str
    fmt: OutputFormat
    out_dir: Optional[str]
    filename_base: str
    stdout: bool


def fill_missing_with_prompt(
    *,
    argv: Sequence[str],
    url: Optional[str],
    fmt: str,
    out_dir: Optional[str],
    filename_base: Optional[str],
    stdout: bool,
) -> PromptResult:
    """
    args.py でパースした値＋argv を入力として、
    「未指定のものだけ」対話で埋めた結果を返す。

    想定（main.py側）:
    - argv は sys.argv[1:] をそのまま渡す
    - url は parse前/後いずれでも良いが、parse前に拾えないなら None で来る想定
    - fmt/out_dir/filename_base/stdout は args.py のデフォルトが入っている可能性があるため、
      argv にフラグがあるかどうかで「指定されたか」を判定する。
    """
    argv_set = set(argv)

    # ---- URL: --url が無いなら対話入力 ----
    if "--url" not in argv_set or not url:
        url = _prompt_url()

    # ---- format: --format が無いなら対話入力 ----
    if "--format" not in argv_set:
        fmt = _prompt_format(default="csv")
    else:
        fmt = _normalize_format(fmt)

    # ---- out-dir: --out-dir が無いなら対話入力 ----
    if "--out-dir" not in argv_set:
        out_dir = _prompt_out_dir()

    # ---- filename-base: --filename-base が無いなら対話入力 ----
    if "--filename-base" not in argv_set:
        filename_base = _prompt_filename_base(default="tablepick")
    else:
        filename_base = filename_base or "tablepick"

    # ---- stdout: --stdout/--no-stdout が無いなら対話入力 ----
    if ("--stdout" not in argv_set) and ("--no-stdout" not in argv_set):
        stdout = _prompt_stdout(default=True)

    return PromptResult(
        url=url,
        fmt=fmt,  # type: ignore[arg-type]
        out_dir=out_dir,
        filename_base=filename_base,
        stdout=stdout,
    )


# ----------------------------
# prompt implementations
# ----------------------------

def _prompt_url() -> str:
    while True:
        raw = input("URL（http/https の scheme 必須）: ").strip()
        try:
            return _validate_url_strict(raw)
        except ValueError as e:
            print(f"[error] {e}")
            exit()


def _prompt_format(*, default: OutputFormat) -> OutputFormat:
    while True:
        raw = input(f"出力形式 format [csv/json] (default: {default}): ").strip()
        if raw == "":
            return default
        try:
            return _normalize_format(raw)
        except ValueError as e:
            print(f"[error] {e}")
            exit()


def _prompt_out_dir() -> Optional[str]:
    raw = input("出力先ディレクトリ out-dir（空ならファイル出力しない）: ").strip()
    return raw or None


def _prompt_filename_base(*, default: str) -> str:
    raw = input(f"出力ファイルのベース名 filename-base (default: {default}): ").strip()
    return raw or default


def _prompt_stdout(*, default: bool) -> bool:
    # True -> Y/n, False -> y/N
    suffix = "Y/n" if default else "y/N"
    while True:
        raw = input(f"stdout にも出力しますか？ [{suffix}]: ").strip().lower()
        if raw == "":
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("[error] y / n で入力してください。")


# ----------------------------
# validation helpers
# ----------------------------

def _validate_url_strict(value: str) -> str:
    v = (value or "").strip()
    if not v:
        raise ValueError("URL が空です。例: https://example.com")
        sys.exit()

    parsed = urlparse(v)
    if not parsed.scheme:
        raise ValueError("URL scheme がありません。http/https を含む完全なURLを入力してください。例: https://example.com")
    if parsed.scheme not in ("http", "https"):
        raise ValueError("未対応の scheme です。http / https のみ許可されます。")
    if not parsed.netloc:
        raise ValueError("ホスト名がありません（netloc が空です）。例: https://example.com")

    return v


def _normalize_format(value: str) -> OutputFormat:
    v = (value or "").strip().lower()
    if v in ("csv", "json"):
        return v  # type: ignore[return-value]
    raise ValueError("format は csv または json を指定してください。")
