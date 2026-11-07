import os
import subprocess
import time

def open_dnd_settings() -> bool:
    """
    Mở trang Cài đặt thông báo của Windows và dùng Win32 API 
    để ép cửa sổ nhảy lên đè trước màn hình 100%.
    """
    try:
        # 1. Mở trang cài đặt Windows
        subprocess.Popen('start ms-settings:notifications', shell=True)
        
        # 2. Dùng một luồng nhỏ chờ 0.5 giây để Windows kịp khởi tạo cửa sổ, 
        # sau đó tìm và ép nó hiện đè lên trên cùng
        def bring_to_front():
            time.sleep(0.5)
            try:
                import win32gui
                import win32con

                def enum_windows_callback(hwnd, _):
                    if not win32gui.IsWindowVisible(hwnd):
                        return True
                    title = win32gui.GetWindowText(hwnd).lower()
                    # Tìm cửa sổ Settings hoặc Thông báo của Windows
                    if title in ["settings", "cài đặt"]:
                        try:
                            # Khôi phục cửa sổ nếu bị thu nhỏ và ép lên foreground trực tiếp
                            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                            win32gui.SetWindowPos(
                                hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW
                            )
                            win32gui.SetWindowPos(
                                hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
                                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW
                            )
                            win32gui.SetForegroundWindow(hwnd)
                            return False # Đã tìm thấy và xử lý xong thì dừng
                        except Exception:
                            pass
                    return True

                win32gui.EnumWindows(enum_windows_callback, None)
            except Exception as e:
                print(f"[DND Focus Error]: {e}")

        import threading
        threading.Thread(target=bring_to_front, daemon=True).start()

        print("[DND] Đã mở và ép cửa sổ Cài đặt Windows hiển thị đè lên màn hình thành công.")
        return True
    except Exception as e:
        print(f"[DND LỖI]: Không thể mở Cài đặt Windows: {e}")
        return False

    if __name__ == "__main__":
        open_dnd_settings()