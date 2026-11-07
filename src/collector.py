import asyncio
import os
import re
import sys
import subprocess
import time
import threading
from dnd_manager import open_dnd_settings
from analyzer import process_and_notify_async, encrypt_sender_name
# Thêm thư mục gốc vào path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from winsdk.windows.ui.notifications import (
    NotificationKinds,
    UserNotificationChangedEventArgs,
)
from winsdk.windows.ui.notifications.management import (
    UserNotificationListener,
    UserNotificationListenerAccessStatus,
)

from analyzer import process_and_notify_async

APP_NAME_MAP = {
    "zalo": "Zalo",
    "facebook.messenger": "Messenger",
    "chrome": "Google Chrome",
    "ms-teams": "Microsoft Teams",
    "discord": "Discord",
}

IGNORED_APP_KEYWORDS = [
    "screensketch",
    "windows.defender",
    "securityhealth",
    "system-settings",
    "bluetooth",
    "setup",
]

APP_START_TIME = time.time()  # MỐC THỜI GIAN KHỞI CHẠY ỨNG DỤNG
RECENT_NOTIFICATIONS = {}
PROCESSED_NOTIF_IDS = set()  # BỘ LƯU ID CHỐNG LẶP THÔNG BÁO TỪ WINDOWS
LOCK = threading.Lock()
PRINT_LOCK = asyncio.Lock()  # Khóa đồng bộ luồng in ấn và phân tích AI
NOTIFICATION_QUEUE = asyncio.Queue()

# Biến lưu trữ tiến trình Zalo và Event Loop
ZALO_PROCESS = None
MAIN_LOOP = None


def identify_source(app_id: str) -> str:
    app_id_lower = app_id.lower()
    for key, name in APP_NAME_MAP.items():
        if key in app_id_lower:
            return name
    return app_id


def clean_sender_for_ai(raw_sender: str) -> str:
    """
    Làm sạch chuỗi người gửi rác từ thông báo hệ thống Facebook/Messenger.
    Ví dụ: 'Nguyễn Minh Đức đã xoá bạn ra khỏi cuộc trò chuyện gửi tới Học đi...' -> 'Nguyễn Minh Đức'
    Hay đã rời khỏi đoạn chat, đã rời khỏi nhóm ,...."""
    patterns = [
        r"\s+(đã xoá bạn ra khỏi|đã xoá một tin nhắn|đã gửi|sent a photo|sent a video|sent a GIF).*",
        r"\s+(gửi tới|to)\s+.*",
    ]
    cleaned = raw_sender
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    return cleaned.strip() or raw_sender.strip()


def parse_notification_payload(raw_sender: str, raw_content: str, raw_source: str):
    source = raw_source
    if "facebook" in raw_sender.lower():
        source = "Facebook"
    elif "messenger" in raw_sender.lower():
        source = "Messenger"

    display_sender = raw_sender.strip()
    content = raw_content.strip()

    if raw_sender in ["Facebook", "Messenger", "Google Chrome"] or "facebook" in raw_sender.lower():
        if ":" in raw_content:
            parts = raw_content.split(":", 1)
            display_sender = parts[0].strip()
            content = parts[1].strip()
        elif re.search(r"\b(sent a photo to|sent a video to|đã gửi một ảnh tới)\b", raw_content, re.IGNORECASE):
            match = re.split(r"\b(sent a photo to|sent a video to|đã gửi một ảnh tới)\b", raw_content, flags=re.IGNORECASE)
            if len(match) >= 3:
                display_sender = f"{match[0].strip()} sent a photo to {match[2].strip()}"
                content = "[Đã gửi một hình ảnh/tệp tin]"

    # Tách tên sạch dành riêng cho AI phân tích
    ai_sender = clean_sender_for_ai(display_sender)

    return source, display_sender, ai_sender, content


