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
from web.api import contests, admin, publish, youtube_auth, ws, analytics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Contest Bot WebApp")

# Директории
static_dir = os.path.join(os.path.dirname(__file__), "static")
uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
dist_dir = os.path.join(static_dir, "dist")

# Монтируем загрузки
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# Монтируем ассеты билда
if os.path.exists(os.path.join(dist_dir, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(dist_dir, "assets")), name="assets")

# Подключение API роутеров
app.include_router(contests.router)
app.include_router(admin.router)
app.include_router(publish.router)
app.include_router(youtube_auth.router)
app.include_router(ws.router)
app.include_router(analytics.router)

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
    # Если это не запрос к API и не к статике, отдаем index.html
    if rest_of_path.startswith("api/") or rest_of_path.startswith("uploads/"):
        return HTMLResponse("Not Found", status_code=404)
        
    index_path = os.path.join(dist_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("Not Found", status_code=404)

if __name__ == "__main__":
    uvicorn.run("web.main:app", host="0.0.0.0", port=8000, reload=True)
