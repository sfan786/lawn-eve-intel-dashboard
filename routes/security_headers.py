"""
Browser security headers on every response.

Set in the app rather than nginx so they apply however the app is reached
(nginx, a different proxy, or `python app.py` locally) and are covered by tests.

* **frame-ancestors / X-Frame-Options** — the dashboard has write buttons
  (delete timer, clear entosis nodes, roster edits). Without these another
  site can frame it invisibly and click them with the visitor's session
  (clickjacking).
* **Content-Security-Policy** — no script source but our own bundle. Nothing
  here renders HTML from data today; the CSP is the backstop if that ever
  changes, which matters because the timer password sits in localStorage.
  The allowed hosts are exactly what the frontend loads: Google Fonts for
  the stylesheet and font files, images.evetech.net for portraits/logos.
  `style-src 'unsafe-inline'` is needed for React `style` props and costs
  little — inline style can't run script.
* **HSTS** only when the request actually arrived over HTTPS (ProxyFix makes
  that visible behind nginx), so plain-HTTP local work isn't pinned.
"""

from flask import request

CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data: https://images.evetech.net",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])

_STATIC_HEADERS = {
    "Content-Security-Policy": CSP,
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # Shares and the dashboard never need these; deny so an injected script
    # couldn't prompt for them under our origin either.
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
}

# No includeSubDomains: other services on sibling subdomains may still be HTTP.
HSTS = "max-age=31536000"


def apply_security_headers(app):
    @app.after_request
    def _set_security_headers(response):
        for name, value in _STATIC_HEADERS.items():
            response.headers.setdefault(name, value)
        if request.is_secure:
            response.headers.setdefault("Strict-Transport-Security", HSTS)
        return response

    return app
