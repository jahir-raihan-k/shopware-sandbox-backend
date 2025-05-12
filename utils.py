import re
import hmac, hashlib
from fastapi import Request, HTTPException


def generate_hmac(data: bytes, key: str) -> str:
    """Return hex‑encoded HMAC‑SHA256 of data using key."""
    return hmac.new(key.encode('utf-8'), data, hashlib.sha256).hexdigest()


def verify_hmac(received_sig: str, data: bytes, key: str):
    """Timing‑safe comparison of received_sig vs HMAC(data, key)."""
    expected = generate_hmac(data, key)
    if not hmac.compare_digest(expected, received_sig):
        raise HTTPException(status_code=401, detail="Invalid signature")


async def verify_header_signature(request: Request, shop_secret: str, header_name: str):
    """Verify signature from header (used in /registration)."""

    raw_qs = request.scope["query_string"]  # bytes
    sig = request.headers.get(header_name)
    if sig is None:
        raise HTTPException(400, detail=f"Missing header: {header_name}")
    verify_hmac(sig, raw_qs, shop_secret)


async def verify_query_param_signature(
    request: Request,
    shop_secret: str,
    param_name: str = "shopware-shop-signature"
):
    """
    Verifies Shopware signature using the raw query string as-is,
    stripping out the signature param but preserving everything else.
    """

    raw_query = request.url.query  # str (already decoded from bytes)
    sig = request.query_params.get(param_name)
    if not sig:
        raise HTTPException(400, detail=f"Missing query param: {param_name}")

    # Remove the param from the raw string using pattern
    # Safe to remove using this exact pattern: "&key=value" or "key=value"
    pattern = rf"(&?{param_name}={re.escape(sig)})"
    cleaned_query = re.sub(pattern, "", raw_query)

    # cleaning up any leading & signs
    if cleaned_query.startswith("&"):
        cleaned_query = cleaned_query[1:]

    # Validate signature against  cleaned original query string
    verify_hmac(sig, cleaned_query.encode(), shop_secret)


async def verify_body_signature(request: Request, shop_secret: str,  header_name: str):
    """
    For POST/webhooks/confirmation: verify HMAC of raw body.
    Shopware sends header 'shopware-shop-signature'.
    """

    raw_body = await request.body()  # bytes
    sig = request.headers.get(header_name)
    if sig is None:
        raise HTTPException(400, detail=f"Missing header {header_name}")

    verify_hmac(sig, raw_body, shop_secret)
