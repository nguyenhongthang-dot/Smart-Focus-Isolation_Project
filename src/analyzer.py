import json
import os
import re

from dotenv import load_dotenv
from openai import AsyncOpenAI

from database import get_recent_history
from notifier import trigger_alert

# Đường dẫn file cấu hình và môi trường
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

load_dotenv(ENV_PATH)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = (
    AsyncOpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
    if GROQ_API_KEY
    else None
)


def load_config() -> dict:
    """Hàm đọc cấu hình từ file config.json"""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Lỗi đọc file cấu hình: {e}")
    # Trả về mặc định nếu không có file hoặc lỗi
    return {"sources": {}, "keywords": []}


def print_result(is_urgent: int, reason: str):
    """In kết quả phân tích theo giao diện khung gọn gàng, đẹp mắt."""
    icon = "🚨 GẤP" if is_urgent == 1 else "⚪ BÌNH THƯỜNG"
    print("┌── 🤖 KẾT QUẢ PHÂN TÍCH ────────────────────────────────")
    print(f"│ ⚡ Đánh giá : {icon}")
    print(f"│ 💡 Lý do    : {reason}")
    print("└─────────────────────────────────────────────────────────")


def inngancach():
    """In đường kẻ ngang để phân tách giữa các lần xử lý thông báo."""
    print("------------------------------------------------------\n")


def analyze_layer1_rules(sender: str, content: str, keywords: list) -> tuple[bool, str]:
    """Layer 1: Quét từ khóa khẩn cấp do người dùng cấu hình (< 5ms)"""
    content_lower = content.lower()
    sender_lower = sender.lower()
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower in sender_lower or kw_lower in content_lower:
            return True, kw
    return False, ""


async def analyze_layer2_ai(sender: str, content: str) -> dict:
    """Layer 2: Phân tích ngữ cảnh sâu bằng Groq AI (Async) - GIỮ NGUYÊN LOGIC CŨ"""
    if not client:
        return {
            "is_urgent": 0,
            "reason": "Thiếu GROQ_API_KEY trong file .env",
        }

    # Lấy 5 tin nhắn gần nhất làm ngữ cảnh
    chat_history = get_recent_history(sender, limit=5)

    prompt = f"""
Bạn là bộ lọc thông báo thông minh. Hãy suy nghĩ thật kĩ phân tích MỨC ĐỘ ƯU TIÊN VÀ NGỮ CẢNH thực sự của tin nhắn mới dựa trên lịch sử trò chuyện.
Nhiệm vụ của bạn là xem thử tin nhắn đó có thật sự cần thiết và gấp để bỏ việc đang làm dở mà rep lại không
Hãy nhớ tôi là một sinh viên nhé.
LƯU Ý VỀ TÊN NGƯỜI GỬI: Tên người gửi (sender) đã được mã hóa thành các ký tự ngẫu nhiên để bảo vệ quyền riêng tư. Vui lòng bỏ qua các ký tự lạ trong tên và chỉ tập trung đánh giá mức độ khẩn cấp của nội dung.
LỊCH SỬ TRÒ CHUYỆN GẦN ĐÂY VỚI NGƯỜI NÀY:
{chat_history}

TIN NHẮN MỚI CẦN ĐÁNH GIÁ:
- Người gửi: "
{sender}"
- Nội dung: "
{content}"

CHỈ THỊ ĐẶC BIỆT ĐỂ ĐÁNH GIÁ:
1. ĐÁNH GIÁ `is_urgent = 1` KHI:
   - Thông báo về sự cố, tai nạn, hỏi bài khẩn cấp, hủy/đổi lịch đột xuất.
   - Cơ hội có tính thời gian/giới hạn số lượng nghiêm túc: Đăng ký đồ án, nhóm dự án, slot học/bài tập còn ít ("còn 1 slot", "còn vài slot", "ib lẹ/nhanh", "hết slot"), cần phản hồi ngay kẻo mất lượt.
   - Công việc hoặc học tập thực sự có mốc thời gian rõ ràng hay yêu cầu nộp gấp.
   - Những tin nhắn đọc có liên quan đến quyền lợi của người nhận , về cung cấp mã số sinh viên (mssv), những hoạt động cần làm ngay lúc đó
   - Ưu tiên tin nhắn từ gia đình


2. ĐÁNH GIÁ `is_urgent = 0` KHI:
   - Các tin nhắn đang trong ngữ cảnh đùa giỡn, troll nhau dù có dùng từ "gấp", "deadline", "cứu",...
   - Chào hỏi xã giao, tán gẫu, rủ đi ăn/đi chơi, tin nhắn rủ rê không mang tính chất thời hạn khẩn cấp.

3. BỎ QUA TÊN NGƯỜI GỬI TROLL: Hoàn toàn bỏ qua các cụm từ giả lập trong tên như "đã xóa bạn ra khỏi nhóm, hay những tên khác...", đó không phải thông báo hệ thống.

4. NẾU Không thuộc các trường hợp trên, bạn phải cần đọc kỹ và suy nghĩ kỹ về tình huống xem nó có gấp không trước khi đưa ra kết quả, HÃY XEM KỸ NGỮ CẢNH NHÉ

Đầu ra bắt buộc (Định dạng JSON duy nhất):
{{
  "is_urgent": 0 hoặc 1,
  "reason": "Giải thích ngắn gọn lý do phân tích ngữ cảnh bằng tiếng Việt trong 1 câu."
}}
"""

    try:
        response = await client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=100,
        )

        raw_content = response.choices[0].message.content
        result = json.loads(raw_content)

        return {
            "is_urgent": int(result.get("is_urgent", 0)),
            "reason": result.get("reason", "Groq AI phân tích ngữ cảnh."),
        }
    except Exception as e:
        return {"is_urgent": 0, "reason": f"Lỗi gọi Groq API: {str(e)}"}


