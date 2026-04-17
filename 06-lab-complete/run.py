import os
import uvicorn

if __name__ == "__main__":
    # Lấy port từ môi trường, nếu không có thì mặc định 8000
    port_env = os.environ.get("PORT", "8000")
    
    # Ép kiểu sang int để đảm bảo không dính ký tự lạ
    try:
        port = int(port_env)
    except ValueError:
        # Xử lý trường hợp port bị dính ký tự xuống dòng \r hoặc khoảng trắng
        import re
        port = int(re.sub(r"\D", "", port_env))

    print(f"🚀 Starting server on port {port}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)