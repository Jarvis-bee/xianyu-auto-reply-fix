from __future__ import annotations

import hashlib
import json
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

PUBLISH_API_PATH = "/h5/mtop.idle.pc.idleitem.publish/1.0/"
_MTOP_APP_KEY = "34839810"


def rewrite_publish_request_quantity(request_url: str, post_data: str, quantity: int, *, token: str) -> tuple[str, str]:
    """重写闲鱼发布请求，将无规格商品库存写入 quantity 并重算签名。"""
    normalized_quantity = int(quantity)
    if normalized_quantity < 1:
        raise ValueError("quantity 必须大于 0")

    normalized_token = str(token or "").strip()
    if not normalized_token:
        raise ValueError("缺少 _m_h5_tk token，无法重算发布签名")

    form_pairs = parse_qsl(str(post_data or ""), keep_blank_values=True)
    if not form_pairs:
        raise ValueError("发布请求缺少表单数据")

    form_data = dict(form_pairs)
    raw_data = form_data.get("data")
    if not raw_data:
        raise ValueError("发布请求缺少 data 参数")

    payload = json.loads(raw_data)
    payload["quantity"] = str(normalized_quantity)
    rewritten_data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    rewritten_pairs = _replace_key_in_pairs(form_pairs, "data", rewritten_data)
    request_t = _get_query_param(request_url, "t")
    if not request_t:
        raise ValueError("发布请求缺少 t 参数")

    rewritten_sign = _generate_sign(request_t, normalized_token, rewritten_data)
    rewritten_url = _replace_query_param(request_url, "sign", rewritten_sign)
    rewritten_post_data = urlencode(rewritten_pairs)
    return rewritten_url, rewritten_post_data


def _generate_sign(t_value: str, token: str, data: str) -> str:
    digest = hashlib.md5()
    digest.update(f"{token}&{t_value}&{_MTOP_APP_KEY}&{data}".encode("utf-8"))
    return digest.hexdigest()


def _replace_key_in_pairs(pairs: list[tuple[str, str]], key: str, value: str) -> list[tuple[str, str]]:
    replaced = False
    rewritten_pairs: list[tuple[str, str]] = []
    for current_key, current_value in pairs:
        if current_key == key:
            rewritten_pairs.append((current_key, value))
            replaced = True
        else:
            rewritten_pairs.append((current_key, current_value))

    if not replaced:
        rewritten_pairs.append((key, value))
    return rewritten_pairs


def _get_query_param(request_url: str, key: str) -> str | None:
    for current_key, current_value in parse_qsl(urlsplit(request_url).query, keep_blank_values=True):
        if current_key == key:
            return current_value
    return None


def _replace_query_param(request_url: str, key: str, value: str) -> str:
    parts = urlsplit(request_url)
    query_pairs = parse_qsl(parts.query, keep_blank_values=True)
    rewritten_pairs = _replace_key_in_pairs(query_pairs, key, value)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(rewritten_pairs), parts.fragment))