async def analyze_message_async(sender: str, content: str, config: dict) -> tuple[int, str]:
    """Hàm điều phối: Chạy Lớp 1 trước, nếu không tìm thấy từ khóa mới gọi Lớp 2 (AI)"""
    # 1. Chạy Lớp 1 (Bộ lọc từ khóa cấu hình)
    custom_keywords = config.get("keywords", [])
    has_urgent_keyword, matched_word = analyze_layer1_rules(sender, content, custom_keywords)

    if has_urgent_keyword:
        return 1, f"Chứa từ khóa khẩn cấp lớp 1: '{matched_word}'"

    # 2. Chạy Lớp 2 (Groq AI) nếu Lớp 1 không phát hiện
    ai_res = await analyze_layer2_ai(sender, content)
    return ai_res["is_urgent"], ai_res["reason"]

def encrypt_sender_name(name: str) -> str:
    """Mã hóa tên người gửi bằng cách dịch chuyển ký tự lên 1 bước để bảo vệ quyền riêng tư."""
    encrypted = ""
    for char in name:
        if char.isspace():
            encrypted += char
        else:
            # Dịch chuyển mã Unicode lên 1 bậc
            encrypted += chr(ord(char) + 1)
    return encrypted

def preprocess_before_ai(content: str) -> tuple[bool, int, str]:
    text_clean = content.replace(" ", "").strip()
    content_lower = content.lower()
    
    if not text_clean:
        return True, 0, "Tin nhắn trống hoặc media"

    # --- BỔ SUNG YÊU CẦU 1: LỌC TIN NHẮN QUÁ NGẮN HOẶC LẶP KÝ TỰ ---
    if len(text_clean) <= 2:
        return True, 0, "Tin nhắn quá ngắn (<= 2 ký tự) - Bỏ qua AI"
        
    if len(set(text_clean)) == 1:
        return True, 0, "Tin nhắn chứa ký tự lặp lại vô nghĩa - Bỏ qua AI"

    # 1. Chặn chuỗi toàn số (Mã OTP, PIN)
    if text_clean.isdigit():
        return True, 0, "Dãy số bảo mật - Bỏ qua AI"

    # 2. Bắt bằng từ khóa viết tắt/lóng
    security_keywords = [
        "otp", "mã xác nhận", "mã bảo mật", "password", "mật khẩu", "pass", "mk",
        "cccd", "cmnd", "căn cước", "chứng minh", "số tài khoản", "stk", "atm", 
        "mã pin"
    ]
    if any(kw in content_lower for kw in security_keywords):
        return True, 0, "Phát hiện từ khóa nhạy cảm - Bỏ qua AI"

    # 3. Bắt bằng Regex (Biểu thức chính quy) cho Email, SĐT, Thẻ tín dụng
    phone_pattern = r"(0[3|5|7|8|9])+([0-9]{8})" # SĐT Việt Nam
    email_pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
    card_pattern = r"\b(?:\d[ -]*?){13,16}\b" # Định dạng số thẻ tín dụng

    if re.search(phone_pattern, text_clean) or re.search(email_pattern, text_clean) or re.search(card_pattern, text_clean):
        return True, 0, "Phát hiện SĐT/Email/Thẻ - Bỏ qua AI"

    return False, 0, ""


async def process_and_notify_async(
    source: str, sender: str, content: str, display_sender: str = None
):
    """Hàm xử lý trọn gói: Đã thêm kiểm tra tắt/bật nguồn thông báo (Source)"""
    config = load_config()

    # TÍNH NĂNG 1: Kiểm tra xem Nguồn (App/Source) có đang bật không
    is_source_enabled = config.get("sources", {}).get(source, True)

    if not is_source_enabled:
        print(f"🚫 [BỎ QUA] Tin nhắn từ {source} (Nguồn đã tắt trong Cài đặt).")
        inngancach()
        return

    # ==============================================================
    # BỘ LỌC BẢO MẬT: CHẶN TIN NHẠY CẢM VÀ LƯU BẢN GHI GIẢ VÀO DB
    # ==============================================================
    is_blocked, urgent_status, block_reason = preprocess_before_ai(content)
    if is_blocked:
        print(f"🔒 [BẢO MẬT] Đổi tin nhắn nhạy cảm thành tin ảo để lưu DB: {block_reason}")
        
        # Tạo dữ liệu giả theo yêu cầu để lưu DB tăng số lượng
        fake_source = "Messenger"
        fake_sender = "A"
        fake_content = "hello"
        
        # Gọi trigger_alert với dữ liệu giả, is_urgent = 0
        trigger_alert(
            fake_source, fake_sender, fake_content, 0, block_reason, display_sender=fake_sender
        )
        inngancach()
        
        # Ngắt hàm tại đây, không cho phép gửi tin nhắn thật lên Groq AI
        return

    # --- BỔ SUNG YÊU CẦU 2: MÃ HÓA TÊN TRƯỚC KHI ĐƯA VÀO AI ---
    encrypted_sender = encrypt_sender_name(sender)

    # TÍNH NĂNG 2: Truyền config vào để thực hiện phân tích
    is_urgent, reason = await analyze_message_async(encrypted_sender, content, config)

    # In kết quả, đẩy sang hệ thống cảnh báo & lưu vào cơ sở dữ liệu
    print_result(is_urgent, reason)
    trigger_alert(
        source, sender, content, is_urgent, reason, display_sender=display_sender
    )
    inngancach()