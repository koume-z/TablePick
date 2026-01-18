"""
cli/main.py

TablePick CLI の実行エントリポイント。
- args.py: 引数定義・設定生成
- prompt.py: 未指定の重要引数を対話で補完
- core: fetch / convert / output を実行

終了コード（目安）:
- 0: 成功
- 1: 想定内エラー（入力不備、取得失敗、テーブル無し等）
- 2: 想定外エラー
"""

from __future__ import annotations

import json
import sys
from typing import Optional, Sequence

from tablepick.core import HtmlFetcher
from tablepick.core.converter import HtmlTableConverter
from tablepick.core.output import TableOutputWriter

from . import args as cli_args
from . import prompt as cli_prompt


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv_list = list(argv) if argv is not None else sys.argv[1:]

    try:
        # 1) 足りない重要オプションを対話補完し、argv を拡張
        argv_list = _maybe_prompt_and_extend_argv(argv_list)

        # 2) 最終パース
        ns = cli_args.parse_args(argv_list)

        # 3) debug（stderr）
        if getattr(ns, "debug", False):
            _print_debug(ns)

        # 4) core 実行パイプライン
        fetch_config = cli_args.make_fetch_config(ns)
        out_opt = cli_args.make_output_options(ns)

        # HtmlFetcher.fetch は (html, final_url, response) を返す
        html, final_url, response = HtmlFetcher(config=fetch_config).fetch(ns.url)

        tables = HtmlTableConverter().convert(html)

        writer = TableOutputWriter()
        written = writer.emit(tables, out_opt)

        # stdout を汚さないため、状況メッセージは stderr に
        if out_opt.out_dir is not None:
            print(f"[tablepick] wrote {len(written)} file(s) to: {out_opt.out_dir}", file=sys.stderr)

        return 0

    except SystemExit as e:
        # argparse が exit するケース（invalid args）
        code = int(e.code) if e.code is not None else 1
        return code

    except Exception as e:
        # 例外体系は tablepick/error.py に集約される想定。
        # ここでは stdout を汚さないよう stderr に出して exit code=1 とする。
        print(f"[tablepick:error] {e}", file=sys.stderr)
        return 1


def _maybe_prompt_and_extend_argv(argv_list: list[str]) -> list[str]:
    """
    argv に重要オプションが不足している場合だけ prompt を起動し、
    入力された値で argv を補完して返す。

    対象（prompt.py の仕様）:
    - --url, --format, --out-dir, --filename-base, --stdout/--no-stdout
    """
    argv_set = set(argv_list)

    # --help がある場合はヘルプ表示だけ行う
    if "--help" in argv_set or "-h" in argv_set:
        return argv_list

    def _get_opt_value(opt: str) -> Optional[str]:
        """
        argv_list から `opt` の値を取り出す。
        - opt が無い → None
        - opt があるが値が無い（末尾）→ None
        - opt の次が別オプションっぽい（-で始まる）→ None
        """
        try:
            i = argv_list.index(opt)

        except ValueError:
            return None

        if i + 1 >= len(argv_list):
            return None

        v = argv_list[i + 1]
        if v.startswith("-"):
            return None

        return v

    provided_url = _get_opt_value("--url")
    need_prompt = (
        ("--url" not in argv_set)
        or ("--format" not in argv_set)
        or ("--out-dir" not in argv_set)
        or ("--filename-base" not in argv_set)
        or (("--stdout" not in argv_set) and ("--no-stdout" not in argv_set))
    )

    if not need_prompt:
        return argv_list

    pr = cli_prompt.fill_missing_with_prompt(
        argv=argv_list,
        url=provided_url,
        fmt="csv",
        out_dir=None,
        filename_base="tablepick",
        stdout=True,
    )

    extended = list(argv_list)

    if "--url" not in argv_set:
        extended += ["--url", pr.url]

    if "--format" not in argv_set:
        extended += ["--format", pr.fmt]

    if "--out-dir" not in argv_set:
        # 空入力は None（=ファイル出力しない）なので、その場合は追加しない
        if pr.out_dir is not None:
            extended += ["--out-dir", pr.out_dir]

    if "--filename-base" not in argv_set:
        extended += ["--filename-base", pr.filename_base]

    if ("--stdout" not in argv_set) and ("--no-stdout" not in argv_set):
        extended += ["--stdout"] if pr.stdout else ["--no-stdout"]

    return extended


def _print_debug(ns) -> None:
    """
    args.py の debug_dump を stderr に出す。
    """
    data = cli_args.debug_dump(ns)
    print("[tablepick:debug] parsed configs:", file=sys.stderr)
    print(json.dumps(data, ensure_ascii=False, indent=2), file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
