from __future__ import annotations

import argparse
import sys
from typing import Any, TextIO

from xianyu_cli.api.client import APIClient, APIClientError
from xianyu_cli.cli_common import (
    CLIUsageError,
    emit_fatal_error,
    is_interactive_terminal,
    optional_text,
    require_text,
    resolve_server,
    resolve_token,
    validate_positive_int,
)
from xianyu_cli.interactive.cards import build_card_choices, prompt_card_selection
from xianyu_cli.output import (
    print_delivery_rule_detail,
    print_delivery_rule_list,
    print_json,
    print_message,
    print_stats,
)


def register(subparsers: Any) -> None:
    parser = subparsers.add_parser("delivery-rule", help="管理自动发货规则")
    parser.set_defaults(handler=_make_help_handler(parser))
    rule_subparsers = parser.add_subparsers(dest="rule_command", metavar="<subcommand>")

    list_parser = rule_subparsers.add_parser("list", help="列出发货规则")
    _add_runtime_args(list_parser)
    list_parser.set_defaults(handler=handle_list_delivery_rules)

    get_parser = rule_subparsers.add_parser("get", help="查看发货规则详情")
    get_parser.add_argument("rule_id", type=int, help="规则 ID")
    _add_runtime_args(get_parser)
    get_parser.set_defaults(handler=handle_get_delivery_rule)

    create_parser = rule_subparsers.add_parser("create", help="创建发货规则")
    _add_rule_arguments(create_parser)
    _add_runtime_args(create_parser)
    create_parser.set_defaults(handler=handle_create_delivery_rule)

    update_parser = rule_subparsers.add_parser("update", help="更新发货规则")
    update_parser.add_argument("rule_id", type=int, help="规则 ID")
    _add_rule_arguments(update_parser, create_mode=False)
    _add_runtime_args(update_parser)
    update_parser.set_defaults(handler=handle_update_delivery_rule)

    delete_parser = rule_subparsers.add_parser("delete", help="删除发货规则")
    delete_parser.add_argument("rule_id", type=int, help="规则 ID")
    _add_runtime_args(delete_parser)
    delete_parser.set_defaults(handler=handle_delete_delivery_rule)

    stats_parser = rule_subparsers.add_parser("stats", help="查看发货统计")
    _add_runtime_args(stats_parser)
    stats_parser.set_defaults(handler=handle_delivery_rule_stats)


