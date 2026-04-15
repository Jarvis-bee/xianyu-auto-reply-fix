from __future__ import annotations

import importlib
import sys
import types
import unittest
from unittest.mock import AsyncMock, MagicMock

try:
    importlib.import_module("loguru")
except ModuleNotFoundError:
    fake_loguru = types.ModuleType("loguru")
    fake_loguru.logger = MagicMock()
    sys.modules.setdefault("loguru", fake_loguru)

from product_publisher import XianyuProductPublisher


class DummyConfig:
    def __init__(self, data: dict) -> None:
        self.data = data

    def get(self, *keys, default=None):
        value = self.data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value


class ProductPublisherSelectorTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.publisher = XianyuProductPublisher("cookie-a", "")
        self.publisher.config = DummyConfig(
            {
                "retry": {"selector_timeout": 1000},
                "logging": {"log_selector_search": True},
                "selectors": {
                    "price_input": {
                        "primary": 'input.ant-input[placeholder="0.00"]',
                        "match_index": 0,
                        "visible_only": True,
                    },
                    "original_price_input": {
                        "primary": 'input.ant-input[placeholder="0.00"]',
                        "match_index": 1,
                        "visible_only": True,
                    },
                },
            }
        )
        self.publisher.page = MagicMock()

    async def test_price_input_uses_first_visible_match(self) -> None:
        first_visible = MagicMock()
        hidden = MagicMock()
        second_visible = MagicMock()

        first_visible.is_visible = AsyncMock(return_value=True)
        hidden.is_visible = AsyncMock(return_value=False)
        second_visible.is_visible = AsyncMock(return_value=True)

        self.publisher.page.wait_for_selector = AsyncMock(return_value=first_visible)
        self.publisher.page.query_selector_all = AsyncMock(
            return_value=[first_visible, hidden, second_visible]
        )

        found = await self.publisher._find_element_with_fallback("price_input")

        self.assertIs(found, first_visible)
        self.publisher.page.query_selector_all.assert_awaited_once_with(
            'input.ant-input[placeholder="0.00"]'
        )

    async def test_original_price_input_uses_second_visible_match(self) -> None:
        first_visible = MagicMock()
        hidden = MagicMock()
        second_visible = MagicMock()

        first_visible.is_visible = AsyncMock(return_value=True)
        hidden.is_visible = AsyncMock(return_value=False)
        second_visible.is_visible = AsyncMock(return_value=True)

        self.publisher.page.wait_for_selector = AsyncMock(return_value=first_visible)
        self.publisher.page.query_selector_all = AsyncMock(
            return_value=[first_visible, hidden, second_visible]
        )

        found = await self.publisher._find_element_with_fallback("original_price_input")

        self.assertIs(found, second_visible)
        self.publisher.page.query_selector_all.assert_awaited_once_with(
            'input.ant-input[placeholder="0.00"]'
        )


if __name__ == "__main__":
    unittest.main()
