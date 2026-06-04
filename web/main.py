"""
Главный файл для запуска FastAPI веб-сервера
"""
import uvicorn
import logging
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from shared.config import config
from shared.services.upload_storage import ensure_upload_dir
from web.api import contests, admin, publish, youtube_auth, ws, analytics, tiktok_auth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Contest Bot WebApp")

# Директории
static_dir = os.path.join(os.path.dirname(__file__), "static")
uploads_dir = ensure_upload_dir()
dist_dir = os.path.join(static_dir, "dist")
presentation_dir = os.path.join(static_dir, "presentation")
presentation_index = os.path.join(presentation_dir, "index.html")
presentation_images_dir = os.path.join(presentation_dir, "images")


# Монтируем загрузки
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# Монтируем ассеты билда
if os.path.exists(os.path.join(dist_dir, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(dist_dir, "assets")), name="assets")

# Монтируем презентацию как статический сайт на /presentation
if os.path.exists(presentation_dir):
    app.mount("/presentation", StaticFiles(directory=presentation_dir, html=True), name="presentation")

# Подключение API роутеров
app.include_router(contests.router)
app.include_router(admin.router)
app.include_router(publish.router)
app.include_router(youtube_auth.router)
app.include_router(tiktok_auth.router)
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
    max-width: 860px;
    margin: 0 auto;
    padding: 48px 20px 72px;
}
a { color: #66b7ff; }
h1 { font-size: 34px; line-height: 1.15; margin: 0 0 16px; }
h2 { font-size: 20px; margin-top: 34px; }
p, li { color: #c8d4df; }
strong { color: #eef4fb; }
.muted { color: #8fa1b2; }
.card {
    border: 1px solid rgba(148, 163, 184, 0.22);
    background: rgba(15, 23, 32, 0.72);
    border-radius: 18px;
    padding: 18px 20px;
    margin: 22px 0;
}
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
<p class="muted">Last updated: May 27, 2026</p>
<p>TelOnyx Contest Bot is a Telegram Mini App used to run Telegram contests and verify contest participation requirements, including Telegram membership and optional external service requirements such as YouTube channel subscription verification.</p>
<p>This Privacy Policy explains what data we collect, how we use it, how we store and protect it, how we share it, and how users can request deletion of their data.</p>

<div class="card">
  <p><strong>Google API Services User Data Policy disclosure:</strong> TelOnyx Contest Bot's use and transfer of information received from Google APIs will adhere to the <a href="https://developers.google.com/terms/api-services-user-data-policy">Google API Services User Data Policy</a>, including the Limited Use requirements.</p>
</div>

<h2>1. Data We Collect</h2>
<p>When a participant registers for a contest, TelOnyx Contest Bot may collect the following Telegram-related and contest-related data:</p>
<ul>
  <li>Telegram user ID;</li>
  <li>Telegram username;</li>
  <li>Telegram first name and last name;</li>
  <li>contest registration records;</li>
  <li>contest participation status;</li>
  <li>contest eligibility status;</li>
  <li>winner information when applicable.</li>
</ul>
<p>When a contest requires external service verification, the app may also collect account identifiers and OAuth credentials required to complete that verification.</p>

<h2>2. Google User Data Accessed</h2>
<p>If a participant chooses to connect their Google / YouTube account, TelOnyx Contest Bot requests the following Google OAuth scope:</p>
<ul>
  <li><code>https://www.googleapis.com/auth/youtube.readonly</code></li>
</ul>
<p>The app uses this read-only access only for contest requirement verification. Depending on the contest setup, the app may access the following Google / YouTube user data:</p>
<ul>
  <li>basic Google OAuth authentication result required to connect the account;</li>
  <li>YouTube channel ID associated with the connected account;</li>
  <li>YouTube channel title and public channel metadata returned by the YouTube Data API;</li>
  <li>YouTube subscription list data needed to verify whether the participant is subscribed to the required contest channel;</li>
  <li>OAuth access token, refresh token, token URI, token expiration time, client ID reference, and granted scopes required to perform and maintain the verification.</li>
</ul>
<p>TelOnyx Contest Bot does not request permission to upload, modify, delete, or manage YouTube videos, channels, comments, playlists, or other user content.</p>

<h2>3. How Google User Data Is Used</h2>
<p>Google user data is used only for the following purposes:</p>
<ul>
  <li>to authenticate the participant through Google OAuth;</li>
  <li>to identify the participant's connected YouTube channel;</li>
  <li>to verify whether the participant meets a contest requirement, such as being subscribed to a specific YouTube channel;</li>
  <li>to update the participant's contest eligibility status inside TelOnyx Contest Bot;</li>
  <li>to allow the participant to disconnect their YouTube account from the contest bot.</li>
</ul>
<p>Google user data is not used for advertising, analytics profiling, unrelated marketing, or any purpose unrelated to contest requirement verification.</p>
<p>Google user data is not used to develop, improve, or train generalized artificial intelligence or machine learning models.</p>

<h2>4. Data Sharing</h2>
<p>TelOnyx Contest Bot does not sell Google user data.</p>
<p>Google user data is not shared with advertisers, data brokers, or unrelated third parties.</p>
<p>Contest organizers may see limited contest-related information, such as participant registration status, eligibility status, and winner information. Contest organizers do not receive OAuth access tokens or refresh tokens.</p>
<p>Google user data may be processed by our hosting, database, logging, and infrastructure providers only as necessary to operate, secure, monitor, and maintain the application. These providers process data only for infrastructure and service operation purposes.</p>
<p>We may disclose information if required by law, regulation, legal process, or to protect the security, integrity, and lawful operation of the service.</p>

<h2>5. Data Storage and Protection</h2>
<p>OAuth tokens, account identifiers, YouTube channel identifiers, and contest records are stored on server-side infrastructure.</p>
<p>Access tokens, refresh tokens, client secrets, and service credentials are not exposed to participants in the Telegram Mini App.</p>
<p>We use reasonable technical and organizational safeguards to protect user data, including:</p>
<ul>
  <li>HTTPS for data transmission;</li>
  <li>server-side storage of OAuth credentials;</li>
  <li>restricted access to production infrastructure;</li>
  <li>environment-based secret management;</li>
  <li>database access controls;</li>
  <li>limiting access to user data to authorized administrators or backend services that require it to operate the contest.</li>
</ul>

<h2>6. Data Retention and Deletion</h2>
<p>Contest participation records are retained only as long as necessary to administer the contest, resolve disputes, prevent fraud, maintain contest integrity, and comply with operational or legal requirements.</p>
<p>OAuth tokens and connected Google / YouTube account data are retained only as long as needed to verify contest requirements or maintain the participant's contest eligibility status.</p>
<p>Users may request deletion of their stored OAuth credentials, connected account data, and contest participation data by contacting the TelOnyx Contest Bot administrator.</p>
<p>For privacy or deletion requests, contact: <a href="mailto:a0w.k1m@gmail.com">a0w.k1m@gmail.com</a></p>
<p>After receiving a deletion request, we will delete or anonymize the user's stored data unless retention is required for legal, security, fraud prevention, or contest integrity reasons.</p>

<h2>7. Revoking Google Access</h2>
<p>Users can revoke TelOnyx Contest Bot's access to their Google account at any time through their Google Account permissions page:</p>
<p><a href="https://myaccount.google.com/permissions">https://myaccount.google.com/permissions</a></p>
<p>After access is revoked, TelOnyx Contest Bot will no longer be able to verify YouTube subscription status for that user unless the user connects their Google account again.</p>

<h2>8. Security</h2>
<p>We take reasonable measures to protect user data from unauthorized access, disclosure, alteration, or destruction.</p>
<p>However, no online service can guarantee absolute security. Users should contact us if they believe their data has been accessed or used without authorization.</p>

<h2>9. Contact</h2>
<p>For privacy requests, data deletion requests, or questions about this Privacy Policy, please contact:</p>
<p><a href="mailto:a0w.k1m@gmail.com">a0w.k1m@gmail.com</a></p>
<p>Users may also contact the contest administrator through the Telegram bot or the organization operating the contest.</p>
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
