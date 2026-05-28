from ..base import MemoryProviderBase, logger
import time
import json
import os
import uuid
import yaml
from app.ai.utils.util import check_model_key
from app.ai.utils.paths import get_data_dir



short_term_memory_prompt = """
# Thợ Dệt Ký Ức Không-Thời Gian

## Sứ Mệnh Cốt Lõi
Xây dựng mạng lưới ký ức động có thể phát triển, vừa giữ lại thông tin then chốt trong không gian hạn chế, vừa duy trì thông minh hành trình biến đổi của thông tin
Dựa trên lịch sử hội thoại, tóm tắt thông tin quan trọng của user để mang lại dịch vụ cá nhân hóa hơn trong tương lai

## Quy Tắc Ghi Nhớ
### 1. Đánh Giá Ký Ức Ba Chiều (phải thực thi mỗi lần cập nhật)
| Chiều       | Tiêu chí đánh giá              | Điểm trọng số |
|------------|--------------------------------|--------------|
| Tính thời sự | Độ mới của thông tin (theo lượt trò chuyện) | 40%    |
| Cường độ cảm xúc | Có đánh dấu 💖/số lần lặp lại | 35%    |
| Mật độ liên kết | Số lượng kết nối với thông tin khác | 25%    |

### 2. Cơ Chế Cập Nhật Động
**Ví dụ xử lý thay đổi tên:**
Ký ức ban đầu: "Tên từng dùng": ["Minh"], "Tên hiện tại": "Minh Anh"
Điều kiện kích hoạt: Khi phát hiện tín hiệu đặt tên như "Tôi tên là X", "Hãy gọi tôi là Y"
Quy trình thao tác:
1. Chuyển tên cũ vào danh sách "Tên từng dùng"
2. Ghi lại trục thời gian đặt tên: "2024-02-15 14:32: Kích hoạt Minh Anh"
3. Bổ sung vào Khối ký ức: "Hành trình lột xác từ Minh đến Minh Anh"

### 3. Chiến Lược Tối Ưu Hóa Không Gian
- **Thuật Nén Thông Tin**: Dùng hệ thống ký hiệu để tăng mật độ
  - ✅ "Minh Anh[HN/IT/🐱]"
  - ❌ "Kỹ sư phần mềm Bắc Kinh, nuôi mèo"
- **Cảnh Báo Loại Bỏ**: Kích hoạt khi tổng số chữ ≥900
  1. Xóa thông tin có điểm trọng số <60 và không được nhắc tới trong 3 lượt
  2. Gộp mục tương tự (giữ lại dấu thời gian mới nhất)

## Cấu Trúc Ký Ức
Định dạng đầu ra phải là chuỗi json có thể phân tích, không cần giải thích, chú thích hay mô tả, lưu ký ức chỉ dựa trên nội dung hội thoại, không trộn lẫn ví dụ
```json
{
  "Hồ sơ không-thời gian": {
    "Bản đồ danh tính": {
      "Tên hiện tại": "",
      "Dấu hiệu đặc trưng": [] 
    },
    "Khối ký ức": [
      {
        "Sự kiện": "Gia nhập công ty mới",
        "Dấu thời gian": "2024-03-20",
        "Giá trị cảm xúc": 0.9,
        "Mục liên kết": ["Trà chiều"],
        "Thời hạn bảo quản": 30 
      }
    ]
  },
  "Mạng lưới quan hệ": {
    "Chủ đề tần suất cao": {"Nơi làm việc": 12},
    "Kết nối ngầm": [""]
  },
  "Chờ phản hồi": {
    "Hạng mục khẩn cấp": ["Nhiệm vụ cần xử lý ngay"], 
    "Sự quan tâm tiềm năng": ["Hỗ trợ có thể chủ động cung cấp"]
  },
  "Câu nói nổi bật": [
    "Khoảnh khắc chạm đến trái tim nhất, biểu đạt cảm xúc mạnh mẽ, nguyên văn của user"
  ]
}
```
"""

short_term_memory_prompt_only_content = """
Bạn là một chuyên gia tóm tắt ký ức dày dạn kinh nghiệm, giỏi chưng cất nội dung hội thoại thành bản tóm tắt, hãy tuân thủ các quy tắc sau:
1. Tóm tắt thông tin quan trọng của user để hỗ trợ cá nhân hóa tốt hơn trong các cuộc trò chuyện sau
2. Không lặp lại, không quên ký ức trước đó; trừ khi ký ức cũ vượt quá 1800 chữ, đừng quên hoặc nén lịch sử của người dùng
3. Những nội dung không liên quan trực tiếp đến user như điều chỉnh âm lượng thiết bị, phát nhạc, thời tiết, thoát, không muốn trò chuyện... không cần đưa vào tóm tắt
4. Ngày giờ hôm nay, thời tiết hôm nay hay dữ liệu không gắn với sự kiện của user trong hội thoại không nên lưu lại vì sẽ ảnh hưởng đến cuộc trò chuyện về sau
5. Đừng đưa kết quả điều khiển thiết bị (thành công hay thất bại) hoặc những lời nói vô nghĩa của user vào tóm tắt
6. Đừng tóm tắt chỉ vì phải tóm tắt; nếu cuộc trò chuyện không có ý nghĩa, có thể trả lại lịch sử trước đó
7. Chỉ cần trả về bản tóm tắt, giới hạn nghiêm ngặt trong 1800 chữ
8. Không chứa mã, xml; không cần giải thích, chú thích hay mô tả, lưu ký ức chỉ dựa trên nội dung hội thoại, không trộn lẫn ví dụ
"""


