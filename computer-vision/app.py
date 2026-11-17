"""Entrypoint FastAPI Asisten Belajar AI & IoT Companion Server."""

import uvicorn
from config import Config
from server import app

if __name__ == "__main__":
    port = Config.PORT if hasattr(Config, "PORT") else 5000
    host = Config.HOST if hasattr(Config, "HOST") else "0.0.0.0"

    print("\n" + "=" * 62, flush=True)
    print("🌟 ASISTEN BELAJAR AI - FASTAPI CORE BACKEND", flush=True)
    print(f"📡 Swagger API Documentation : http://localhost:{port}/docs", flush=True)
    print(f"📷 Video Stream MJPEG Feed    : http://localhost:{port}/video_feed", flush=True)
    print(f"🤖 ESP32-S3 OLED Endpoint    : http://localhost:{port}/api/esp/pomodoro", flush=True)
    print("=" * 62 + "\n", flush=True)

    uvicorn.run("server:app", host=host, port=port, reload=False)
