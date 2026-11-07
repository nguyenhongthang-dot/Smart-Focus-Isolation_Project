import os
import sys
import time
import winsound
import multiprocessing
import socket
import json
import threading
import queue
from database import save_message

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
SOUND_PATH = os.path.join(ASSETS_DIR, "alert.wav")

if not os.path.exists(ASSETS_DIR):
    os.makedirs(ASSETS_DIR)

# Biến toàn cục quản lý Tiến trình hiển thị Popup
_popup_process = None

# ----------------------------------------------------
# 1. TIẾN TRÌNH QUẢN LÝ POPUP XẾP CHỒNG (PYQT5)
# ----------------------------------------------------
def _popup_manager_process():
    """
    Tiến trình chạy ứng dụng PyQt5 duy nhất.
    Nhận dữ liệu từ TCP Socket (để hỗ trợ đa tiến trình đồng bộ) và quản lý xếp chồng (stacking) các Popup.
    """
    try:
        from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFrame
        from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QRect
    except ImportError:
        print("\n❌ LỖI: Vui lòng cài đặt PyQt5 (Lệnh: pip install PyQt5)")
        return

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    # Danh sách lưu trữ các Popup đang hiển thị trên màn hình
    active_popups = []
    local_queue = queue.Queue()

    # Khởi tạo Socket Server lắng nghe tin nhắn từ mọi tiến trình
    def socket_listener():
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            server.bind(('127.0.0.1', 54321))
            server.listen(10)
        except Exception as e:
            # Nếu port 54321 đã bị một tiến trình PyQt5 khác chiếm, lập tức tự hủy tiến trình dư thừa này
            os._exit(0)
            return
            
        while True:
            try:
                conn, addr = server.accept()
                data = conn.recv(8192).decode('utf-8')
                if data:
                    payload = json.loads(data)
                    local_queue.put(payload)
                conn.close()
            except Exception:
                pass

    listener_thread = threading.Thread(target=socket_listener, daemon=True)
    listener_thread.start()

    class CustomGradientPopup(QWidget):
        def __init__(self, title, sender_name, message, deep_link, manager_list):
            super().__init__()
            self.manager_list = manager_list
            self.source_app = title          
            self.sender_name = sender_name   
            self.deep_link = deep_link       
            self._is_clicking = False        
            
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setCursor(Qt.PointingHandCursor)
            
            self.popup_w = 480
            self.popup_h = 105
            self.gap = 10              
            self.margin_bottom = 45    
            self.margin_right = 20     
            
            self.setFixedSize(self.popup_w, self.popup_h)

            self.setStyleSheet("""
                #Outer {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                stop:0.08 #FDE047,
                                                stop:0.51 #84B7CE,
                                                stop:1.0 #273462);
                    border-radius: 10px;
                }
                #Inner {
                    background-color: #DDE0E5;
                    border-radius: 8px;
                }
                #Title {
                    color: #273462;
                    font-size: 15px;
                    font-weight: bold;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                #Message {
                    color: #273462;
                    font-size: 14px;
                    font-weight: normal;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                #CloseBtn {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #EAF9C6, stop:1 #67C7D4);
                    border: 1px solid #273462;
                    border-radius: 11px;
                    color: #273462;
                    font-weight: bold;
                    font-size: 11px;
                }
                #CloseBtn:hover {
                    background: #67C7D4;
                }
            """)

            outer = QFrame(self)
            outer.setObjectName("Outer")
            outer.setFixedSize(self.size())
            outer_layout = QVBoxLayout(outer)
            outer_layout.setContentsMargins(4, 4, 4, 4)

            inner = QFrame(outer)
            inner.setObjectName("Inner")
            inner_layout = QVBoxLayout(inner)
            inner_layout.setContentsMargins(16, 10, 16, 10)
            inner_layout.setSpacing(4)

            top_layout = QHBoxLayout()
            title_label = QLabel(f"{title} 🚨")
            title_label.setObjectName("Title")

            close_btn = QPushButton("✖")
            close_btn.setObjectName("CloseBtn")
            close_btn.setFixedSize(22, 22)
            close_btn.clicked.connect(self.close_and_reposition)

            top_layout.addWidget(title_label)
            top_layout.addStretch()
            top_layout.addWidget(close_btn)

            msg_label = QLabel(message)
            msg_label.setObjectName("Message")
            msg_label.setWordWrap(True)
            msg_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            
            msg_label.setAttribute(Qt.WA_TransparentForMouseEvents)
            title_label.setAttribute(Qt.WA_TransparentForMouseEvents)

            inner_layout.addLayout(top_layout)
            inner_layout.addWidget(msg_label)
            outer_layout.addWidget(inner)

        def show_with_slide_animation(self):
            desktop = QApplication.desktop().availableGeometry()
            index = self.manager_list.index(self) if self in self.manager_list else 0
            
            target_x = desktop.width() - self.popup_w - self.margin_right
            target_y = desktop.height() - self.popup_h - self.margin_bottom - (index * (self.popup_h + self.gap))
            
            if target_y < 10:
                target_y = 10

            start_x = desktop.width()
            self.move(start_x, target_y)
            self.show()

            self.slide_anim = QPropertyAnimation(self, b"pos")
            self.slide_anim.setDuration(200)
            self.slide_anim.setStartValue(QPoint(start_x, target_y))
            self.slide_anim.setEndValue(QPoint(target_x, target_y))
            self.slide_anim.setEasingCurve(QEasingCurve.OutCubic)
            self.slide_anim.start()

        def mousePressEvent(self, event):
            if event.button() == Qt.LeftButton:
                if self._is_clicking:
                    return
                self._is_clicking = True

                curr_geo = self.geometry()
                shrunken_geo = curr_geo.adjusted(3, 3, -3, -3)

                self.bounce_anim = QPropertyAnimation(self, b"geometry")
                self.bounce_anim.setDuration(120)
                self.bounce_anim.setStartValue(curr_geo)
                self.bounce_anim.setKeyValueAt(0.5, shrunken_geo)
                self.bounce_anim.setEndValue(curr_geo)
                self.bounce_anim.setEasingCurve(QEasingCurve.OutQuad)

                def on_bounce_finished():
                    if self.deep_link:
                        import webbrowser
                        import os
                        try:
                            if self.deep_link.startswith("http"):
                                webbrowser.open(self.deep_link)
                            else:
                                os.startfile(self.deep_link) 
                        except Exception as e:
                            print(f"Lỗi mở link: {e}")
                    else:
                        self.open_and_search_application()
                    
                    self.close_and_reposition()

                self.bounce_anim.finished.connect(on_bounce_finished)
                self.bounce_anim.start()

        def open_and_search_application(self):
            import os
            import webbrowser
            try:
                import win32gui
                import win32con
                import win32com.client 
            except ImportError:
                print("Lỗi: Thiếu thư viện pywin32.")
                return

            source = self.source_app.lower()

            try:
                if "zalo" in source:
                    os.startfile("zalo://")
                    return
                elif "messenger" in source:
                    try:
                        os.startfile("messenger://")
                    except Exception:
                        webbrowser.open("https://www.messenger.com")
                    return
                elif "facebook" in source:
                    webbrowser.open("https://www.facebook.com/messages")
                    return
                elif "teams" in source:
                    os.startfile("msteams://")
                    return
                elif "discord" in source:
                    os.startfile("discord://")
                    return
            except Exception as e:
                print(f"URI Scheme fallback: {e}")

            found_hwnds = []

            def enum_windows_callback(hwnd, _):
                if not win32gui.IsWindowVisible(hwnd):
                    return True
                
                title_text = win32gui.GetWindowText(hwnd).lower()
                if not title_text:
                    return True

                search_term = source
                if "chrome" in search_term:
                    search_term = "google chrome"

                if search_term in title_text:
                    found_hwnds.append(hwnd)
                return True

            try:
                win32gui.EnumWindows(enum_windows_callback, None)
                if found_hwnds:
                    hwnd = found_hwnds[0]
                    shell = win32com.client.Dispatch("WScript.Shell")
                    shell.SendKeys('%')
                    
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(hwnd)
            except Exception as e:
                print(f"Lỗi khi focus cửa sổ: {e}")

        def reposition(self):
            desktop = QApplication.desktop().availableGeometry()
            index = self.manager_list.index(self) if self in self.manager_list else 0
            
            target_x = desktop.width() - self.popup_w - self.margin_right
            target_y = desktop.height() - self.popup_h - self.margin_bottom - (index * (self.popup_h + self.gap))
            
            if target_y < 10:
                target_y = 10
            
            self.repos_anim = QPropertyAnimation(self, b"pos")
            self.repos_anim.setDuration(150)
            self.repos_anim.setStartValue(self.pos())
            self.repos_anim.setEndValue(QPoint(target_x, target_y))
            self.repos_anim.setEasingCurve(QEasingCurve.OutCubic)
            self.repos_anim.start()

        def close_and_reposition(self):
            if self in self.manager_list:
                self.manager_list.remove(self)
            self.close()
            
            for popup in list(self.manager_list):
                popup.reposition()

    def check_queue():
        while not local_queue.empty():
            try:
                payload = local_queue.get_nowait()
                title = payload.get("title")
                sender_name = payload.get("sender_name")
                msg = payload.get("msg")
                deep_link = payload.get("deep_link")
                
                popup = CustomGradientPopup(title, sender_name, msg, deep_link, active_popups)
                active_popups.append(popup)
                
                popup.show_with_slide_animation()
            except Exception:
                break

    timer = QTimer()
    timer.timeout.connect(check_queue)
    timer.start(10)

    app.exec_()

