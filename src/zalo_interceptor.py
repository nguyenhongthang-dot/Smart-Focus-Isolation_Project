import asyncio
import ctypes
from ctypes import wintypes
import os
import psutil
import sys
import threading
import time
import uiautomation as auto
import win32con  # type: ignore
import win32gui  # type: ignore
import win32process  # type: ignore
import multiprocessing
from pycaw.pycaw import AudioUtilities  # Đã thêm thư viện pycaw

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

try:
    from src.analyzer import process_and_notify_async, encrypt_sender_name
except ImportError:
    from analyzer import process_and_notify_async, encrypt_sender_name


# --- CẤU HÌNH WIN32 HOOK ---
WINEVENT_OUTOFCONTEXT = 0x0000
EVENT_OBJECT_SHOW = 0x8002

user32 = ctypes.windll.user32
ole32 = ctypes.windll.ole32

WinEventProcType = ctypes.WINFUNCTYPE(
    None,
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.HWND,
    wintypes.LONG,
    wintypes.LONG,
    wintypes.DWORD,
    wintypes.DWORD,
)

PROCESSED_HWNDS = set()
RECENT_MESSAGES = {}
LOCK = threading.Lock()
ASYNC_LOOP = None

ZALO_QUEUE = asyncio.Queue()
PRINT_LOCK = asyncio.Lock()


# Đã thêm hàm mute_zalo_process
def mute_zalo_process(mute=True):
    sessions = AudioUtilities.GetAllSessions()
    for session in sessions:
        if session.Process and session.Process.name().lower() == "zalo.exe":
            volume = session.SimpleAudioVolume
            volume.SetMute(int(mute), None)


def is_zalo_process(hwnd: int) -> bool:
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if pid == 0:
            return False
        proc = psutil.Process(pid)
        return proc.name().lower() == "zalo.exe"
    except Exception:
        return False


def extract_text_recursive(element) -> list[str]:
    texts = []
    try:
        name = element.Name.strip() if element.Name else ""
        if name and name not in texts:
            texts.append(name)

        for child in element.GetChildren():
            child_texts = extract_text_recursive(child)
            for t in child_texts:
                if t not in texts:
                    texts.append(t)
    except Exception:
        pass
    return texts


def parse_zalo_popup_text(texts: list[str]) -> tuple[str, str]:
    ignored_keywords = ["Zalo", "Trả lời", "Bỏ qua", "Đóng", "b", "Đánh dấu đã đọc"]
    filtered = [
        t.strip() for t in texts if t.strip() and t.strip() not in ignored_keywords
    ]

    if not filtered:
        return None, None

    if len(filtered) == 1:
        content = filtered[0]
        if len(content) <= 2 or "Có tin nhắn mới" in content or "tin nhắn" in content.lower():
            return None, None
        sender = "Hệ thống Zalo"
    else:
        sender = filtered[0]
        content = " ".join(filtered[1:])

    if len(content) > 500:
        content = content[:500] + "..."

    return sender, content


def is_duplicate_message(sender: str, content: str) -> bool:
    now = time.time()
    key = f"{sender}:{content}"
    
    with LOCK:
        for k in list(RECENT_MESSAGES.keys()):
            if now - RECENT_MESSAGES[k] > 10:
                del RECENT_MESSAGES[k]
                
        if key in RECENT_MESSAGES and (now - RECENT_MESSAGES[key] < 3):
            return True
            
        RECENT_MESSAGES[key] = now
        return False


def handle_zalo_popup(hwnd: int):
    try:
        ole32.CoInitialize(None)
    except Exception:
        pass

    with LOCK:
        if hwnd in PROCESSED_HWNDS:
            return
        PROCESSED_HWNDS.add(hwnd)

    try:
        if not win32gui.IsWindow(hwnd):
            return

        try:
            rect = win32gui.GetWindowRect(hwnd)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]

            if width > 500 or height > 400 or width <= 10 or height <= 10:
                return
        except Exception:
            return

        # Làm trong suốt popup (tàng hình) và thêm độ trễ nhân tạo nhẹ
        if win32gui.IsWindow(hwnd):
            try:
                # Ép trong suốt hoàn toàn thay vì giật tọa độ
                style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style | win32con.WS_EX_LAYERED)
                win32gui.SetLayeredWindowAttributes(hwnd, 0, 0, win32con.LWA_ALPHA)
                
                # Humanize: trễ 0.1s để giả lập độ trễ API/mắt người
                time.sleep(0.1)
            except Exception:
                pass

        control = auto.ControlFromHandle(hwnd)
        if not control.Exists(maxSearchSeconds=1):
            return

        raw_texts = extract_text_recursive(control)
        sender, content = parse_zalo_popup_text(raw_texts)

        if not sender or not content:
            if win32gui.IsWindow(hwnd):
                try:
                    time.sleep(0.05)
                    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                except Exception:
                    pass
            return

        if win32gui.IsWindow(hwnd):
            try:
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            except Exception:
                pass

        if is_duplicate_message(sender, content):
            return

        if ASYNC_LOOP and ASYNC_LOOP.is_running():
            asyncio.run_coroutine_threadsafe(
                ZALO_QUEUE.put({"sender": sender, "content": content}), ASYNC_LOOP
            )

    except Exception:
        pass
    finally:
        try:
            ole32.CoUninitialize()
        except Exception:
            pass


