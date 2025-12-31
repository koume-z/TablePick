"""
TablePick - get_html.py

このモジュールは「指定URLからHTML(静的)を取得する」責務のみを持つ。
設定値（FetchConfig）は src/core/__init__.py に集約し、本モジュールでは参照のみ行う。
"""

from __future__ import annotations

import time
import warnings
from typing import Optional, Set, TYPE_CHECKING
from urllib.parse import urljoin, urlparse

import requests

# core/__init__.py に定義された設定クラスを利用する
if TYPE_CHECKING:
    from . import FetchConfig


# NOTE:
# User-Agent は fetcher 固有の責務としてここで定義する
DEFAULT_HEADERS = {
    "User-Agent": "TablePick/1.0 (contact: xxxx@xxx.com) requests"
}


class HtmlFetcher:
    def __init__(self, config: FetchConfig, headers: Optional[dict] = None):
        self.config = config
        self.headers = headers or DEFAULT_HEADERS

    # ==================================================
    # public method
    # ==================================================

    # 次のメソッド:
    # - URLを正規化し、ポリシーに従ってHTMLを取得する
    # - (html, final_url, response) を返す
    def fetch(self, url: str) -> tuple[str, str, requests.Response]:
        # 1) URLを内部処理用に正規化する
        normalized_url = self._normalize_url(url)

        # 2) HTTPスキームの場合は警告を出す（処理は継続）
        self._warn_if_http(normalized_url)

        # 3) retry / timeout 等のポリシーに従ってリクエストを送信
        response = self._request_with_policy(normalized_url)

        # 4) リダイレクトを最大回数まで追従する
        response = self._follow_redirects(response)

        # 5) HTTPエラーを明示的に検出する
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise requests.HTTPError(
                f"{e} (status={response.status_code}, url={response.url})"
            ) from e

        # 6) HTML本文を取得（encoding判定はrequestsに委ねる）
        html = response.text

        # 7) JavaScript生成ページの可能性があれば警告する
        self._warn_if_js_generated(html, response)

        return html, response.url, response

    # ==================================================
    # private methods
    # ==================================================

    # 次のメソッド:
    # - URLを正規化し、内部処理での表記ゆれを防ぐ
    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(url)

        # 要素1: schemeが無い場合は https を補完する
        if not parsed.scheme:
            url = "https://" + url
            parsed = urlparse(url)

        # 要素2: scheme / netloc を小文字に統一する
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()

        # 要素3: pathが空の場合は "/" を明示的に付与する
        path = parsed.path or "/"

        # 要素4: query は保持する（検索条件として重要なため）
        query = f"?{parsed.query}" if parsed.query else ""

        return f"{scheme}://{netloc}{path}{query}"

    # 次のメソッド:
    # - HTTPS推奨のため、HTTPの場合は警告を出す
    def _warn_if_http(self, url: str) -> None:
        parsed = urlparse(url)

        # 要素: schemeがhttpの場合のみ警告
        if parsed.scheme == "http":
            warnings.warn(
                "This URL uses HTTP. HTTPS is recommended.",
                UserWarning,
                stacklevel=2,
            )

    # 次のメソッド:
    # - FetchConfig に従って GET リクエストを実行する
    def _request_with_policy(self, url: str) -> requests.Response:
        last_exc: Optional[Exception] = None

        # 要素1: retries + 初回分の回数だけ試行する
        for attempt in range(self.config.retries + 1):
            try:
                return requests.get(
                    url,
                    headers=self.headers,
                    timeout=self.config.timeout,
                    allow_redirects=False,  # リダイレクトは自前で処理
                )
            except requests.RequestException as e:
                last_exc = e

                # 要素2: リトライ可能なら一定時間待って再試行
                if attempt < self.config.retries:
                    time.sleep(self.config.retry_interval)

        # 要素3: 全試行失敗時は最後の例外を送出
        assert last_exc is not None
        raise last_exc

    # 次のメソッド:
    # - Locationヘッダを見てリダイレクトを追従する
    def _follow_redirects(self, response: requests.Response) -> requests.Response:
        redirects_followed = 0
        visited: Set[str] = set()

        # 要素1: 初回URLを記録（ループ防止）
        if response.url:
            visited.add(response.url)

        while True:
            # 要素2: リダイレクトでなければ終了
            if not response.is_redirect and not response.is_permanent_redirect:
                return response

            # 要素3: Locationが無ければ追従不能
            location = response.headers.get("Location")
            if not location:
                return response

            # 要素4: 最大回数を超えた場合は例外
            if redirects_followed >= self.config.max_redirects:
                raise requests.TooManyRedirects(
                    f"Too many redirects (>{self.config.max_redirects}). "
                    f"last_url={response.url}"
                )

            # 要素5: 相対URLを絶対URLへ解決
            next_url = urljoin(response.url, location)

            # 要素6: リダイレクトループ検出
            if next_url in visited:
                raise requests.TooManyRedirects(
                    f"Redirect loop detected: {next_url}"
                )
            visited.add(next_url)

            # 要素7: 次URLへリクエスト
            response = self._request_with_policy(next_url)
            redirects_followed += 1

    # 次のメソッド:
    # - JavaScript生成ページの可能性を検知し警告する
    def _warn_if_js_generated(
        self, html: str, response: requests.Response
    ) -> None:
        # 要素1: Content-TypeがHTML以外の場合は警告
        content_type = (response.headers.get("Content-Type") or "").lower()
        if content_type and "text/html" not in content_type:
            warnings.warn(
                f"Content-Type is not text/html (got: {content_type})",
                UserWarning,
                stacklevel=2,
            )
            return

        lower_html = html.lower()

        # 要素2: JavaScript必須を示す典型文言を検出
        js_messages = (
            "enable javascript",
            "requires javascript",
            "please enable javascript",
            "javascript is disabled",
        )
        if any(msg in lower_html for msg in js_messages):
            warnings.warn(
                "This page appears to require JavaScript to render content.",
                UserWarning,
                stacklevel=2,
            )
            return

        # 要素3: scriptタグ過多＋本文が短い場合のヒューリスティック警告
        if lower_html.count("<script") >= 10 and len(html) < 30_000:
            warnings.warn(
                "This page may rely heavily on JavaScript for rendering.",
                UserWarning,
                stacklevel=2,
            )