def process_user_notification(user_notification):
    """HÀM XỬ LÝ TRUNG TÂM: Trích xuất và chỉ xử lý mỗi thông báo ĐÚNG 1 LẦN DUY NHẤT."""
    try:
        if not user_notification:
            return

        # 0. BỎ QUA TIN NHẮN TẠO TRƯỚC THỜI ĐIỂM BẬT APP
        try:
            if user_notification.creation_time.timestamp() < APP_START_TIME:
                return
        except Exception:
            pass

        # 1. KIỂM TRA ID THÔNG BÁO TỪ WINDOWS (LỌC THEO ID HỆ THỐNG)
        notif_id = user_notification.id
        with LOCK:
            if notif_id in PROCESSED_NOTIF_IDS:
                return
            PROCESSED_NOTIF_IDS.add(notif_id)

            if len(PROCESSED_NOTIF_IDS) > 1000:
                ids_to_remove = list(PROCESSED_NOTIF_IDS)[:200]
                for old_id in ids_to_remove:
                    PROCESSED_NOTIF_IDS.remove(old_id)

        # 2. BẮT ĐẦU TRÍCH XUẤT NỘI DUNG THÔNG BÁO
        app_id = user_notification.app_info.app_user_model_id
        if any(ignored in app_id.lower() for ignored in IGNORED_APP_KEYWORDS):
            return

        visual = user_notification.notification.visual
        binding = visual.get_binding("ToastGeneric")
        if not binding:
            return

        text_elements = binding.get_text_elements()
        texts = [element.text for element in text_elements if element.text]
        if not texts:
            return

        raw_sender = texts[0].strip()
        raw_content = " ".join(texts[1:]).strip() if len(texts) > 1 else ""
        if not raw_content:
            raw_content = raw_sender
            raw_sender = "Hệ thống"

        raw_source = identify_source(app_id)
        source, display_sender, ai_sender, content = parse_notification_payload(
            raw_sender, raw_content, raw_source
        )

        # ---> DÙNG WHITELIST: CHỈ CHO PHÉP CÁC NGUỒN TIN NHẮN <---
        # Các từ khóa nhận diện ứng dụng/trang web tin nhắn (nhớ viết chữ thường)
        allowed_messengers = [
            "zalo", "messenger", "discord", "gmail", "facebook",
            "telegram", "viber", "skype", "whatsapp", "mail"
        ]

        # Gộp cả nguồn (app) và tên hiển thị để kiểm tra
        check_string = f"{source} {display_sender}".lower()
        
        # Nếu KHÔNG CÓ bất kỳ từ khóa cho phép nào xuất hiện -> Bỏ qua
        if not any(allowed in check_string for allowed in allowed_messengers):
            return  
        # ---------------------------------------------------------

        # 3. KHÓA CHỐNG TRÙNG LẶP THEO NỘI DUNG TIN NHẮN (DUY TRÌ TRONG 120 GIÂY)
        normalized_content = re.sub(r"\s+", " ", content.lower().strip())
        normalized_sender = re.sub(r"\s+", " ", ai_sender.lower().strip())
        dedup_key = f"{normalized_sender}:{normalized_content}"

        current_time = time.time()

        with LOCK:
            if (
                dedup_key in RECENT_NOTIFICATIONS
                and (current_time - RECENT_NOTIFICATIONS[dedup_key]) < 120
            ):
                return  # Đã xử lý nội dung này gần đây -> Bỏ qua ngay!

            RECENT_NOTIFICATIONS[dedup_key] = current_time

            for k in list(RECENT_NOTIFICATIONS.keys()):
                if current_time - RECENT_NOTIFICATIONS[k] > 180:
                    del RECENT_NOTIFICATIONS[k]

        # 4. ĐẨY VÀO QUEUE CHO AI XỬ LÝ (THREAD-SAFE)
        if MAIN_LOOP and MAIN_LOOP.is_running():
            MAIN_LOOP.call_soon_threadsafe(
                NOTIFICATION_QUEUE.put_nowait,
                {
                    "source": source,
                    "display_sender": display_sender,
                    "ai_sender": ai_sender,
                    "content": content,
                },
            )

    except Exception as err:
        print(f"[DEBUG] Lỗi trích xuất thông báo: {err}")


async def poll_action_center_backup(listener):
    """LUỒNG DỰ PHÒNG: Chủ động vào Action Center hốt tin nhắn Messenger mỗi 1.5s"""
    while True:
        try:
            notifications = await listener.get_notifications_async(NotificationKinds.TOAST)
            if notifications:
                for notif in notifications:
                    process_user_notification(notif)
        except Exception:
            pass
        await asyncio.sleep(1.5)


