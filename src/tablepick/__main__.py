"""
tablepick/__main__.py

`python -m tablepick ...` の実行エントリポイント。

方針:
- 実際の CLI 実行は cli/main.py の main() に委譲する。
- main() が返す終了コードをそのまま sys.exit() に渡す。
"""

from __future__ import annotations

import sys


def _run() -> int:
    # CLI 実装は cli/main.py に集約
    from tablepick.cli.main import main as cli_main

    code = cli_main(sys.argv[1:])

    # 念のため: None が返ってきた場合は成功扱いに寄せる
    if code is None:
        return 0

    try:
        return int(code)
    except Exception:
        # 変な値が返った場合は想定外として 2
        return 2


if __name__ == "__main__":
    raise SystemExit(_run())
