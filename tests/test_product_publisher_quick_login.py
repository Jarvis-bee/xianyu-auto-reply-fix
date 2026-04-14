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

from product_publisher import ProductInfo, XianyuProductPublisher


class QuickLoginModalTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.publisher = XianyuProductPublisher("cookie-a", "")
        self.publisher.page = MagicMock()
        self.publisher.page.goto = AsyncMock()
        self.publisher._emit_progress = MagicMock()
        self.publisher.take_screenshot = AsyncMock()
        self.publisher._simulate_page_scroll = AsyncMock()
        self.publisher._upload_images = AsyncMock(return_value=True)
        self.publisher._fill_product_info = AsyncMock(return_value=True)
        self.publisher._click_publish = AsyncMock(return_value=True)
        self.publisher._verify_publish_success = AsyncMock(return_value=(True, "1001", "https://example.com/item/1001"))
        self.publisher._remove_default_specs = AsyncMock()
        self.publisher.config.reload_if_changed = MagicMock()
        self.publisher._retry_with_backoff = AsyncMock()
        self.publisher._check_captcha = AsyncMock(return_value=False)

    async def test_click_quick_login_control_only_searches_modal_container(self) -> None:
        modal_container = MagicMock()
        modal_frame = MagicMock()
        target_element = MagicMock()
        target_element.is_visible = AsyncMock(return_value=True)
        target_element.click = AsyncMock()
        modal_container.query_selector = AsyncMock(return_value=target_element)
        modal_frame.query_selector = AsyncMock(side_effect=AssertionError("不应在整个 frame 内查找关闭控件"))
        self.publisher._quick_login_modal_still_visible = AsyncMock(return_value=False)

        success = await self.publisher._click_quick_login_control(
            {"frame": modal_frame, "container": modal_container},
            'text="×"',
            success_log="尝试关闭弹窗",
        )

        self.assertTrue(success)
        modal_container.query_selector.assert_awaited_once_with('text="×"')
        modal_frame.query_selector.assert_not_called()
        target_element.click.assert_awaited_once_with(force=True)

    async def test_quick_login_modal_visibility_only_checks_modal_container(self) -> None:
        modal_container = MagicMock()
        modal_frame = MagicMock()
        marker_element = MagicMock()
        marker_element.is_visible = AsyncMock(return_value=True)
        modal_container.query_selector = AsyncMock(return_value=marker_element)
        modal_frame.query_selector = AsyncMock(side_effect=AssertionError("不应在整个 frame 内判断弹窗是否消失"))

        visible = await self.publisher._quick_login_modal_still_visible(
            {"frame": modal_frame, "container": modal_container}
        )

        self.assertTrue(visible)
        modal_container.query_selector.assert_awaited_once_with('text="手机扫码安全登录"')
        modal_frame.query_selector.assert_not_called()

    async def test_publish_stops_when_quick_login_modal_stays_visible(self) -> None:
        quick_login_modal = {"frame": MagicMock(), "container": MagicMock()}
        self.publisher._find_quick_login_modal_context = AsyncMock(return_value=quick_login_modal)
        self.publisher._dismiss_quick_login_modal = AsyncMock(return_value=False)
        self.publisher._quick_login_modal_still_visible = AsyncMock(return_value=True)

        success, product_id, product_url = await self.publisher.publish_product(
            ProductInfo(
                title="测试商品",
                description="测试描述",
                price=10.0,
                images=["/tmp/test.png"],
            )
        )

        self.assertEqual((success, product_id, product_url), (False, None, None))
        self.publisher._retry_with_backoff.assert_awaited_once_with(
            self.publisher.page.goto,
            url=self.publisher.PUBLISH_URL,
            wait_until='domcontentloaded'
        )
        self.publisher._dismiss_quick_login_modal.assert_awaited_once_with(quick_login_modal)
        self.publisher._quick_login_modal_still_visible.assert_awaited_once_with(quick_login_modal)
        self.publisher._simulate_page_scroll.assert_not_awaited()
        self.publisher.take_screenshot.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
