"""Security headers middleware.

Adds OWASP-recommended security headers to all responses.
CSP is intentionally omitted — this backend serves JSON, not HTML.
CSP should be configured on the frontend hosting layer.
"""

from starlette.requests import Request
from starlette.responses import Response


async def security_headers_middleware(request: Request, call_next) -> Response:
    """Add security headers to every response."""
    response: Response = await call_next(request)

    response.headers["Strict-Transport-Security"] = (
        "max-age=63072000; includeSubDomains; preload"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "geolocation=(), camera=(), microphone=(), payment=()"
    )

    # Remove server fingerprinting headers
    if "Server" in response.headers:
        del response.headers["Server"]
    if "X-Powered-By" in response.headers:
        del response.headers["X-Powered-By"]

    return response