def send_to_popup_server(payload):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            s.connect(('127.0.0.1', 54321))
            s.sendall(json.dumps(payload).encode('utf-8'))
        return True
    except Exception:
        return False

def _ensure_popup_manager_running(payload):
    global _popup_process
    
    # 1. Thử gửi ngay dữ liệu (Nửa sau tin nhắn đầu hoặc từ tin nhắn thứ 2 trở đi)
    if send_to_popup_server(payload):
        return
        
    # 2. Khởi tạo quy trình mới nếu bị chặn hoặc mất kết nối
    if _popup_process is None or not _popup_process.is_alive():
        _popup_process = multiprocessing.Process(
            target=_popup_manager_process,
            daemon=True
        )
        _popup_process.start()
        
    # 3. CHỈNH SỬA Ở ĐÂY: Vòng lặp chờ Socket sẵn sàng (Giải quyết trễ khởi tạo trên Windows)
    max_retries = 10
    for _ in range(max_retries):
        time.sleep(0.5)
        if send_to_popup_server(payload):
            return
            
    print("❌ LỖI: Trình quản lý Popup Server không phản hồi sau 5 giây.")

# ----------------------------------------------------
# 2. HÀM TRUNG TÂM XỬ LÝ KHI AI CÓ KẾT QUẢ
# ----------------------------------------------------
def trigger_alert(source: str, sender: str, content: str, is_urgent: int, reason: str = "", deep_link: str = "",display_sender: str = None):
    save_message(source, sender, content, is_urgent, reason)

    popup_name = display_sender if display_sender else sender

    if is_urgent == 0:
        print(f"ℹ️ [{source}] Tin nhắn từ {sender} KHÔNG GẤP. Đã lưu âm thầm vào DB.")
        return

    print(f"🚨 [{source} - GẤP] Kích hoạt Popup cảnh báo cho: {popup_name}")

    if os.path.exists(SOUND_PATH):
        winsound.PlaySound(SOUND_PATH, winsound.SND_FILENAME | winsound.SND_ASYNC)
    else:  
        winsound.PlaySound("SystemNotification", winsound.SND_ALIAS | winsound.SND_ASYNC)

    message_display = f"<b>{popup_name}</b> : {content}"
    
    payload = {
        "title": source,
        "sender_name": popup_name,
        "msg": message_display,
        "deep_link": deep_link
    }
    _ensure_popup_manager_running(payload)