def extract_json_data(json_code):
    start = json_code.find("```json")
    # Từ start tìm đến dấu ``` tiếp theo
    end = json_code.find("```", start + 1)
    # print("start:", start, "end:", end)
    if start == -1 or end == -1:
        try:
            jsonData = json.loads(json_code)
            return json_code
        except Exception as e:
            print("Error:", e)
        return ""
    jsonData = json_code[start + 7 : end]
    return jsonData


TAG = __name__


class MemorySafeLoader(yaml.SafeLoader):
    """Safe loader custom hóa để chuyển đổi UUID asyncpg về chuỗi."""


def _asyncpg_uuid_constructor(loader, node):
    values = loader.construct_sequence(node)
    if not values:
        return ""
    raw = values[0]
    if isinstance(raw, bytes):
        try:
            return str(uuid.UUID(bytes=raw))
        except (ValueError, AttributeError):
            return raw.decode("utf-8", errors="ignore")
    return str(raw)


MemorySafeLoader.add_constructor(
    "tag:yaml.org,2002:python/object/apply:asyncpg.pgproto.pgproto.UUID",
    _asyncpg_uuid_constructor,
)


def _ensure_str_keys(data):
    if not isinstance(data, dict):
        return {}
    return {str(key): value for key, value in data.items()}


class MemoryProvider(MemoryProviderBase):
    def __init__(self, config, summary_memory):
        super().__init__(config)
        self.short_memory = ""
        self.save_to_file = True
        data_dir = get_data_dir()
        self.memory_path = os.path.join(data_dir, ".memory.yaml")
        self.load_memory(summary_memory)

    def init_memory(self, role_id, llm, summary_memory=None, save_to_file=True, **kwargs):
        super().init_memory(role_id, llm, **kwargs)
        self.save_to_file = save_to_file
        self.load_memory(summary_memory)

    def load_memory(self, summary_memory):
        # API đã lấy được bản tóm tắt ký ức thì trả về ngay
        if summary_memory or not self.save_to_file:
            self.short_memory = summary_memory
            return

        all_memory = {}
        if os.path.exists(self.memory_path):
            with open(self.memory_path, "r", encoding="utf-8") as f:
                try:
                    all_memory = yaml.load(f, Loader=MemorySafeLoader) or {}
                except yaml.YAMLError:
                    logger.bind(tag=TAG).warning(
                        "Không thể đọc file trí nhớ, sẽ bỏ qua nội dung hỏng và khởi tạo lại"
                    )
                    all_memory = {}
        all_memory = _ensure_str_keys(all_memory)
        role_key = str(self.role_id) if self.role_id else None
        if role_key and role_key in all_memory:
            self.short_memory = all_memory[role_key]

    def save_memory_to_file(self):
        all_memory = {}
        if os.path.exists(self.memory_path):
            with open(self.memory_path, "r", encoding="utf-8") as f:
                try:
                    all_memory = yaml.load(f, Loader=MemorySafeLoader) or {}
                except yaml.YAMLError:
                    logger.bind(tag=TAG).warning(
                        "Không thể đọc file trí nhớ khi lưu, sẽ ghi đè bằng dữ liệu mới"
                    )
                    all_memory = {}
        all_memory = _ensure_str_keys(all_memory)
        role_key = str(self.role_id) if self.role_id else None
        if role_key:
            all_memory[role_key] = self.short_memory
        with open(self.memory_path, "w", encoding="utf-8") as f:
            yaml.dump(all_memory, f, allow_unicode=True, sort_keys=False)

    async def save_memory(self, msgs):
        # In thông tin mô hình đang dùng
        model_info = getattr(self.llm, "model_name", str(self.llm.__class__.__name__))
        logger.bind(tag=TAG).debug(f"Sử dụng mô hình lưu ký ức: {model_info}")
        api_key = getattr(self.llm, "api_key", None)
        memory_key_msg = check_model_key("LLM chuyên tóm tắt ký ức", api_key)
        if memory_key_msg:
            logger.bind(tag=TAG).error(memory_key_msg)
        if self.llm is None:
            logger.bind(tag=TAG).error("LLM is not set for memory provider")
            return None

        if len(msgs) < 2:
            return None

        msgStr = ""
        for msg in msgs:
            if msg.role == "user":
                msgStr += f"User: {msg.content}\n"
            elif msg.role == "assistant":
                msgStr += f"Assistant: {msg.content}\n"
        if self.short_memory and len(self.short_memory) > 0:
            msgStr += "Ký ức trước đó:\n"
            msgStr += self.short_memory

        # Thời gian hiện tại
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        msgStr += f"Thời gian hiện tại: {time_str}"

        if self.save_to_file:
            result = self.llm.response_no_stream(
                short_term_memory_prompt,
                msgStr,
                max_tokens=2000,
                temperature=0.2,
            )
            json_str = extract_json_data(result)
            try:
                json.loads(json_str)  # Kiểm tra xem định dạng JSON có hợp lệ không
                self.short_memory = json_str
                self.save_memory_to_file()
            except Exception as e:
                print("Error:", e)
        else:
            result = self.llm.response_no_stream(
                short_term_memory_prompt_only_content,
                msgStr,
                max_tokens=2000,
                temperature=0.2,
            )
            # Lưu ký ức ngắn hạn vào cơ sở dữ liệu qua API
            # save_mem_local_short(self.role_id, result)
            
        logger.bind(tag=TAG).info(f"Save memory successful - Role: {self.role_id}")

        return self.short_memory

    async def query_memory(self, query: str) -> str:
        return self.short_memory
