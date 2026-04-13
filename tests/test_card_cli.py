from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from xianyu_cli.commands.card import (
    handle_create_card,
    handle_update_card,
)
from xianyu_cli.main import build_parser


class FakeCardClient:
    def __init__(self, server: str, token: str) -> None:
        self.server = server
        self.token = token
        self.health_checked = False
        self.upload_calls: list[str] = []
        self.create_card_calls: list[dict] = []
        self.update_card_calls: list[dict] = []
        self.cards_by_id: dict[int, dict] = {}

    def __enter__(self) -> "FakeCardClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def check_health(self) -> dict:
        self.health_checked = True
        return {"status": "healthy"}

    def upload_image(self, image_path: str) -> str:
        self.upload_calls.append(image_path)
        return f"/static/uploads/images/{Path(image_path).name}"

    def create_card(self, payload: dict) -> dict:
        self.create_card_calls.append(payload)
        return {"id": 101, "message": "卡片创建成功"}

    def get_card(self, card_id: int) -> dict:
        return dict(self.cards_by_id[card_id])

    def update_card(self, card_id: int, payload: dict) -> dict:
        self.update_card_calls.append({"card_id": card_id, "payload": payload})
        return {"message": "卡片更新成功"}


class FakeCardClientFactory:
    def __init__(self, client: FakeCardClient) -> None:
        self.client = client

    def __call__(self, server: str, token: str) -> FakeCardClient:
        self.client.server = server
        self.client.token = token
        return self.client


