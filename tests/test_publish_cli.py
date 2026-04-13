from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from xianyu_cli.commands.publish import handle_publish
from xianyu_cli.interactive.cookies import build_cookie_choices, parse_cookie_selection
from xianyu_cli.main import build_parser


class FakeStdin(io.StringIO):
    def __init__(self, value: str, *, interactive: bool) -> None:
        super().__init__(value)
        self._interactive = interactive

    def isatty(self) -> bool:
        return self._interactive


class FakeClient:
    def __init__(self, server: str, token: str) -> None:
        self.server = server
        self.token = token
        self.publish_calls: list[dict] = []
        self.upload_calls: list[str] = []
        self.cookies = []
        self.publish_responses: dict[str, dict] = {}
        self.raise_on_publish: dict[str, Exception] = {}
        self.health_checked = False

    def __enter__(self) -> "FakeClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def check_health(self) -> dict:
        self.health_checked = True
        return {"status": "healthy"}

    def get_cookie_details(self) -> list[dict]:
        return list(self.cookies)

    def upload_image(self, image_path: str) -> str:
        self.upload_calls.append(image_path)
        return f"/static/uploads/images/{Path(image_path).name}"

    def publish_product(self, payload: dict) -> dict:
        self.publish_calls.append(payload)
        cookie_id = payload["cookie_id"]
        if cookie_id in self.raise_on_publish:
            raise self.raise_on_publish[cookie_id]
        return self.publish_responses[cookie_id]


class FakeClientFactory:
    def __init__(self, client: FakeClient) -> None:
        self.client = client

    def __call__(self, server: str, token: str) -> FakeClient:
        self.client.server = server
        self.client.token = token
        return self.client


