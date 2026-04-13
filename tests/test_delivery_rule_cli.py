from __future__ import annotations

import contextlib
import io
import json
import unittest
from argparse import Namespace

from xianyu_cli.commands.delivery_rule import handle_create_delivery_rule, handle_update_delivery_rule
from xianyu_cli.interactive.cards import build_card_choices, parse_card_selection
from xianyu_cli.main import build_parser


class FakeStdin(io.StringIO):
    def __init__(self, value: str, *, interactive: bool) -> None:
        super().__init__(value)
        self._interactive = interactive

    def isatty(self) -> bool:
        return self._interactive


class FakeDeliveryRuleClient:
    def __init__(self, server: str, token: str) -> None:
        self.server = server
        self.token = token
        self.health_checked = False
        self.cards: list[dict] = []
        self.create_calls: list[dict] = []
        self.update_calls: list[dict] = []
        self.rules_by_id: dict[int, dict] = {}

    def __enter__(self) -> "FakeDeliveryRuleClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def check_health(self) -> dict:
        self.health_checked = True
        return {"status": "healthy"}

    def list_cards(self) -> list[dict]:
        return list(self.cards)

    def create_delivery_rule(self, payload: dict) -> dict:
        self.create_calls.append(payload)
        return {"id": 55, "message": "发货规则创建成功"}

    def get_delivery_rule(self, rule_id: int) -> dict:
        return dict(self.rules_by_id[rule_id])

    def update_delivery_rule(self, rule_id: int, payload: dict) -> dict:
        self.update_calls.append({"rule_id": rule_id, "payload": payload})
        return {"message": "发货规则更新成功"}


class FakeDeliveryRuleClientFactory:
    def __init__(self, client: FakeDeliveryRuleClient) -> None:
        self.client = client

    def __call__(self, server: str, token: str) -> FakeDeliveryRuleClient:
        self.client.server = server
        self.client.token = token
        return self.client


class DeliveryRuleCLITests(unittest.TestCase):
    def test_delivery_rule_help_works(self) -> None:
        parser = build_parser()
        stdout = io.StringIO()
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stdout(stdout):
                parser.parse_args(["delivery-rule", "create", "--help"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn("--card-id", stdout.getvalue())

    def test_parse_card_selection_returns_single_index(self) -> None:
        self.assertEqual(parse_card_selection("2", 3), 2)

    def test_build_card_choices_filters_disabled(self) -> None:
        raw = [
            {"id": 1, "name": "A", "enabled": True, "type": "text"},
            {"id": 2, "name": "B", "enabled": False, "type": "text"},
        ]
        choices = build_card_choices(raw, enabled_only=True)
        self.assertEqual([choice.card_id for choice in choices], [1])

    def test_create_rule_requires_card_id_in_non_interactive_mode(self) -> None:
        args = Namespace(
            keyword="商品关键字",
            card_id=None,
            delivery_count=None,
            description=None,
            enabled=None,
            server=None,
            token="test-token",
            json_output=False,
        )
        stderr = io.StringIO()

        exit_code = handle_create_delivery_rule(
            args,
            client_factory=FakeDeliveryRuleClientFactory(FakeDeliveryRuleClient("http://127.0.0.1:8090", "Bearer test-token")),
            stdin=FakeStdin("", interactive=False),
            stdout=io.StringIO(),
            stderr=stderr,
        )

        self.assertEqual(exit_code, 1)
        self.assertIn("未提供 --card-id", stderr.getvalue())

    def test_create_rule_prompts_for_enabled_card_and_keeps_stdout_json_clean(self) -> None:
        args = Namespace(
            keyword="商品关键字",
            card_id=None,
            delivery_count="2",
            description="测试规则",
            enabled=None,
            server=None,
            token="test-token",
            json_output=True,
        )
        client = FakeDeliveryRuleClient("http://127.0.0.1:8090", "Bearer test-token")
        client.cards = [
            {"id": 11, "name": "文本卡", "enabled": True, "type": "text"},
            {"id": 22, "name": "禁用卡", "enabled": False, "type": "data"},
        ]
        stdout = io.StringIO()
        stderr = io.StringIO()

        exit_code = handle_create_delivery_rule(
            args,
            client_factory=FakeDeliveryRuleClientFactory(client),
            stdin=FakeStdin("1\n", interactive=True),
            stdout=stdout,
            stderr=stderr,
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(client.create_calls[0]["card_id"], 11)
        self.assertNotIn("可用卡片", stdout.getvalue())
        self.assertIn("可用卡片", stderr.getvalue())
        self.assertEqual(json.loads(stdout.getvalue())["id"], 55)

    def test_update_rule_without_card_id_does_not_prompt(self) -> None:
        args = Namespace(
            rule_id=9,
            keyword=None,
            card_id=None,
            delivery_count="3",
            description=None,
            enabled=None,
            server=None,
            token="test-token",
            json_output=False,
        )
        client = FakeDeliveryRuleClient("http://127.0.0.1:8090", "Bearer test-token")
        client.rules_by_id[9] = {
            "id": 9,
            "keyword": "旧关键字",
            "card_id": 11,
            "delivery_count": 2,
            "enabled": False,
            "description": "旧描述",
        }

        exit_code = handle_update_delivery_rule(
            args,
            client_factory=FakeDeliveryRuleClientFactory(client),
            stdout=io.StringIO(),
            stderr=io.StringIO(),
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(client.update_calls[0]["payload"], {"delivery_count": 3, "enabled": False})

    def test_update_rule_preserves_existing_count_and_enabled(self) -> None:
        args = Namespace(
            rule_id=10,
            keyword=None,
            card_id=None,
            delivery_count=None,
            description="新描述",
            enabled=None,
            server=None,
            token="test-token",
            json_output=False,
        )
        client = FakeDeliveryRuleClient("http://127.0.0.1:8090", "Bearer test-token")
        client.rules_by_id[10] = {
            "id": 10,
            "keyword": "旧关键字",
            "card_id": 12,
            "delivery_count": 5,
            "enabled": False,
            "description": "旧描述",
        }

        exit_code = handle_update_delivery_rule(
            args,
            client_factory=FakeDeliveryRuleClientFactory(client),
            stdout=io.StringIO(),
            stderr=io.StringIO(),
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            client.update_calls[0]["payload"],
            {"description": "新描述", "delivery_count": 5, "enabled": False},
        )

    def test_create_rule_rejects_invalid_delivery_count(self) -> None:
        args = Namespace(
            keyword="商品关键字",
            card_id=11,
            delivery_count="0",
            description=None,
            enabled=None,
            server=None,
            token="test-token",
            json_output=False,
        )
        stderr = io.StringIO()

        exit_code = handle_create_delivery_rule(
            args,
            client_factory=FakeDeliveryRuleClientFactory(FakeDeliveryRuleClient("http://127.0.0.1:8090", "Bearer test-token")),
            stdin=FakeStdin("", interactive=False),
            stdout=io.StringIO(),
            stderr=stderr,
        )

        self.assertEqual(exit_code, 1)
        self.assertIn("发货数量必须大于等于 1", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
