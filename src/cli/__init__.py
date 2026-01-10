"""
cli package

TablePick の CLI 層。
- args.py   : 引数定義・設定生成
- prompt.py : 対話入力による不足オプション補完
- main.py   : CLI 実行のオーケストレーション（entrypoint）

ここでは外部から利用しやすい最低限のAPIを re-export する。
"""

from .main import main
from .args import build_parser, parse_args, make_fetch_config, make_output_options, debug_dump
from .prompt import fill_missing_with_prompt, PromptResult

__all__ = [
    # entrypoint
    "main",
    # args helpers
    "build_parser",
    "parse_args",
    "make_fetch_config",
    "make_output_options",
    "debug_dump",
    # prompt helpers
    "fill_missing_with_prompt",
    "PromptResult",
]
