"""
Главный файл для запуска FastAPI веб-сервера
"""
import uvicorn
import logging
import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from shared.config import config
from shared.services.upload_storage import ensure_upload_dir
from web.api import contests, admin, billing, publish, youtube_auth, ws, analytics, tiktok_auth, instagram_auth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Contest Bot WebApp")

# Директории
static_dir = os.path.join(os.path.dirname(__file__), "static")
uploads_dir = ensure_upload_dir()
dist_dir = os.path.join(static_dir, "dist")

# Монтируем загрузки
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# Монтируем ассеты билда
if os.path.exists(os.path.join(dist_dir, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(dist_dir, "assets")), name="assets")

# Подключение API роутеров
app.include_router(contests.router)
app.include_router(admin.router)
app.include_router(billing.router)
app.include_router(publish.router)
app.include_router(youtube_auth.router)
app.include_router(tiktok_auth.router)
app.include_router(instagram_auth.router)
app.include_router(ws.router)
app.include_router(analytics.router)

LEGAL_PAGE_STYLE = """
body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: #0f1720;
    color: #eef4fb;
    line-height: 1.6;
}
main {
    max-width: 820px;
    margin: 0 auto;
    padding: 48px 20px 72px;
}
a { color: #66b7ff; }
h1 { font-size: 34px; line-height: 1.15; margin: 0 0 16px; }
h2 { font-size: 20px; margin-top: 34px; }
p, li { color: #c8d4df; }
.muted { color: #8fa1b2; }
"""


def legal_page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>{LEGAL_PAGE_STYLE}</style>
</head>
<body>
  <main>{body}</main>
</body>
</html>"""
    )


@app.get("/about", response_class=HTMLResponse)
async def about():
    """Public application information for OAuth verification."""
    return legal_page(
        "TelOnyx Contest Bot",
        """
<h1>TelOnyx Contest Bot</h1>
<p>TelOnyx Contest Bot is a Telegram Mini App for creating and managing community contests in Telegram channels, groups, and forum topics.</p>
<p>The app helps participants register for contests and allows contest organizers to verify required participation conditions, including Telegram membership and optional YouTube channel subscription checks.</p>
<h2>How YouTube access is used</h2>
<p>When a contest requires a YouTube subscription, a participant can sign in with Google so the app can verify whether that participant is subscribed to the required YouTube channel. The app does not publish content to YouTube, modify YouTube accounts, or sell YouTube data.</p>
<p><a href="/privacy">Privacy Policy</a> · <a href="/terms">Terms of Service</a></p>
<p class="muted">Production URL: https://contest.telonyx.app</p>
"""
    )


@app.get("/privacy", response_class=HTMLResponse)
async def privacy():
    """Privacy policy for OAuth verification."""
    return legal_page(
        "Privacy Policy - TelOnyx Contest Bot",
        """
<h1>Privacy Policy</h1>
<p class="muted">Last updated: April 29, 2026</p>
<p>TelOnyx Contest Bot collects only the data needed to run Telegram contests and verify contest requirements.</p>
<h2>Data We Collect</h2>
<ul>
  <li>Telegram user ID, username, first name, and last name when a participant registers for a contest.</li>
  <li>Contest registration records, participation status, and winner information.</li>
  <li>OAuth tokens and account identifiers for connected services such as YouTube, TikTok, or Instagram when a contest requires external subscription verification.</li>
</ul>
<h2>Google User Data</h2>
<p>If a participant connects YouTube, the app requests read-only YouTube access only to verify the participant's channel identity and subscription status for the required contest channel. Google user data is not sold, shared for advertising, or used for unrelated purposes.</p>
<h2>Data Sharing</h2>
<p>Contest organizers may see participant registration records and winner information. We do not sell personal data.</p>
<h2>Data Retention and Deletion</h2>
<p>Contest records are retained as needed for contest administration. Users can request deletion of stored OAuth credentials and participation data by contacting the contest administrator.</p>
<h2>Security</h2>
<p>Access tokens and service credentials are stored on server-side infrastructure and are not exposed to participants in the Mini App.</p>
<h2>Contact</h2>
<p>For privacy requests or questions, contact the TelOnyx Contest Bot administrator through the Telegram bot or the organization that operates the contest.</p>
<p><a href="/about">About</a> · <a href="/terms">Terms of Service</a></p>
"""
    )


@app.get("/terms", response_class=HTMLResponse)
async def terms():
    """Terms of service for OAuth verification."""
    return legal_page(
        "Terms of Service - TelOnyx Contest Bot",
        """
<h1>Terms of Service</h1>
<p class="muted">Last updated: April 29, 2026</p>
<p>By using TelOnyx Contest Bot, you agree to use the service only for lawful contest participation and administration.</p>
<h2>Contest Participation</h2>
<p>Contest rules, eligibility, prizes, and winner selection are defined by the contest organizer. TelOnyx Contest Bot provides tools for registration, verification, and result publication.</p>
<h2>External Account Verification</h2>
<p>Some contests may require verification of subscriptions or follows on external platforms such as YouTube. The app uses read-only access where possible and only for the requested contest verification.</p>
<h2>Prohibited Use</h2>
<p>Users may not abuse the service, attempt unauthorized access, manipulate contest entries, or submit false information.</p>
<h2>Availability</h2>
<p>The service is provided as available. Features may change as platform APIs, Telegram Mini Apps, and OAuth providers evolve.</p>
<h2>Contact</h2>
<p>For questions about a specific contest, contact the contest organizer. For technical questions, contact the TelOnyx Contest Bot administrator through Telegram.</p>
<p><a href="/about">About</a> · <a href="/privacy">Privacy Policy</a></p>
"""
    )


@app.get("/", response_class=FileResponse)
async def root():
    """Служит точкой входа для SPA"""
    index_path = os.path.join(dist_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("Frontend not built. Run 'npm run build' in web/frontend", status_code=404)

@app.get("/{rest_of_path:path}")
async def catch_all(rest_of_path: str):
    """Catch-all роут для SPA роутинга"""
    if rest_of_path.startswith(("api/", "uploads/", "assets/")):
        return HTMLResponse("Not Found", status_code=404)

    allowed_spa_paths = {"admin", "register"}
    allowed_spa_prefixes = ("results/",)
    if rest_of_path not in allowed_spa_paths and not rest_of_path.startswith(allowed_spa_prefixes):
        return HTMLResponse("Not Found", status_code=404)

    index_path = os.path.join(dist_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("Not Found", status_code=404)

if __name__ == "__main__":
    uvicorn.run(
        "web.main:app",
        host=config.web_host,
        port=int(os.getenv("PORT", config.web_port)),
        reload=os.getenv("UVICORN_RELOAD", "false").lower() == "true",
    )
