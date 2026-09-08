import json
import logging
import random
import requests
import time
from dataclasses import dataclass, field
from typing import Union, Literal, Optional

LOGGER = logging.getLogger(__name__)

DataType = Literal['json', 'text']

def get_url(base: str, endpoint: str) -> str:
    if base.endswith('/') and endpoint.startswith('/'):
        base = base[:-1]
    elif not base.endswith('/') and not endpoint.startswith('/'):
        base = f'{base}/'

    return f'{base}{endpoint}'

def serialize(data, data_type: DataType):
    if data_type == 'json':
        return json.dumps(data)
    return str(data)

@dataclass
class Response:
    status: int
    data: Union[dict, list, str]

class RequestException(Exception):
    def __init__(self, status: int, data, url: str, method: str):
        self.status = status
        self.data = data
        self.url = url
        self.method = method
        super().__init__(f'{method} {url} failed with status {status}:\n{data}')

@dataclass
class HttpClient:
    base: str
    headers: dict = field(default_factory=dict)
    default_data_type: DataType = 'json'
    raises_exception: bool = False
    basic: tuple = field(default=None)
    max_retries: int = 5
    timeout: int = 30

    def get(self, endpoint, **kwargs) -> Response:
        return self.request('GET', endpoint, **kwargs)

    def post(self, endpoint, data=None, files=None, **kwargs) -> Response:
        return self.request('POST', endpoint, data=data, files=files, **kwargs)

    def put(self, endpoint, data=None, **kwargs) -> Response:
        return self.request('PUT', endpoint, data=data, **kwargs)

    def patch(self, endpoint, data=None, **kwargs) -> Response:
        return self.request('PATCH', endpoint, data=data, **kwargs)

    def delete(self, endpoint, **kwargs) -> Response:
        return self.request('DELETE', endpoint, **kwargs)

    def request(
        self,
        method: str,
        endpoint: str,
        *,
        headers: Optional[dict] = None,
        params: Optional[dict] = None,
        data=None,
        files=None,
        data_type: Optional[DataType] = None,
    ) -> Response:
        
        url = get_url(self.base, endpoint)
        data_type = data_type or self.default_data_type

        req_headers = {**self.headers, **(headers or {})}

        payload = None
        if data is not None:
            payload = serialize(data, data_type)

            if data_type == "json":
                req_headers["Content-Type"] = "application/json"

        for attempt in range(self.max_retries + 1):
            res = requests.request(
                method=method,
                url=url,
                headers=req_headers,
                params=params,
                data=payload,
                files=files,
                auth=self.basic,
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
            raise RequestException(
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