def handle_list_delivery_rules(
    args: argparse.Namespace,
    *,
    client_factory: type[APIClient] = APIClient,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    try:
        with client_factory(resolve_server(args.server), resolve_token(args.token)) as client:
            client.check_health()
            rules = client.list_delivery_rules()
    except (CLIUsageError, APIClientError, ValueError) as exc:
        return emit_fatal_error(str(exc), json_output=bool(args.json_output), stdout=stdout, stderr=stderr)

    if args.json_output:
        print_json(rules, stdout)
    else:
        print_delivery_rule_list(rules, stdout)
    return 0


def handle_get_delivery_rule(
    args: argparse.Namespace,
    *,
    client_factory: type[APIClient] = APIClient,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    try:
        with client_factory(resolve_server(args.server), resolve_token(args.token)) as client:
            client.check_health()
            rule = client.get_delivery_rule(args.rule_id)
    except (CLIUsageError, APIClientError, ValueError) as exc:
        return emit_fatal_error(str(exc), json_output=bool(args.json_output), stdout=stdout, stderr=stderr)

    if args.json_output:
        print_json(rule, stdout)
    else:
        print_delivery_rule_detail(rule, stdout)
    return 0


def handle_create_delivery_rule(
    args: argparse.Namespace,
    *,
    client_factory: type[APIClient] = APIClient,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    try:
        with client_factory(resolve_server(args.server), resolve_token(args.token)) as client:
            client.check_health()
            payload = _build_create_payload(args, client, stdin=stdin, prompt_stream=stderr)
            response = client.create_delivery_rule(payload)
    except (CLIUsageError, APIClientError, ValueError) as exc:
        return emit_fatal_error(str(exc), json_output=bool(args.json_output), stdout=stdout, stderr=stderr)

    if args.json_output:
        print_json(response, stdout)
    else:
        print_message(str(response.get("message") or "发货规则创建成功"), stdout, item_id=response.get("id"))
    return 0


def handle_update_delivery_rule(
    args: argparse.Namespace,
    *,
    client_factory: type[APIClient] = APIClient,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    try:
        with client_factory(resolve_server(args.server), resolve_token(args.token)) as client:
            client.check_health()
            existing_rule = client.get_delivery_rule(args.rule_id)
            payload = _build_update_payload(args, existing_rule)
            response = client.update_delivery_rule(args.rule_id, payload)
    except (CLIUsageError, APIClientError, ValueError) as exc:
        return emit_fatal_error(str(exc), json_output=bool(args.json_output), stdout=stdout, stderr=stderr)

    if args.json_output:
        print_json(response, stdout)
    else:
        print_message(str(response.get("message") or "发货规则更新成功"), stdout, item_id=args.rule_id)
    return 0


def handle_delete_delivery_rule(
    args: argparse.Namespace,
    *,
    client_factory: type[APIClient] = APIClient,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    try:
        with client_factory(resolve_server(args.server), resolve_token(args.token)) as client:
            client.check_health()
            response = client.delete_delivery_rule(args.rule_id)
    except (CLIUsageError, APIClientError, ValueError) as exc:
        return emit_fatal_error(str(exc), json_output=bool(args.json_output), stdout=stdout, stderr=stderr)

    if args.json_output:
        print_json(response, stdout)
    else:
        print_message(str(response.get("message") or "发货规则删除成功"), stdout, item_id=args.rule_id)
    return 0


def handle_delivery_rule_stats(
    args: argparse.Namespace,
    *,
    client_factory: type[APIClient] = APIClient,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    try:
        with client_factory(resolve_server(args.server), resolve_token(args.token)) as client:
            client.check_health()
            stats = client.get_delivery_rule_stats()
    except (CLIUsageError, APIClientError, ValueError) as exc:
        return emit_fatal_error(str(exc), json_output=bool(args.json_output), stdout=stdout, stderr=stderr)

    if args.json_output:
        print_json(stats, stdout)
    else:
        print_stats(stats, stdout)
    return 0


def _add_rule_arguments(parser: argparse.ArgumentParser, *, create_mode: bool = True) -> None:
    parser.add_argument("--keyword", required=create_mode, help="匹配商品关键字")
    parser.add_argument("--card-id", type=int, help="关联卡片 ID")
    parser.add_argument("--delivery-count", help="发货数量，默认 1")
    parser.add_argument("--description", help="规则描述")
    state_group = parser.add_mutually_exclusive_group()
    state_group.add_argument("--enabled", dest="enabled", action="store_true", help="启用规则")
    state_group.add_argument("--disabled", dest="enabled", action="store_false", help="禁用规则")
    parser.set_defaults(enabled=None)


def _add_runtime_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--server", help="服务地址，默认读取 XIANYU_SERVER 或 http://127.0.0.1:8090")
    parser.add_argument("--token", help="后台 Bearer token，默认读取 XIANYU_TOKEN")
    parser.add_argument("--json", action="store_true", dest="json_output", help="以 JSON 输出结果")


def _build_create_payload(
    args: argparse.Namespace,
    client: APIClient,
    *,
    stdin: TextIO,
    prompt_stream: TextIO,
) -> dict[str, Any]:
    return {
        "keyword": require_text(args.keyword, field_name="商品关键字"),
        "card_id": _resolve_card_id_for_create(args.card_id, client, stdin=stdin, prompt_stream=prompt_stream),
        "delivery_count": validate_positive_int(args.delivery_count or 1, field_name="发货数量"),
        "enabled": True if args.enabled is None else bool(args.enabled),
        "description": optional_text(args.description),
    }


def _build_update_payload(args: argparse.Namespace, existing_rule: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if args.keyword is not None:
        payload["keyword"] = require_text(args.keyword, field_name="商品关键字")
    if args.card_id is not None:
        payload["card_id"] = int(args.card_id)
    if args.delivery_count is not None:
        payload["delivery_count"] = validate_positive_int(args.delivery_count, field_name="发货数量")
    if args.description is not None:
        payload["description"] = optional_text(args.description)
    if args.enabled is not None:
        payload["enabled"] = bool(args.enabled)

    if not payload:
        raise CLIUsageError("没有可更新的内容")

    if "delivery_count" not in payload:
        payload["delivery_count"] = validate_positive_int(
            existing_rule.get("delivery_count") or 1,
            field_name="发货数量",
        )
    if "enabled" not in payload:
        payload["enabled"] = bool(existing_rule.get("enabled"))

    return payload


def _resolve_card_id_for_create(
    raw_card_id: int | None,
    client: APIClient,
    *,
    stdin: TextIO,
    prompt_stream: TextIO,
) -> int:
    if raw_card_id is not None:
        return int(raw_card_id)

    if not is_interactive_terminal(stdin):
        raise CLIUsageError("未提供 --card-id，且当前不是交互终端")

    choices = build_card_choices(client.list_cards(), enabled_only=True)
    if not choices:
        raise CLIUsageError("当前没有可用的启用卡片")

    return prompt_card_selection(choices, stdin=stdin, stdout=prompt_stream)


def _make_help_handler(parser: argparse.ArgumentParser):
    def _handler(_: argparse.Namespace) -> int:
        parser.print_help()
        return 1

    return _handler
