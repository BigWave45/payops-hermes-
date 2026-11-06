"""Small, bounded HTTPS-only JSON client for provider APIs."""
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ALLOWED_HOSTS = {"api.paystack.co", "api.flutterwave.com"}

class ProviderError(RuntimeError):
    pass

class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward a bearer token to a redirect target.
        return None

_OPENER = build_opener(_NoRedirect)

def get_json(base_url, path, token, params=None):
    parsed = urlsplit(base_url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS or parsed.port not in (None, 443):
        raise ProviderError("Provider endpoint is not permitted")
    if parsed.username or parsed.password:
        raise ProviderError("Provider endpoint is not permitted")
    url = base_url.rstrip("/") + "/" + path.lstrip("/")
    if params:
        url += "?" + urlencode(params)
    request = Request(url, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/json",
        "User-Agent": "payops-hermes/0.1",
    }, method="GET")
    try:
        with _OPENER.open(request, timeout=20) as response:
            raw = response.read(5 * 1024 * 1024 + 1)
            if len(raw) > 5 * 1024 * 1024:
                raise ProviderError("Provider response exceeded 5 MB limit")
            data = json.loads(raw.decode("utf-8"))
    except HTTPError as exc:
        raise ProviderError("Provider returned HTTP %s" % exc.code) from None
    except (URLError, TimeoutError, OSError):
        raise ProviderError("Could not reach payment provider") from None
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ProviderError("Provider returned invalid JSON") from None
    if not isinstance(data, dict):
        raise ProviderError("Unexpected provider response shape")
    return data
