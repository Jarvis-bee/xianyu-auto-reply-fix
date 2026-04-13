from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any, Optional

import httpx


class APIClientError(RuntimeError):
    """Raised when the backend service cannot fulfill a CLI request."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        payload: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


def normalize_bearer_token(token: str) -> str:
    """Normalize raw token input into a Bearer header value."""
    cleaned = str(token or "").strip()
    if not cleaned:
        raise ValueError("缺少后台 token，请通过 --token 或 XIANYU_TOKEN 提供")

    if cleaned.lower().startswith("bearer "):
        cleaned = cleaned.split(None, 1)[1].strip()

    if not cleaned:
        raise ValueError("后台 token 不能为空")

    return f"Bearer {cleaned}"


class APIClient:
    """Thin synchronous HTTP client for the existing FastAPI service."""

    def __init__(
        self,
        server: str,
        token: str,
        *,
        timeout: float = 30.0,
        publish_timeout: float = 180.0,
    ) -> None:
        cleaned_server = str(server or "").strip().rstrip("/")
        if not cleaned_server:
            raise ValueError("服务地址不能为空")

        self.base_url = cleaned_server
        self.token = normalize_bearer_token(token)
        self.timeout = timeout
        self.publish_timeout = publish_timeout
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={
                "Accept": "application/json",
                "Authorization": self.token,
            },
        )

    def __enter__(self) -> "APIClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def check_health(self) -> dict[str, Any]:
        payload = self._request("GET", "/health")
        if not isinstance(payload, dict):
            raise APIClientError("健康检查返回格式不正确", payload=payload)

        if payload.get("status") != "healthy":
            raise APIClientError(
                f"服务健康检查未通过: {payload.get('status') or 'unknown'}",
                payload=payload,
            )

        return payload

    def get_cookie_details(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/cookies/details")
        return self._expect_list(payload, "账号列表返回格式不正确")

    def upload_image(self, image_path: str | Path) -> str:
        path = Path(image_path)
        media_type = mimetypes.guess_type(path.name)[0] or "image/png"
        if not media_type.startswith("image/"):
            media_type = "image/png"

        try:
            with path.open("rb") as handle:
                payload = self._request(
                    "POST",
                    "/upload-image",
                    files={"image": (path.name, handle, media_type)},
                )
        except OSError as exc:
            raise APIClientError(f"读取图片失败: {path}") from exc

        if not isinstance(payload, dict):
            raise APIClientError("图片上传接口返回格式不正确", payload=payload)

        image_url = str(payload.get("image_url") or "").strip()
        if not image_url:
            raise APIClientError("图片上传成功但未返回 image_url", payload=payload)

        return image_url

    def publish_product(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._request(
            "POST",
            "/api/products/publish",
            json_body=payload,
            timeout=self.publish_timeout,
        )
        return self._expect_dict(response, "发布接口返回格式不正确")

    def list_cards(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/cards")
        return self._expect_list(payload, "卡片列表返回格式不正确")

    def get_card(self, card_id: int) -> dict[str, Any]:
        payload = self._request("GET", f"/cards/{int(card_id)}")
        return self._expect_dict(payload, "卡片详情返回格式不正确")

    def create_card(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._request("POST", "/cards", json_body=payload)
        return self._expect_dict(response, "卡片创建接口返回格式不正确")

    def update_card(self, card_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._request("PUT", f"/cards/{int(card_id)}", json_body=payload)
        return self._expect_dict(response, "卡片更新接口返回格式不正确")

    def delete_card(self, card_id: int) -> dict[str, Any]:
        response = self._request("DELETE", f"/cards/{int(card_id)}")
        return self._expect_dict(response, "卡片删除接口返回格式不正确")

    def list_delivery_rules(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/delivery-rules")
        return self._expect_list(payload, "发货规则列表返回格式不正确")

    def get_delivery_rule(self, rule_id: int) -> dict[str, Any]:
        payload = self._request("GET", f"/delivery-rules/{int(rule_id)}")
        return self._expect_dict(payload, "发货规则详情返回格式不正确")

    def create_delivery_rule(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._request("POST", "/delivery-rules", json_body=payload)
        return self._expect_dict(response, "发货规则创建接口返回格式不正确")

    def update_delivery_rule(self, rule_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._request("PUT", f"/delivery-rules/{int(rule_id)}", json_body=payload)
        return self._expect_dict(response, "发货规则更新接口返回格式不正确")

    def delete_delivery_rule(self, rule_id: int) -> dict[str, Any]:
        response = self._request("DELETE", f"/delivery-rules/{int(rule_id)}")
        return self._expect_dict(response, "发货规则删除接口返回格式不正确")

    def get_delivery_rule_stats(self) -> dict[str, Any]:
        payload = self._request("GET", "/delivery-rules/stats")
        return self._expect_dict(payload, "发货统计接口返回格式不正确")

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        files: Any = None,
        timeout: float | httpx.Timeout | None = None,
    ) -> Any:
        try:
            request_kwargs: dict[str, Any] = {}
            if json_body is not None:
                request_kwargs["json"] = json_body
            if files is not None:
                request_kwargs["files"] = files
            if timeout is not None:
                request_kwargs["timeout"] = timeout
            response = self._client.request(method, path, **request_kwargs)
        except httpx.HTTPError as exc:
            raise APIClientError(f"无法连接服务 {self.base_url}: {exc}") from exc

        payload: Any = None
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type.lower():
            try:
                payload = response.json()
            except ValueError:
                payload = None

        if response.status_code >= 400:
            raise APIClientError(
                self._extract_error_message(response, payload),
                status_code=response.status_code,
                payload=payload,
            )

        if payload is not None:
            return payload

        return response.text

    def _extract_error_message(self, response: httpx.Response, payload: Any) -> str:
        detail = ""

        if isinstance(payload, dict):
            detail = str(payload.get("detail") or payload.get("message") or "").strip()
        elif isinstance(payload, list):
            detail = str(payload).strip()

        if not detail:
            text = response.text.strip()
            if text:
                detail = text

        if detail:
            return f"请求失败 ({response.status_code}): {detail}"

        return f"请求失败 ({response.status_code})"

    def _expect_dict(self, payload: Any, message: str) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise APIClientError(message, payload=payload)
        return payload

    def _expect_list(self, payload: Any, message: str) -> list[dict[str, Any]]:
        if not isinstance(payload, list):
            raise APIClientError(message, payload=payload)
        return payload