async def zalo_notification_worker():
    """Worker đẩy dữ liệu sang AI để phân tích."""
    while True:
        payload = await ZALO_QUEUE.get()
        try:
            sender = payload["sender"]
            content = payload["content"]

            async with PRINT_LOCK:
                print("\n┌── 📩 NHẬN THÔNG BÁO MỚI (ZALO INTERCEPTOR) ─────────────")
                print(f"│ 📍 Nguồn    : Zalo")
                print(f"│ 👤 Người gửi : {sender}")
                encrypted_name = encrypt_sender_name(sender)
                print(f"│ 🤖 Tên gửi AI: {encrypted_name} (Đã mã hóa ẩn danh)")
                print(f"│ 💬 Nội dung  : {content}")
                print("└─────────────────────────────────────────────────────────")

                # Đẩy sang cho AI phân tích. AI phân tích xong sẽ gọi notifier.py
                # Nếu is_urgent == 1 thì Popup PyQt5 mới được mở ra!
                await process_and_notify_async("Zalo", sender, content)
                print("------------------------------------------------------")
                
        except Exception as e:
            print(f"[LỖI WORKER ZALO]: {e}")
        finally:
            ZALO_QUEUE.task_done()


def win_event_callback(hWinEventHook, event, hwnd, idObject, idChild, dwEventThread, dwmsEventTime):
    if not hwnd or not win32gui.IsWindow(hwnd):
        return

    if is_zalo_process(hwnd):
        try:
            rect = win32gui.GetWindowRect(hwnd)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]

            if 50 < width <= 500 and 50 < height <= 400:
                threading.Thread(
                    target=handle_zalo_popup, args=(hwnd,), daemon=True
                ).start()
        except Exception:
            pass

def purge_unprocessed_zalo_popups():
    """
    Quét và xóa toàn bộ Popup Zalo chưa xử lý còn tồn đọng trên hệ thống
    TRƯỚC KHI Collector chính thức lắng nghe thông báo mới.
    """
    count = 0
    def enum_windows_callback(hwnd, _):
        nonlocal count
        if not win32gui.IsWindow(hwnd):
            return True
        
        # Kiểm tra xem cửa sổ có thuộc Zalo hay không
        if is_zalo_process(hwnd):
            try:
                rect = win32gui.GetWindowRect(hwnd)
                width = rect[2] - rect[0]
                height = rect[3] - rect[1]

                # Kiểm tra kích thước khung Popup Zalo
                if 50 < width <= 500 and 50 < height <= 400:
                    with LOCK:
                        PROCESSED_HWNDS.add(hwnd)  # Đánh dấu đã bỏ qua (không cho AI phân tích)
                    
                    # Phát lệnh đóng ngay lập tức cửa sổ Popup cũ
                    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                    count += 1
            except Exception:
                pass
        return True

    try:
        win32gui.EnumWindows(enum_windows_callback, None)
        print(f"🧹 [ZALO CLEANUP] Đã dọn dẹp {count} Popup Zalo tồn đọng từ trước!")
    except Exception as e:
        print(f"⚠️ [ZALO CLEANUP LỖI]: {e}")


def start_win32_hook():
    ole32.CoInitialize(None)

    purge_unprocessed_zalo_popups()

    proc_delegate = WinEventProcType(win_event_callback)

    hook = user32.SetWinEventHook(
        EVENT_OBJECT_SHOW, EVENT_OBJECT_SHOW, 0, proc_delegate, 0, 0, WINEVENT_OUTOFCONTEXT
    )

    if not hook:
        print("❌ [LỖI] Không thể đăng ký Windows Win32 Hook!")
        return

    print("=========================================================")
    print("🛡️  ZALO POPUP INTERCEPTOR IS RUNNING (CÁCH 1: TÀNG HÌNH) 🛡️")
    print("=========================================================")
    print("✅ Đã kích hoạt Hook tàng hình tọa độ âm (-10000, -10000).")
    print("🎧 Đang lắng nghe và tự động chuyển giao dữ liệu cho AI...\n")

    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))

    user32.UnhookWinEvent(hook)


async def main():
    global ASYNC_LOOP
    ASYNC_LOOP = asyncio.get_running_loop()

    # Đã thêm lời gọi hàm để tắt âm thanh Zalo khi khởi chạy
    try:
        mute_zalo_process(True)
        print("🔇 Đã tắt âm thanh hệ thống của Zalo thành công!")
    except Exception as e:
        print(f"⚠️ Không thể tắt âm thanh Zalo: {e}")

    asyncio.create_task(zalo_notification_worker())

    hook_thread = threading.Thread(target=start_win32_hook, daemon=True)
    hook_thread.start()

    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    multiprocessing.freeze_support() 
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Đã thêm lời gọi hàm để bật lại âm thanh Zalo khi tắt chương trình
        try:
            mute_zalo_process(False)
            print("\n🔊 Đã bật lại âm thanh cho Zalo.")
        except Exception:
            pass
        print("🛑 Đã dừng Zalo Interceptor.")