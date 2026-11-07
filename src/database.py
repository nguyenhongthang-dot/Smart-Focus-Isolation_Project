import os
import sqlite3


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "focus_guard.db")




def get_connection():
    return sqlite3.connect(DB_PATH)




def init_db():
    db_exists = os.path.exists(DB_PATH)  # <-- Thêm kiểm tra tồn tại
    with get_connection() as conn:
        cursor = conn.cursor()
        # BẢNG TIN NHẮN (Bổ sung cột session_id để biết tin nhắn thuộc phiên Live nào)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS message_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                source TEXT NOT NULL,
                sender TEXT NOT NULL,
                content TEXT NOT NULL,
                is_urgent INTEGER NOT NULL,
                reason TEXT,
                received_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            )
        """)
        # BẢNG PHIÊN LIVE (Lưu đúng Ngày + Giờ thực tế theo giờ máy tính 'localtime')
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS focus_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                end_time TIMESTAMP,
                duration_seconds INTEGER DEFAULT 0,
                status TEXT DEFAULT 'ACTIVE'
            )
        """)
        conn.commit()
   
    # <-- Thêm điều kiện if để chỉ in nếu DB mới được tạo
    if not db_exists:
        print(f"Đã khởi tạo cơ sỡ dữ liệu thành công tại: {DB_PATH}")




# TỰ ĐỘNG GỌI HÀM KHỞI TẠO ĐỂ ĐẢM BẢO BẢNG LUÔN TỒN TẠI TRƯỚC KHI LƯU
init_db()  # <-- Thêm gọi hàm tự động




def save_message(
    source: str, sender: str, content: str, is_urgent: int, reason: str = "", session_id: int = None
):
    if sender == "SFIT" and source == "Smart focus isolation":
        return
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO message_logs (session_id, source, sender, content, is_urgent, reason)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (session_id, source, sender, content, is_urgent, reason),
        )
        conn.commit()
    print(f"[DB Saved] [Session #{session_id}] {source} | Từ: {sender} | Gấp: {is_urgent}")




def get_recent_history(sender: str, limit: int = 5) -> str:
    """Lấy N tin nhắn gần nhất của người gửi để làm ngữ cảnh cho AI"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT content FROM message_logs
                WHERE sender = ?
                ORDER BY id DESC LIMIT ?
            """,
                (sender, limit),
            )
            rows = cursor.fetchall()
            if not rows:
                return "Không có lịch sử trò chuyện trước đó."
            # Đảo ngược lại đúng thứ tự thời gian
            history = [r[0] for r in reversed(rows)]
            return "\n".join([f"- {msg}" for msg in history])
    except Exception as e:  # <-- Thêm as e
        print(f"[LỖI ĐỌC DB]: {e}")  # <-- Thêm câu lệnh in lỗi
        return ""




def start_live_session() -> int:
    """Tạo phiên Live mới (Đóng tất cả các phiên ACTIVE trôi nổi trước đó)"""
    with get_connection() as conn:
        cursor = conn.cursor()
       
        # Dọn sạch các phiên ACTIVE cũ (nếu có do sập server hoặc lỗi)
        cursor.execute("""
            UPDATE focus_sessions
            SET end_time = datetime('now', 'localtime'),
                duration_seconds = CAST((strftime('%s', datetime('now', 'localtime')) - strftime('%s', start_time)) AS INTEGER),
                status = 'STOPPED'
            WHERE status = 'ACTIVE'
        """)
       
        # Tạo phiên mới
        cursor.execute("INSERT INTO focus_sessions (status) VALUES ('ACTIVE')")
        conn.commit()
        return cursor.lastrowid


def stop_live_session(session_id: int):
    """Đóng phiên Live & Lưu GIỜ THỰC KẾT THÚC"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE focus_sessions
            SET end_time = datetime('now', 'localtime'),
                duration_seconds = CAST((strftime('%s', datetime('now', 'localtime')) - strftime('%s', start_time)) AS INTEGER),
                status = 'STOPPED'
            WHERE id = ?
        """, (session_id,))
        conn.commit()




def get_session_messages(session_id: int) -> list:
    """Hàm lấy toàn bộ tin nhắn thuộc một phiên Live cụ thể (Phục vụ AI tóm tắt sau này)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT source, sender, content, is_urgent, reason, received_at
            FROM message_logs
            WHERE session_id = ?
            ORDER BY id ASC
        """, (session_id,))
        rows = cursor.fetchall()
        return rows




# if __name__ == "__main__":
#     # Chạy thử hàm tạo DB và thêm thử 1 dòng dữ liệu (Mock data)
#     init_db()
#     save_message(
#         source="Zalo",
#         sender="Thầy A",
#         content="Nộp bài tập C++ gấp trước 5h",
#         is_urgent=1,
#         reason="Chứa từ khóa ưu tiên và mốc thời gian",
#     )

