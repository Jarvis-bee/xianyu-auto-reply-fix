from __future__ import annotations

import json
import unittest
from urllib.parse import parse_qs, urlparse

from utils.publish_request_rewriter import rewrite_publish_request_quantity


class PublishRequestRewriterTests(unittest.TestCase):
    def test_rewrite_publish_request_updates_quantity_and_sign(self) -> None:
        original_url = (
            "https://h5api.m.goofish.com/h5/mtop.idle.pc.idleitem.publish/1.0/"
            "?jsv=2.7.2&appKey=34839810&t=1710000000000&sign=oldsign&type=originaljson"
        )
        original_payload = {
            "title": "测试商品",
            "quantity": "1",
            "priceInCent": "100",
        }
        original_post_data = (
            "jsv=2.7.2&appKey=34839810"
            f"&data={json.dumps(original_payload, ensure_ascii=False)}"
        )

        rewritten_url, rewritten_post_data = rewrite_publish_request_quantity(
            original_url,
            original_post_data,
            7,
            token="token123",
        )

        rewritten_query = parse_qs(urlparse(rewritten_url).query)
        rewritten_body = parse_qs(rewritten_post_data)
        rewritten_payload = json.loads(rewritten_body["data"][0])

        self.assertEqual(rewritten_payload["quantity"], "7")
        self.assertEqual(rewritten_payload["title"], "测试商品")
        self.assertNotEqual(rewritten_query["sign"][0], "oldsign")

    def test_rewrite_publish_request_rejects_non_positive_quantity(self) -> None:
        with self.assertRaises(ValueError):
            rewrite_publish_request_quantity(
                "https://example.com/h5/mtop.idle.pc.idleitem.publish/1.0/?t=1&sign=abc",
                "data={}",
                0,
                token="token123",
            )


if __name__ == "__main__":
    unittest.main()
