from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from xianyu_cli.api.client import APIClient


class DummyResponse:
    def __init__(self, payload: dict | list | None = None, *, status_code: int = 200) -> None:
        self._payload = payload if payload is not None else {"success": True}
        self.status_code = status_code
        self.headers = {"content-type": "application/json"}
        self.text = ""

    def json(self):
        return self._payload


class DummyHTTPClient:
    def __init__(self, response: DummyResponse) -> None:
        self.response = response
        self.calls: list[dict] = []

    def request(self, method, path, **kwargs):
        files = kwargs.get("files")
        file_name = None
        content_type = None
        if isinstance(files, dict) and "image" in files:
            image_entry = files["image"]
            if isinstance(image_entry, tuple) and len(image_entry) >= 3:
                file_name = image_entry[0]
                content_type = image_entry[2]
        self.calls.append(
            {
                "method": method,
                "path": path,
                "json": kwargs.get("json"),
                "timeout": kwargs.get("timeout"),
                "has_timeout": "timeout" in kwargs,
                "has_files": files is not None,
                "file_name": file_name,
                "content_type": content_type,
            }
        )
        return self.response

    def close(self) -> None:
        return None


class APIClientTests(unittest.TestCase):
    def test_publish_product_uses_publish_timeout(self) -> None:
        client = APIClient("http://127.0.0.1:8090", "test-token", timeout=30.0, publish_timeout=180.0)
        client._client.close()
        dummy_client = DummyHTTPClient(DummyResponse({"success": True}))
        client._client = dummy_client

        try:
            client.publish_product({"cookie_id": "demo"})
        finally:
            client.close()

        self.assertEqual(len(dummy_client.calls), 1)
        self.assertEqual(dummy_client.calls[0]["path"], "/api/products/publish")
        self.assertTrue(dummy_client.calls[0]["has_timeout"])
        self.assertEqual(dummy_client.calls[0]["timeout"], 180.0)

    def test_health_check_uses_default_timeout(self) -> None:
        client = APIClient("http://127.0.0.1:8090", "test-token", timeout=30.0, publish_timeout=180.0)
        client._client.close()
        dummy_client = DummyHTTPClient(DummyResponse({"status": "healthy"}))
        client._client = dummy_client

        try:
            client.check_health()
        finally:
            client.close()

        self.assertEqual(len(dummy_client.calls), 1)
        self.assertEqual(dummy_client.calls[0]["path"], "/health")
        self.assertFalse(dummy_client.calls[0]["has_timeout"])
        self.assertIsNone(dummy_client.calls[0]["timeout"])

    def test_upload_image_posts_multipart_file(self) -> None:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        tmp.write(b"fake-image")
        tmp.flush()
        tmp.close()
        self.addCleanup(lambda: Path(tmp.name).unlink(missing_ok=True))

        client = APIClient("http://127.0.0.1:8090", "test-token", timeout=30.0, publish_timeout=180.0)
        client._client.close()
        dummy_client = DummyHTTPClient(DummyResponse({"image_url": "/static/uploads/images/demo.png"}))
        client._client = dummy_client

        try:
            image_url = client.upload_image(tmp.name)
        finally:
            client.close()

        self.assertEqual(image_url, "/static/uploads/images/demo.png")
        self.assertEqual(len(dummy_client.calls), 1)
        self.assertEqual(dummy_client.calls[0]["path"], "/upload-image")
        self.assertTrue(dummy_client.calls[0]["has_files"])
        self.assertEqual(dummy_client.calls[0]["file_name"], Path(tmp.name).name)
        self.assertEqual(dummy_client.calls[0]["content_type"], "image/png")

    def test_list_cards_uses_cards_path(self) -> None:
        client = APIClient("http://127.0.0.1:8090", "test-token")
        client._client.close()
        dummy_client = DummyHTTPClient(DummyResponse([{"id": 1, "name": "A"}]))
        client._client = dummy_client

        try:
            cards = client.list_cards()
        finally:
            client.close()

        self.assertEqual(cards[0]["id"], 1)
        self.assertEqual(dummy_client.calls[0]["path"], "/cards")

    def test_create_delivery_rule_posts_json(self) -> None:
        client = APIClient("http://127.0.0.1:8090", "test-token")
        client._client.close()
        dummy_client = DummyHTTPClient(DummyResponse({"id": 5, "message": "ok"}))
        client._client = dummy_client

        try:
            payload = {"keyword": "demo", "card_id": 1, "delivery_count": 1}
            response = client.create_delivery_rule(payload)
        finally:
            client.close()

        self.assertEqual(response["id"], 5)
        self.assertEqual(dummy_client.calls[0]["path"], "/delivery-rules")
        self.assertEqual(dummy_client.calls[0]["json"], payload)


if __name__ == "__main__":
    unittest.main()
