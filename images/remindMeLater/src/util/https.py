from dataclasses import dataclass
import json
from typing import Optional, Union

import requests


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

    def __init__(
        self,
        base: str = "",
        headers: Optional[dict[str, str]] = None,
        raises_exception: bool = False
    ):
        self.base = base
        self.headers = headers or {}
        self.raises_exception = raises_exception

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

        res = requests.request(
            method=method,
            url=url,
            headers=headers,
            data=json.dumps(data) if data is not None else None,
            params=params
        )

        status = res.status_code
        try:
            res_data = res.json()
        except ValueError:
            res_data = res.text

        if self.raises_exception and (400 <= status < 600):
            raise HttpException(
                status=status,
                data=res_data,
                url=url,
                method=method
            )

        return Response(status, res_data)