class CardCLITests(unittest.TestCase):
    def test_root_help_contains_card_and_delivery_rule(self) -> None:
        parser = build_parser()
        help_text = parser.format_help()
        self.assertIn("card", help_text)
        self.assertIn("delivery-rule", help_text)

    def test_card_help_works(self) -> None:
        parser = build_parser()
        stdout = io.StringIO()
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stdout(stdout):
                parser.parse_args(["card", "create", "--help"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn("--type", stdout.getvalue())

    def test_create_api_card_serializes_headers_and_params_as_strings(self) -> None:
        args = Namespace(
            name="API 卡",
            card_type="api",
            description=None,
            delay_seconds=None,
            enabled=None,
            is_multi_spec=None,
            spec_name=None,
            spec_value=None,
            spec_name_2=None,
            spec_value_2=None,
            text_content=None,
            data_content=None,
            image=None,
            api_url="https://example.com/api",
            api_method="post",
            api_timeout="15",
            api_headers_json='{"Authorization":"Bearer token"}',
            api_params_json='{"foo":"bar"}',
            yifan_user_id=None,
            yifan_user_key=None,
            yifan_goods_id=None,
            yifan_callback_url=None,
            yifan_require_account=None,
            generate_delivery_rule=False,
            server=None,
            token="test-token",
            json_output=False,
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        client = FakeCardClient("http://127.0.0.1:8090", "Bearer test-token")

        exit_code = handle_create_card(
            args,
            client_factory=FakeCardClientFactory(client),
            stdout=stdout,
            stderr=stderr,
        )

        self.assertEqual(exit_code, 0)
        payload = client.create_card_calls[0]
        self.assertEqual(payload["api_config"]["headers"], '{"Authorization":"Bearer token"}')
        self.assertEqual(payload["api_config"]["params"], '{"foo":"bar"}')

    def test_create_image_card_uploads_local_image(self) -> None:
        image_path = self._create_temp_image()
        args = Namespace(
            name="图片卡",
            card_type="image",
            description=None,
            delay_seconds="3",
            enabled=None,
            is_multi_spec=None,
            spec_name=None,
            spec_value=None,
            spec_name_2=None,
            spec_value_2=None,
            text_content=None,
            data_content=None,
            image=image_path,
            api_url=None,
            api_method=None,
            api_timeout=None,
            api_headers_json=None,
            api_params_json=None,
            yifan_user_id=None,
            yifan_user_key=None,
            yifan_goods_id=None,
            yifan_callback_url=None,
            yifan_require_account=None,
            generate_delivery_rule=True,
            server=None,
            token="test-token",
            json_output=False,
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        client = FakeCardClient("http://127.0.0.1:8090", "Bearer test-token")

        exit_code = handle_create_card(
            args,
            client_factory=FakeCardClientFactory(client),
            stdout=stdout,
            stderr=stderr,
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(client.upload_calls), 1)
        self.assertEqual(client.create_card_calls[0]["image_url"], f"/static/uploads/images/{Path(image_path).name}")
        self.assertTrue(client.create_card_calls[0]["generate_delivery_rule"])

    def test_create_image_card_accepts_server_static_path_without_upload(self) -> None:
        args = Namespace(
            name="图片卡",
            card_type="image",
            description=None,
            delay_seconds=None,
            enabled=None,
            is_multi_spec=None,
            spec_name=None,
            spec_value=None,
            spec_name_2=None,
            spec_value_2=None,
            text_content=None,
            data_content=None,
            image="/static/uploads/images/demo.png",
            api_url=None,
            api_method=None,
            api_timeout=None,
            api_headers_json=None,
            api_params_json=None,
            yifan_user_id=None,
            yifan_user_key=None,
            yifan_goods_id=None,
            yifan_callback_url=None,
            yifan_require_account=None,
            generate_delivery_rule=False,
            server=None,
            token="test-token",
            json_output=False,
        )
        client = FakeCardClient("http://127.0.0.1:8090", "Bearer test-token")

        exit_code = handle_create_card(
            args,
            client_factory=FakeCardClientFactory(client),
            stdout=io.StringIO(),
            stderr=io.StringIO(),
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(client.upload_calls, [])
        self.assertEqual(client.create_card_calls[0]["image_url"], "/static/uploads/images/demo.png")

    def test_create_yifan_card_requires_mandatory_fields(self) -> None:
        args = Namespace(
            name="亦凡卡",
            card_type="yifan_api",
            description=None,
            delay_seconds=None,
            enabled=None,
            is_multi_spec=None,
            spec_name=None,
            spec_value=None,
            spec_name_2=None,
            spec_value_2=None,
            text_content=None,
            data_content=None,
            image=None,
            api_url=None,
            api_method=None,
            api_timeout=None,
            api_headers_json=None,
            api_params_json=None,
            yifan_user_id="merchant",
            yifan_user_key=None,
            yifan_goods_id=None,
            yifan_callback_url=None,
            yifan_require_account=None,
            generate_delivery_rule=False,
            server=None,
            token="test-token",
            json_output=False,
        )
        stderr = io.StringIO()

        exit_code = handle_create_card(
            args,
            client_factory=FakeCardClientFactory(FakeCardClient("http://127.0.0.1:8090", "Bearer test-token")),
            stdout=io.StringIO(),
            stderr=stderr,
        )

        self.assertEqual(exit_code, 1)
        self.assertIn("亦凡 API 商户 KEY不能为空", stderr.getvalue())

    def test_create_card_rejects_invalid_api_json(self) -> None:
        args = Namespace(
            name="API 卡",
            card_type="api",
            description=None,
            delay_seconds=None,
            enabled=None,
            is_multi_spec=None,
            spec_name=None,
            spec_value=None,
            spec_name_2=None,
            spec_value_2=None,
            text_content=None,
            data_content=None,
            image=None,
            api_url="https://example.com/api",
            api_method=None,
            api_timeout=None,
            api_headers_json="[]",
            api_params_json=None,
            yifan_user_id=None,
            yifan_user_key=None,
            yifan_goods_id=None,
            yifan_callback_url=None,
            yifan_require_account=None,
            generate_delivery_rule=False,
            server=None,
            token="test-token",
            json_output=False,
        )
        stderr = io.StringIO()

        exit_code = handle_create_card(
            args,
            client_factory=FakeCardClientFactory(FakeCardClient("http://127.0.0.1:8090", "Bearer test-token")),
            stdout=io.StringIO(),
            stderr=stderr,
        )

        self.assertEqual(exit_code, 1)
        self.assertIn("API 请求头必须是 JSON 对象", stderr.getvalue())

    def test_update_card_sends_only_changed_fields(self) -> None:
        args = Namespace(
            card_id=12,
            name=None,
            card_type=None,
            description="新描述",
            delay_seconds=None,
            enabled=None,
            is_multi_spec=None,
            spec_name=None,
            spec_value=None,
            spec_name_2=None,
            spec_value_2=None,
            text_content=None,
            data_content=None,
            image=None,
            api_url=None,
            api_method=None,
            api_timeout=None,
            api_headers_json=None,
            api_params_json=None,
            yifan_user_id=None,
            yifan_user_key=None,
            yifan_goods_id=None,
            yifan_callback_url=None,
            yifan_require_account=None,
            server=None,
            token="test-token",
            json_output=False,
        )
        client = FakeCardClient("http://127.0.0.1:8090", "Bearer test-token")
        client.cards_by_id[12] = {
            "id": 12,
            "name": "原卡片",
            "type": "text",
            "description": "旧描述",
            "enabled": True,
            "delay_seconds": 0,
            "is_multi_spec": False,
            "text_content": "hello",
        }

        exit_code = handle_update_card(
            args,
            client_factory=FakeCardClientFactory(client),
            stdout=io.StringIO(),
            stderr=io.StringIO(),
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(client.update_card_calls[0]["payload"], {"description": "新描述", "enabled": True})

    def test_update_disabled_card_preserves_disabled_state(self) -> None:
        args = Namespace(
            card_id=13,
            name=None,
            card_type=None,
            description="新描述",
            delay_seconds=None,
            enabled=None,
            is_multi_spec=None,
            spec_name=None,
            spec_value=None,
            spec_name_2=None,
            spec_value_2=None,
            text_content=None,
            data_content=None,
            image=None,
            api_url=None,
            api_method=None,
            api_timeout=None,
            api_headers_json=None,
            api_params_json=None,
            yifan_user_id=None,
            yifan_user_key=None,
            yifan_goods_id=None,
            yifan_callback_url=None,
            yifan_require_account=None,
            server=None,
            token="test-token",
            json_output=False,
        )
        client = FakeCardClient("http://127.0.0.1:8090", "Bearer test-token")
        client.cards_by_id[13] = {
            "id": 13,
            "name": "禁用卡片",
            "type": "text",
            "description": "旧描述",
            "enabled": False,
            "delay_seconds": 0,
            "is_multi_spec": False,
            "text_content": "hello",
        }

        exit_code = handle_update_card(
            args,
            client_factory=FakeCardClientFactory(client),
            stdout=io.StringIO(),
            stderr=io.StringIO(),
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(client.update_card_calls[0]["payload"], {"description": "新描述", "enabled": False})

    def test_update_card_rejects_cross_type_change(self) -> None:
        args = Namespace(
            card_id=7,
            name=None,
            card_type="image",
            description=None,
            delay_seconds=None,
            enabled=None,
            is_multi_spec=None,
            spec_name=None,
            spec_value=None,
            spec_name_2=None,
            spec_value_2=None,
            text_content=None,
            data_content=None,
            image=None,
            api_url=None,
            api_method=None,
            api_timeout=None,
            api_headers_json=None,
            api_params_json=None,
            yifan_user_id=None,
            yifan_user_key=None,
            yifan_goods_id=None,
            yifan_callback_url=None,
            yifan_require_account=None,
            server=None,
            token="test-token",
            json_output=False,
        )
        client = FakeCardClient("http://127.0.0.1:8090", "Bearer test-token")
        client.cards_by_id[7] = {
            "id": 7,
            "name": "文本卡",
            "type": "text",
            "enabled": True,
            "delay_seconds": 0,
            "is_multi_spec": False,
        }
        stderr = io.StringIO()

        exit_code = handle_update_card(
            args,
            client_factory=FakeCardClientFactory(client),
            stdout=io.StringIO(),
            stderr=stderr,
        )

        self.assertEqual(exit_code, 1)
        self.assertIn("不支持卡片跨类型更新", stderr.getvalue())

    def test_update_card_can_disable_multi_spec(self) -> None:
        args = Namespace(
            card_id=18,
            name=None,
            card_type=None,
            description=None,
            delay_seconds=None,
            enabled=None,
            is_multi_spec=False,
            spec_name=None,
            spec_value=None,
            spec_name_2=None,
            spec_value_2=None,
            text_content=None,
            data_content=None,
            image=None,
            api_url=None,
            api_method=None,
            api_timeout=None,
            api_headers_json=None,
            api_params_json=None,
            yifan_user_id=None,
            yifan_user_key=None,
            yifan_goods_id=None,
            yifan_callback_url=None,
            yifan_require_account=None,
            server=None,
            token="test-token",
            json_output=False,
        )
        client = FakeCardClient("http://127.0.0.1:8090", "Bearer test-token")
        client.cards_by_id[18] = {
            "id": 18,
            "name": "多规格卡",
            "type": "text",
            "enabled": True,
            "delay_seconds": 0,
            "is_multi_spec": True,
            "spec_name": "颜色",
            "spec_value": "红色",
            "spec_name_2": "容量",
            "spec_value_2": "256G",
        }

        exit_code = handle_update_card(
            args,
            client_factory=FakeCardClientFactory(client),
            stdout=io.StringIO(),
            stderr=io.StringIO(),
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            client.update_card_calls[0]["payload"],
            {
                "is_multi_spec": False,
                "spec_name": "",
                "spec_value": "",
                "spec_name_2": "",
                "spec_value_2": "",
                "enabled": True,
            },
        )

    def test_update_yifan_card_can_disable_require_account(self) -> None:
        args = Namespace(
            card_id=21,
            name=None,
            card_type=None,
            description=None,
            delay_seconds=None,
            enabled=None,
            is_multi_spec=None,
            spec_name=None,
            spec_value=None,
            spec_name_2=None,
            spec_value_2=None,
            text_content=None,
            data_content=None,
            image=None,
            api_url=None,
            api_method=None,
            api_timeout=None,
            api_headers_json=None,
            api_params_json=None,
            yifan_user_id=None,
            yifan_user_key=None,
            yifan_goods_id=None,
            yifan_callback_url=None,
            yifan_require_account=False,
            server=None,
            token="test-token",
            json_output=False,
        )
        client = FakeCardClient("http://127.0.0.1:8090", "Bearer test-token")
        client.cards_by_id[21] = {
            "id": 21,
            "name": "亦凡卡",
            "type": "yifan_api",
            "enabled": True,
            "delay_seconds": 0,
            "is_multi_spec": False,
            "api_config": {
                "user_id": "merchant",
                "user_key": "secret",
                "goods_id": "g-1",
                "callback_url": "https://example.com/callback",
                "require_account": True,
            },
        }

        exit_code = handle_update_card(
            args,
            client_factory=FakeCardClientFactory(client),
            stdout=io.StringIO(),
            stderr=io.StringIO(),
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            client.update_card_calls[0]["payload"]["api_config"]["require_account"],
            False,
        )

    def test_create_card_rejects_unsupported_api_method(self) -> None:
        args = Namespace(
            name="API 卡",
            card_type="api",
            description=None,
            delay_seconds=None,
            enabled=None,
            is_multi_spec=None,
            spec_name=None,
            spec_value=None,
            spec_name_2=None,
            spec_value_2=None,
            text_content=None,
            data_content=None,
            image=None,
            api_url="https://example.com/api",
            api_method="DELETE",
            api_timeout=None,
            api_headers_json=None,
            api_params_json=None,
            yifan_user_id=None,
            yifan_user_key=None,
            yifan_goods_id=None,
            yifan_callback_url=None,
            yifan_require_account=None,
            generate_delivery_rule=False,
            server=None,
            token="test-token",
            json_output=False,
        )
        stderr = io.StringIO()

        exit_code = handle_create_card(
            args,
            client_factory=FakeCardClientFactory(FakeCardClient("http://127.0.0.1:8090", "Bearer test-token")),
            stdout=io.StringIO(),
            stderr=stderr,
        )

        self.assertEqual(exit_code, 1)
        self.assertIn("API 请求方法仅支持 GET 或 POST", stderr.getvalue())

    def test_create_card_rejects_half_secondary_spec(self) -> None:
        args = Namespace(
            name="多规格卡",
            card_type="text",
            description=None,
            delay_seconds=None,
            enabled=None,
            is_multi_spec=True,
            spec_name="颜色",
            spec_value="红色",
            spec_name_2="容量",
            spec_value_2=None,
            text_content="hello",
            data_content=None,
            image=None,
            api_url=None,
            api_method=None,
            api_timeout=None,
            api_headers_json=None,
            api_params_json=None,
            yifan_user_id=None,
            yifan_user_key=None,
            yifan_goods_id=None,
            yifan_callback_url=None,
            yifan_require_account=None,
            generate_delivery_rule=False,
            server=None,
            token="test-token",
            json_output=False,
        )
        stderr = io.StringIO()

        exit_code = handle_create_card(
            args,
            client_factory=FakeCardClientFactory(FakeCardClient("http://127.0.0.1:8090", "Bearer test-token")),
            stdout=io.StringIO(),
            stderr=stderr,
        )

        self.assertEqual(exit_code, 1)
        self.assertIn("规格 2 必须同时提供名称和值", stderr.getvalue())

    def _create_temp_image(self) -> str:
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        handle.write(b"fake-image")
        handle.flush()
        handle.close()
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        return handle.name


if __name__ == "__main__":
    unittest.main()
