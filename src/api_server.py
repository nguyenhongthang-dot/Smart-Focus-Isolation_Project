# api_server.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
from analytics import get_overview_stats, get_hourly_distribution, get_recent_urgent_logs
from analyzer import load_config
from database import start_live_session, stop_live_session
import subprocess
import os
import sys
from dnd_manager import open_dnd_settings
import asyncio
from collector import start_listener
from notifier import trigger_alert
from contextlib import asynccontextmanager

# Biến toàn cục
current_session_id = None
collector_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Phần code khởi động (startup) nếu có sẽ nằm trước yield
    yield
    
    # Đoạn code xử lý khi tắt server (shutdown)
    global current_session_id
    if current_session_id is not None:
        from database import stop_live_session
        stop_live_session(current_session_id)
        current_session_id = None
    else:
        from database import get_connection
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE focus_sessions SET status = 'STOPPED' WHERE status = 'ACTIVE'")
            conn.commit()

# Khởi tạo app duy nhất 1 lần với lifespan đã định nghĩa ở trên
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/stats")
def get_stats():
    stats = get_overview_stats()
    config = load_config()
    sources = config.get("sources", {})
    main_sources = ["Zalo", "Messenger", "Gmail", "Discord"]
    
    active_count = 0
    if not sources:
        active_count = 4
    else:
        for app_name in main_sources:
            if sources.get(app_name, True) == True:
                active_count += 1
                
    stats["active_sources_count"] = active_count
    return stats

@app.get("/api/hourly")
def get_hourly():
    return get_hourly_distribution()

@app.get("/api/recent-urgent")
def get_logs():
    return get_recent_urgent_logs()

@app.get("/api/config")
def get_config():
    return load_config()

@app.post("/api/config")
def update_config(new_config: dict):
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(new_config, f, indent=2, ensure_ascii=False)
    return {"message": "Success"}

@app.post("/api/collector/start")
async def start_collector():
    global collector_task, current_session_id
    if collector_task is None or collector_task.done():
        # Bắt đầu phiên tập trung mới trong DB
        current_session_id = start_live_session()
        collector_task = asyncio.create_task(start_listener())
        
        # --- THÊM ĐOẠN NÀY: WARM-UP POPUP NGAY KHI KHỞI ĐỘNG ---
        trigger_alert(
            source="Smart focus isolation",
            sender="SFIT",
            content="Hệ thống đã bắt đầu hoạt động, chúc bạn một phiên tập trung hiệu quả 🩵",
            is_urgent=1,
            reason="Khởi động phiên"
        )
        # -------------------------------------------------------
        
        return {"status": "started", "message": "Đã bật Collector", "session_id": current_session_id}
    return {"status": "already_running"}

@app.post("/api/collector/stop")
async def stop_collector():
    global collector_task, current_session_id
    if collector_task is not None and not collector_task.done():
        collector_task.cancel()
        try:
            await collector_task
        except asyncio.CancelledError:
            pass
        collector_task = None
        
        # Kết thúc phiên tập trung và lưu thời gian trong DB
        if current_session_id is not None:
            stop_live_session(current_session_id)
            current_session_id = None
            
        return {"status": "stopped", "message": "Đã tắt hoàn toàn Collector."}
    
    return {"status": "already_stopped", "message": "Collector đã dừng từ trước."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")