async def notification_worker():
    while True:
        payload = await NOTIFICATION_QUEUE.get()
        try:
            source = payload["source"]
            display_sender = payload["display_sender"]
            ai_sender = payload["ai_sender"]
            content = payload["content"]

            # Dùng async lock để ĐẢM BẢO in ấn + phân tích tin nhắn nào xong trọn vẹn tin nhắn đó
            async with PRINT_LOCK:
                print("\n┌── 📩 NHẬN THÔNG BÁO MỚI (ACTION CENTER) ────────────────")
                print(f"│ 📍 Nguồn    : {source}")
                print(f"│ 👤 Người gửi : {display_sender}")
                encrypted_ai_name = encrypt_sender_name(ai_sender)
                print(f"│ 🤖 Tên gửi AI: {encrypted_ai_name} (Đã mã hóa ẩn danh)")
                print(f"│ 💬 Nội dung  : {content}")
                print("└─────────────────────────────────────────────────────────")

                # Chờ Groq AI phân tích và in log xong hoàn toàn trước khi mở khóa cho tin nhắn tiếp theo
                await process_and_notify_async(source, ai_sender, content, display_sender=display_sender)
                print("------------------------------------------------------")

        except Exception as e:
            print(f"[LỖI WORKER XỬ LÝ THÔNG BÁO]: {e}")
        finally:
            NOTIFICATION_QUEUE.task_done()


async def start_listener():
    global ZALO_PROCESS, MAIN_LOOP
    MAIN_LOOP = asyncio.get_running_loop()

    print("\n=========================================================")
    print("🛡️  SMART FOCUS GUARD - UNIFIED COLLECTOR IS RUNNING     🛡️")
    print("=========================================================")

    open_dnd_settings()
    # 1. KÍCH HOẠT ZALO BẰNG ĐA TIẾN TRÌNH (SUBPROCESS - CÁCH LY 100%)
    zalo_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zalo_interceptor.py")
    if os.path.exists(zalo_script_path):
        try:
            ZALO_PROCESS = subprocess.Popen([sys.executable, zalo_script_path])
            print("✅ [ZALO] Đã kích hoạt Zalo Interceptor (Tiến trình độc lập) thành công!")
        except Exception as e:
            print(f"❌ [LỖI ZALO SUBPROCESS]: {e}")
    else:
        print("⚠️ [ZALO] Không tìm thấy file zalo_interceptor.py cùng thư mục.")

    # 2. KHỞI ĐỘNG WINDOWS ACTION CENTER LISTENER
    listener = UserNotificationListener.current
    status = await listener.request_access_async()

    if status != UserNotificationListenerAccessStatus.ALLOWED:
        print("❌ [LỖI] Chưa được cấp quyền truy cập thông báo Windows Action Center!")
        return

    # QUÉT VÀ NẠP TẤT CẢ ID THÔNG BÁO TỒN ĐỌNG TRONG ACTION CENTER VÀO BỘ NHỚ CHỐNG TRÙNG
    try:
        existing_notifs = await listener.get_notifications_async(NotificationKinds.TOAST)
        if existing_notifs:
            with LOCK:
                for notif in existing_notifs:
                    PROCESSED_NOTIF_IDS.add(notif.id)
            print(f"🧹 Đã lọc bỏ {len(existing_notifs)} thông báo cũ tồn đọng trong Action Center trước khi bật app.")
    except Exception as e:
        print(f"⚠️ Không thể quét thông báo cũ: {e}")

    print("✅ [ACTION CENTER] Đã kết nối thành công với Windows Notification Listener!")
    print("🎧 Đang lắng nghe tất cả thông báo hệ thống...\n")

    # Lưu lại tham chiếu 2 task ngầm để có thể cancel triệt để khi stop
    worker_task = asyncio.create_task(notification_worker())
    backup_task = asyncio.create_task(poll_action_center_backup(listener))

    def on_notification_changed(sender, event_args: UserNotificationChangedEventArgs):
        try:
            notification_id = event_args.user_notification_id
            user_notification = listener.get_notification(notification_id)
            if user_notification:
                process_user_notification(user_notification)
        except Exception as err:
            print(f"[DEBUG] Lỗi trích xuất thông báo: {err}")

    token = listener.add_notification_changed(on_notification_changed)

    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        print("\n🛑 [STOP] Đang dọn dẹp và tắt hệ thống Collector...")

        # 1. Gỡ listener sự kiện
        try:
            listener.remove_notification_changed(token)
        except Exception:
            pass

        # 2. Hủy các Task ngầm con
        worker_task.cancel()
        backup_task.cancel()

        # 3. Tắt tiến trình Zalo con
        if ZALO_PROCESS:
            try:
                ZALO_PROCESS.terminate()
                ZALO_PROCESS.wait(timeout=2)
            except Exception:
                ZALO_PROCESS.kill()
            ZALO_PROCESS = None

        open_dnd_settings()
        raise  # Báo lại CancelledError cho api_server nhận biết


if __name__ == "__main__":
    try:
        asyncio.run(start_listener())
    except KeyboardInterrupt:
        pass