class PublishCLITests(unittest.TestCase):
    def test_root_help_contains_publish(self) -> None:
        parser = build_parser()
        help_text = parser.format_help()
        self.assertIn("publish", help_text)

    def test_publish_help_works(self) -> None:
        parser = build_parser()
        stdout = io.StringIO()
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stdout(stdout):
                parser.parse_args(["publish", "--help"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn("--cookie-id", stdout.getvalue())

    def test_parse_cookie_selection_space_separated(self) -> None:
        self.assertEqual(parse_cookie_selection("1 3 3 2", 3), [1, 3, 2])

    def test_build_cookie_choices_filters_disabled(self) -> None:
        raw = [
            {"id": "a", "enabled": True},
            {"id": "b", "enabled": False},
        ]
        choices = build_cookie_choices(raw, enabled_only=True)
        self.assertEqual([choice.cookie_id for choice in choices], ["a"])

    def test_publish_requires_cookie_id_in_non_interactive_mode(self) -> None:
        args = Namespace(
            cookie_ids=None,
            title="测试标题",
            description="测试描述",
            price=10.0,
            images=[self._create_temp_image()],
            category=None,
            location=None,
            original_price=None,
            server=None,
            token="test-token",
            json_output=False,
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        client = FakeClient("http://127.0.0.1:8090", "Bearer test-token")

        exit_code = handle_publish(
            args,
            client_factory=FakeClientFactory(client),
            stdin=FakeStdin("", interactive=False),
            stdout=stdout,
            stderr=stderr,
        )

        self.assertEqual(exit_code, 1)
        self.assertIn("未提供 --cookie-id", stderr.getvalue())

    def test_publish_prompts_and_runs_for_multiple_cookies(self) -> None:
        image_path = self._create_temp_image()
        args = Namespace(
            cookie_ids=None,
            title="测试标题",
            description="测试描述",
            price=10.0,
            images=[image_path],
            category=None,
            location=None,
            original_price=None,
            server=None,
            token="test-token",
            json_output=False,
        )
        client = FakeClient("http://127.0.0.1:8090", "Bearer test-token")
        client.cookies = [
            {"id": "cookie-a", "enabled": True, "remark": "A", "username": "userA", "runtime_status": {"running": True, "connection_state": "connected"}},
            {"id": "cookie-b", "enabled": True, "remark": "B", "username": "userB", "runtime_status": {"running": False, "connection_state": "not_running"}},
            {"id": "cookie-c", "enabled": False, "remark": "C", "username": "userC", "runtime_status": {}},
        ]
        client.publish_responses = {
            "cookie-a": {"success": True, "message": "商品发布成功", "product_id": "1001", "product_url": "https://example.com/1"},
            "cookie-b": {"success": True, "message": "商品发布成功", "product_id": "1002", "product_url": "https://example.com/2"},
        }
        stdout = io.StringIO()
        stderr = io.StringIO()

        exit_code = handle_publish(
            args,
            client_factory=FakeClientFactory(client),
            stdin=FakeStdin("1 2\n", interactive=True),
            stdout=stdout,
            stderr=stderr,
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual([call["cookie_id"] for call in client.publish_calls], ["cookie-a", "cookie-b"])
        self.assertIn("cookie-a", stdout.getvalue())
        self.assertIn("cookie-b", stdout.getvalue())

    def test_publish_continues_after_single_cookie_failure(self) -> None:
        image_path = self._create_temp_image()
        args = Namespace(
            cookie_ids=["cookie-a", "cookie-b"],
            title="测试标题",
            description="测试描述",
            price=10.0,
            images=[image_path],
            category=None,
            location=None,
            original_price=None,
            server=None,
            token="test-token",
            json_output=True,
        )
        client = FakeClient("http://127.0.0.1:8090", "Bearer test-token")
        client.publish_responses = {
            "cookie-a": {"success": False, "message": "Cookie 登录失败，请先确认账号状态"},
            "cookie-b": {"success": True, "message": "商品发布成功", "product_id": "1002"},
        }
        stdout = io.StringIO()
        stderr = io.StringIO()

        exit_code = handle_publish(
            args,
            client_factory=FakeClientFactory(client),
            stdin=FakeStdin("", interactive=False),
            stdout=stdout,
            stderr=stderr,
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual([call["cookie_id"] for call in client.publish_calls], ["cookie-a", "cookie-b"])
        self.assertIn('"failed": 1', stdout.getvalue())

    def test_publish_allows_zero_price_fields(self) -> None:
        image_path = self._create_temp_image()
        args = Namespace(
            cookie_ids=["cookie-a"],
            title="测试标题",
            description="测试描述",
            price=0.0,
            images=[image_path],
            category=None,
            location=None,
            original_price=0.0,
            server=None,
            token="test-token",
            json_output=False,
        )
        client = FakeClient("http://127.0.0.1:8090", "Bearer test-token")
        client.publish_responses = {
            "cookie-a": {"success": True, "message": "商品发布成功", "product_id": "1001"},
        }
        stdout = io.StringIO()
        stderr = io.StringIO()

        exit_code = handle_publish(
            args,
            client_factory=FakeClientFactory(client),
            stdin=FakeStdin("", interactive=False),
            stdout=stdout,
            stderr=stderr,
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(client.publish_calls), 1)
        self.assertEqual(client.publish_calls[0]["price"], 0.0)
        self.assertEqual(client.publish_calls[0]["original_price"], 0.0)

    def test_publish_uploads_local_images_to_server_before_publish(self) -> None:
        image_path = self._create_temp_image()
        args = Namespace(
            cookie_ids=["cookie-a"],
            title="测试标题",
            description="测试描述",
            price=10.0,
            images=[image_path],
            category=None,
            location=None,
            original_price=None,
            server="http://remote.example.com",
            token="test-token",
            json_output=False,
        )
        client = FakeClient("http://remote.example.com", "Bearer test-token")
        client.publish_responses = {
            "cookie-a": {"success": True, "message": "商品发布成功", "product_id": "1001"},
        }
        stdout = io.StringIO()
        stderr = io.StringIO()

        exit_code = handle_publish(
            args,
            client_factory=FakeClientFactory(client),
            stdin=FakeStdin("", interactive=False),
            stdout=stdout,
            stderr=stderr,
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(client.upload_calls), 1)
        self.assertEqual(
            client.publish_calls[0]["images"],
            [f"/static/uploads/images/{Path(image_path).name}"],
        )

    def test_publish_accepts_server_static_image_paths_without_local_upload(self) -> None:
        args = Namespace(
            cookie_ids=["cookie-a"],
            title="测试标题",
            description="测试描述",
            price=10.0,
            images=["/static/uploads/images/demo.jpg", "static/uploads/images/demo-2.jpg"],
            category=None,
            location=None,
            original_price=None,
            server="http://remote.example.com",
            token="test-token",
            json_output=False,
        )
        client = FakeClient("http://remote.example.com", "Bearer test-token")
        client.publish_responses = {
            "cookie-a": {"success": True, "message": "商品发布成功", "product_id": "1001"},
        }
        stdout = io.StringIO()
        stderr = io.StringIO()

        exit_code = handle_publish(
            args,
            client_factory=FakeClientFactory(client),
            stdin=FakeStdin("", interactive=False),
            stdout=stdout,
            stderr=stderr,
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(client.upload_calls, [])
        self.assertEqual(
            client.publish_calls[0]["images"],
            ["/static/uploads/images/demo.jpg", "static/uploads/images/demo-2.jpg"],
        )

    def test_publish_rejects_non_finite_prices(self) -> None:
        image_path = self._create_temp_image()
        args = Namespace(
            cookie_ids=["cookie-a"],
            title="测试标题",
            description="测试描述",
            price=float("nan"),
            images=[image_path],
            category=None,
            location=None,
            original_price=float("inf"),
            server=None,
            token="test-token",
            json_output=False,
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        client = FakeClient("http://127.0.0.1:8090", "Bearer test-token")

        exit_code = handle_publish(
            args,
            client_factory=FakeClientFactory(client),
            stdin=FakeStdin("", interactive=False),
            stdout=stdout,
            stderr=stderr,
        )

        self.assertEqual(exit_code, 1)
        self.assertIn("必须是有限数字", stderr.getvalue())
        self.assertEqual(client.upload_calls, [])
        self.assertEqual(client.publish_calls, [])

    def test_publish_json_keeps_stdout_clean_during_interactive_selection(self) -> None:
        image_path = self._create_temp_image()
        args = Namespace(
            cookie_ids=None,
            title="测试标题",
            description="测试描述",
            price=10.0,
            images=[image_path],
            category=None,
            location=None,
            original_price=None,
            server=None,
            token="test-token",
            json_output=True,
        )
        client = FakeClient("http://127.0.0.1:8090", "Bearer test-token")
        client.cookies = [
            {"id": "cookie-a", "enabled": True, "remark": "A", "username": "userA", "runtime_status": {"running": True, "connection_state": "connected"}},
        ]
        client.publish_responses = {
            "cookie-a": {"success": True, "message": "商品发布成功", "product_id": "1001"},
        }
        stdout = io.StringIO()
        stderr = io.StringIO()

        exit_code = handle_publish(
            args,
            client_factory=FakeClientFactory(client),
            stdin=FakeStdin("1\n", interactive=True),
            stdout=stdout,
            stderr=stderr,
        )

        self.assertEqual(exit_code, 0)
        self.assertIn("可用账号：", stderr.getvalue())
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["success"])
        self.assertEqual(payload["summary"]["success"], 1)

    def _create_temp_image(self) -> str:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        tmp.write(b"test-image")
        tmp.flush()
        tmp.close()
        self.addCleanup(self._cleanup_file, tmp.name)
        return tmp.name

    def _cleanup_file(self, file_path: str) -> None:
        path = Path(file_path)
        if path.exists():
            path.unlink()


if __name__ == "__main__":
    unittest.main()
