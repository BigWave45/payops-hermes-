"""Small, bounded HTTPS-only JSON client for provider APIs."""
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ALLOWED_HOSTS = {
    "api.paystack.co",
    "api.flutterwave.com",
    "idp.flutterwave.com",
    "developersandbox-api.flutterwave.com",
}


class ProviderError(RuntimeError):
    pass


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward credentials to a redirect target.
        return None


_OPENER = build_opener(_NoRedirect)
_MAX_RESPONSE_BYTES = 5 * 1024 * 1024


def _validate_url(url):
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in ALLOWED_HOSTS
        or parsed.port not in (None, 443)
        or parsed.username
        or parsed.password
    ):
        raise ProviderError("Provider endpoint is not permitted")
    return parsed


def _decode_response(response):
    raw = response.read(_MAX_RESPONSE_BYTES + 1)
    if len(raw) > _MAX_RESPONSE_BYTES:
        raise ProviderError("Provider response exceeded 5 MB limit")
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ProviderError("Provider returned invalid JSON") from None
    if not isinstance(data, dict):
        raise ProviderError("Unexpected provider response shape")
    return data


def get_json(base_url, path, token, params=None, headers=None):
    _validate_url(base_url)
    url = base_url.rstrip("/") + "/" + path.lstrip("/")
    if params:
        url += "?" + urlencode(params)
    request_headers = {
        "Authorization": "Bearer " + token,
        "Accept": "application/json",
        "User-Agent": "payops-hermes/0.1",
    }
    if headers:
        request_headers.update(headers)
    request = Request(url, headers=request_headers, method="GET")
    try:
        with _OPENER.open(request, timeout=20) as response:
            return _decode_response(response)
    except HTTPError as exc:
        detail = _safe_error_detail(exc)
        suffix = ": " + detail if detail else ""
        raise ProviderError("Provider returned HTTP %s%s" % (exc.code, suffix)) from None
    except (URLError, TimeoutError, OSError):
        raise ProviderError("Could not reach payment provider") from None


def _safe_error_detail(exc):
    """Expose only short provider error codes/messages, never raw response bodies."""
    try:
        payload = json.loads(exc.read(16 * 1024).decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return ""
    if not isinstance(payload, dict):
        return ""
    parts = []
    for key in ("code", "error", "message"):
        value = payload.get(key)
        if isinstance(value, str):
            cleaned = " ".join(ch for ch in value if ch.isprintable()).strip()
            if cleaned:
                parts.append(cleaned[:120])
    return "; ".join(parts)[:240]


def post_form_json(url, fields):
    parsed = _validate_url(url)
    if parsed.hostname != "idp.flutterwave.com":
        raise ProviderError("Provider endpoint is not permitted")
    body = urlencode(fields).encode("utf-8")
    request = Request(url, data=body, headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "User-Agent": "payops-hermes/0.1",
    }, method="POST")
    try:
        with _OPENER.open(request, timeout=20) as response:
            return _decode_response(response)
    except HTTPError as exc:
        raise ProviderError("Provider returned HTTP %s" % exc.code) from None
    except (URLError, TimeoutError, OSError):
        raise ProviderError("Could not reach payment provider") from None
