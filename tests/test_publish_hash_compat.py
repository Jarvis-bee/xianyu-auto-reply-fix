from __future__ import annotations

import ast
import hashlib
import json
import unittest
from pathlib import Path
from typing import List, Optional


def _load_build_publish_product_hash():
    source_path = Path(__file__).resolve().parent.parent / "reply_server.py"
    source = source_path.read_text(encoding="utf-8")
    module = ast.parse(source, filename=str(source_path))

    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_build_publish_product_hash":
            isolated_module = ast.Module(body=[node], type_ignores=[])
            namespace = {
                "hashlib": hashlib,
                "json": json,
                "List": List,
                "Optional": Optional,
            }
            exec(compile(isolated_module, filename=str(source_path), mode="exec"), namespace)
            return namespace["_build_publish_product_hash"]

    raise AssertionError("未找到 _build_publish_product_hash")


class PublishHashCompatibilityTests(unittest.TestCase):
    def test_quantity_one_matches_legacy_hash_without_quantity(self) -> None:
        build_hash = _load_build_publish_product_hash()

        legacy_hash = build_hash(
            "测试商品",
            10.0,
            "测试描述",
            ["image-a", "image-b"],
            original_price=20.0,
            category="数码产品/手机/苹果",
            location="北京市/朝阳区",
            quantity=None,
        )
        explicit_one_hash = build_hash(
            "测试商品",
            10.0,
            "测试描述",
            ["image-a", "image-b"],
            original_price=20.0,
            category="数码产品/手机/苹果",
            location="北京市/朝阳区",
            quantity=1,
        )
        quantity_five_hash = build_hash(
            "测试商品",
            10.0,
            "测试描述",
            ["image-a", "image-b"],
            original_price=20.0,
            category="数码产品/手机/苹果",
            location="北京市/朝阳区",
            quantity=5,
        )

        self.assertEqual(legacy_hash, explicit_one_hash)
        self.assertNotEqual(legacy_hash, quantity_five_hash)


if __name__ == "__main__":
    unittest.main()
