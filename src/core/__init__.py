from dataclasses import dataclass

@dataclass(frozen=True)
class FetchConfig:
    timeout: int = 10
    retries: int = 0
    retry_interval: int = 10
    max_redirects: int = 3


from .get_html import HtmlFetcher

__all__ = ["FetchConfig", "HtmlFetcher"]
