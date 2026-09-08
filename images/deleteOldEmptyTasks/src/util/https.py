from dataclasses import dataclass
import json
import logging
import random
import time
from typing import Optional, Union

import requests

LOGGER = logging.getLogger(__name__)


@dataclass
class Response:
    status: int
    data: Union[dict, list, str]


class HttpException(Exception):
    def __init__(self, status: int, data, url: str, method: str):
        self.status = status
        self.data = data
        self.url = url
        self.method = method
        super().__init__(f"{method} {url} failed with status {status}:\n{data}")


class HttpClient:
    base: str
    headers: dict[str, str]
    raises_exception: bool
    max_retries: int
    timeout: int

    def __init__(
        self,
        base: str = "",
        headers: Optional[dict[str, str]] = None,
        raises_exception: bool = False,
        max_retries: int = 5,
        timeout: int = 30
    ):
        self.base = base
        self.headers = headers or {}
        self.raises_exception = raises_exception
        self.max_retries = max_retries
        self.timeout = timeout

    def get(
        self,
        endpoint: str,
        params: Optional[dict] = None,
        headers: Optional[dict[str, str]] = None
    ):
        return self.request(
            method="GET",
            endpoint=endpoint,
            params=params,
            headers=headers
        )

    def delete(
        self,
        endpoint: str,
        params: Optional[dict] = None,
        headers: Optional[dict[str, str]] = None
    ):
        return self.request(
            method="DELETE",
            endpoint=endpoint,
            params=params,
            headers=headers
        )

    def request(
        self,
        method: str,
        endpoint: str,
        data=None,
        params: Optional[dict] = None,
        headers: Optional[dict[str, str]] = None
    ):
        headers = self.headers | (headers or {})
        url = f"{self.base}{endpoint}"

        for attempt in range(self.max_retries + 1):
            res = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=json.dumps(data) if data is not None else None,
                params=params,
                timeout=self.timeout
            )

            status = res.status_code
            try:
                res_data = res.json()
            except ValueError:
                res_data = res.text

            if status != 429 or attempt >= self.max_retries:
                break

            retry_delay = self._get_retry_delay(res, attempt)
            LOGGER.warning(
                "[RATE_LIMIT] %s %s returned 429; retrying in %.2fs "
                "(attempt %s/%s, limit=%s, remaining=%s, reset=%s)",
                method,
                url,
                retry_delay,
                attempt + 1,
                self.max_retries,
                res.headers.get("X-RateLimit-Limit"),
                res.headers.get("X-RateLimit-Remaining"),
                res.headers.get("X-RateLimit-Reset")
            )
            time.sleep(retry_delay)

        if self.raises_exception and (400 <= status < 600):
            raise HttpException(
                status=status,
                data=res_data,
                url=url,
                method=method
            )

        return Response(status, res_data)

    def _get_retry_delay(self, res: requests.Response, attempt: int) -> float:
        reset = res.headers.get("X-RateLimit-Reset")
        if reset:
            try:
                delay = int(reset) - time.time()
                return max(delay + 1, 1)
            except ValueError:
                pass

        backoff = min(2 ** attempt, 30)
        return backoff + random.uniform(0, 1)
