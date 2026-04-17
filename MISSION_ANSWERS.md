#  Delivery Checklist — Day 12 Lab Submission

> **Student Name:**  Vũ Quang Dũng 
> **Student ID:** 2A202600442  
> **Date:** 17/04/2026

---

##  Submission Requirements

Submit a **GitHub repository** containing:

### 1. Mission Answers (40 points)

Create a file `MISSION_ANSWERS.md` with your answers to all exercises:

```markdown
# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found
1. **Hardcoded Secrets**: API Key và link Database được ghi trực tiếp trong mã nguồn (`OPENAI_API_KEY`, `DATABASE_URL`), dễ bị lộ khi push code lên GitHub.
2. **Thiếu Quản lý Cấu hình (Config Management)**: Các biến cấu hình (`DEBUG`, `MAX_TOKENS`) chưa được tách biệt ra file môi trường (.env), gây khó khăn khi thay đổi môi trường chạy.
3. **Sử dụng print thay vì Logging chuyên nghiệp**: Việc `print` ra cả secret key trong log là một lỗ hổng bảo mật nghiêm trọng.
4. **Thiếu Health Check Endpoint**: Không có endpoint để hệ thống quản lý cloud (như Railway) kiểm tra xem ứng dụng có đang hoạt động tốt hay đã chết để restart.
5. **Cấu hình host và port cố định**: Fix cứng `host="localhost"` và `port=8000` khiến ứng dụng không thể nhận các kết nối từ bên ngoài hoặc nhận biến Port động từ nền tảng Cloud.
6. **Bật chế độ Reload trong Production**: `reload=True` gây tốn tài nguyên và không ổn định khi chạy trên môi trường thật.

### Exercise 1.3: Comparison table
| Feature | Develop | Production | Why Important? |
|---------|---------|------------|----------------|
| **Config Management** | Hardcoded trong source code. | Load từ Environment Variables qua Pydantic Settings. | Giúp bảo mật secret code và dễ dàng thay đổi cấu hình mà không cần sửa code. |
| **Logging** | Sử dụng `print()` đơn giản, log cả secret. | Structured JSON Logging, KHÔNG log secret. | Dễ dàng quản lý, truy vết lỗi bằng các công cụ tập trung (Datadog, Loki) và bảo mật dữ liệu. |
| **Health Check** | Không có. | Có endpoint `/health`, `/ready`, `/metrics`. | Cần thiết để các nền tảng Cloud (Railway, K8s) theo dõi trạng thái và tự động restart nếu app crash. |
| **Network/Port** | Fix cứng `localhost:8000`. | Bind `0.0.0.0` và nhận Port động từ môi trường. | Để container có thể nhận traffic từ internet và tương thích với mọi nền tảng Hosting. |
| **Shutdown** | Tắt đột ngột (Hard kill). | Xử lý tín hiệu `SIGTERM` và Graceful Shutdown. | Đảm bảo các request đang xử lý được hoàn tất trước khi tắt app, tránh mất mát dữ liệu hoặc lỗi cho người dùng. |
| **CORS** | Không được cấu hình. | Cấu hình tường minh các domain được phép truy cập. | Ngăn chặn các trang web lạ gọi API trái phép, tăng cường bảo mật trình duyệt. |

## Part 2: Docker

### Exercise 2.1: Dockerfile questions
1. **Base image là gì?** Là một image mẫu có sẵn chứa hệ điều hành và các môi trường cần thiết (ở đây là `python:3.11`) để làm nền tảng xây dựng ứng dụng lên trên.
2. **Working directory là gì?** Là thư mục làm việc mặc định bên trong container (lệnh `WORKDIR /app`). Mọi câu lệnh sau đó (`COPY`, `RUN`, `CMD`) sẽ được thực thi tại thư mục này.
3. **Tại sao COPY requirements.txt trước?** Để tận dụng **Docker Layer Cache**. Khi code thay đổi nhưng dependencies không đổi, Docker sẽ bỏ qua bước `pip install` giúp build image nhanh hơn rất nhiều.
4. **CMD vs ENTRYPOINT khác nhau thế nào?** `CMD` cung cấp lệnh mặc định và tham số cho container, có thể bị ghi đè dễ dàng khi chạy `docker run`. `ENTRYPOINT` cũng chạy lệnh khi start nhưng khó bị ghi đè hơn, thường dùng để biến container thành một file thực thi cố định.
### Exercise 2.3: Image size comparison
- Develop: 1.66 GB
- Production: ~160 MB
- Difference: ~90%

#### Giải thích Multi-stage build:
1. **Stage 1 (Builder) làm gì?** Dùng để cài đặt các công cụ build (gcc, libpq-dev) và compile các dependencies. Stage này chứa đầy đủ các file rác phát sinh trong quá trình cài đặt.
2. **Stage 2 (Runtime) làm gì?** Chỉ copy những kết quả cuối cùng (thư viện đã cài xong) từ Stage 1 sang một image cực kỳ tinh giản (`python:3.11-slim`). Stage này hoàn toàn không chứa build tools hay cache của pip.
3. **Tại sao image nhỏ hơn?** 
   - Sử dụng base image là bản `-slim` thay vì bản full (giảm từ ~1GB xuống ~100MB).
   - Loại bỏ hoàn toàn các dependencies dùng để build (compiler, caches, temporary files) chỉ có ở Stage 1.
   - Không chứa các file thừa từ hệ điều hành không cần thiết cho việc chạy ứng dụng Python.

### Exercise 2.4: Docker Compose stack


#### Services & Communication
1. **Các dịch vụ (Services) được khởi động:**
   - **`agent`**: Ứng dụng AI chính chạy bằng FastAPI.
   - **`redis`**: Hệ thống cache để quản lý session và giới hạn tốc độ (rate limiting).
   - **`qdrant`**: Vector Database phục vụ cho các tác vụ RAG (truy xuất thông tin).
   - **`nginx`**: Đóng vai trò Reverse Proxy và Load Balancer, là cửa ngõ duy nhất tiếp nhận traffic từ ngoài vào.

2. **Cách giao tiếp (Communication):**
   - Các dịch vụ được kết nối qua một mạng nội bộ chung mang tên **`internal`**. 
   - Thay vì dùng địa chỉ IP, chúng liên lạc với nhau thông qua **Service Name** (ví dụ: Agent kết nối tới Redis qua địa chỉ `redis:6379`).
   - `nginx` là dịch vụ duy nhất mở cổng (80/443) ra bên ngoài internet. Các dịch vụ khác hoàn toàn bị cô lập trong mạng nội bộ để đảm bảo an toàn bảo mật.
   - `agent` chỉ khởi động sau khi `redis` và `qdrant` ở trạng thái "healthy" nhờ cấu hình `depends_on`.

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment
- URL: https://nhom89-e403-day12-production.up.railway.app
- Screenshot: [extras\railway-url.png]

## Part 4: API Security

### Exercise 4.1-4.3: Test results
### Exercise 4.1: API Key authentication (develop)

- **API key được check ở đâu?**
  - Trong hàm `verify_api_key()` của `04-api-gateway/develop/app.py`.
  - Endpoint `/ask` dùng `Depends(verify_api_key)` nên bắt buộc có header `X-API-Key`.

- **Điều gì xảy ra nếu sai key / thiếu key?**
  - Thiếu key -> `401 Unauthorized`.
  - Sai key -> `403 Forbidden` (theo code).

- **Làm sao rotate key?**
  - Đổi biến môi trường `AGENT_API_KEY` rồi restart service (không hardcode trong code).


```bash
# Không có key
HTTP/1.1 401 Unauthorized

# Có key nhưng gửi JSON body thay vì query param question
HTTP/1.1 422 Unprocessable Entity
{"detail":[{"type":"missing","loc":["query","question"],"msg":"Field required","input":null}]}

# Có key + đúng format endpoint (/ask?question=Hello)
HTTP/1.1 200 OK
{"question":"Hello","answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé."}
```

Kết luận 4.1: Cơ chế API key hoạt động đúng theo thiết kế (thiếu key -> 401, sai format request -> 422, đúng key + đúng tham số -> 200).

### Exercise 4.2: JWT authentication (production)

- **JWT flow (theo `auth.py`):**
  - `POST /auth/token` với username/password hợp lệ -> trả `access_token`.
  - Gọi `/ask` với header `Authorization: Bearer <token>`.
  - Server verify chữ ký + hạn token, sau đó lấy `username`, `role` từ payload.

- **Test output đã chạy trong terminal (sau khi sửa package JWT + dùng Invoke-RestMethod)(Do gặp lỗi (52) Empty reply from server nên sửa lại câu lệnh trên powershell):**
```powershell
$tokenResp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/auth/token" -Method Post -ContentType "application/json" -Body (@{ username = "student"; password = "demo123" } | ConvertTo-Json -Compress); $TOKEN = $tokenResp.access_token; $tokenResp; "TOKEN_LEN=$($TOKEN.Length)"

------------
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
TOKEN_LEN=168

Invoke-RestMethod -Uri "http://127.0.0.1:8000/ask" -Method Post -Headers @{ Authorization = "Bearer $TOKEN" } -ContentType "application/json" -Body (@{ question = "Explain JWT" } | ConvertTo-Json -Compress)

question    answer                                                                             usage
--------    ------                                                                             -----
Explain JWT Agent  Đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé. @{requests_remaining=9; budget_...
```

- **Quan sát:**
  - Lấy token thành công (`TOKEN_LEN=168`), chứng minh JWT flow hoạt động.
  - Gọi `/ask` thành công và trả về `question`, `answer`, `usage`.
  - Chuỗi tiếng Việt trong cột `answer` bị lỗi hiển thị encoding trên terminal PowerShell, không phải lỗi logic API.

### Exercise 4.3: Rate limiting

- **Algorithm dùng:** Sliding Window Counter (deque timestamps) trong `rate_limiter.py`.
- **Limit:**
  - User: `10 requests / 60s`
  - Admin: `100 requests / 60s`
- **Bypass cho admin:** không tắt limit hoàn toàn, mà chuyển sang `rate_limiter_admin` (limit cao hơn) khi `role == "admin"`.

- **Test output đã chạy trong terminal (20 requests):**
```powershell
1..20 | ForEach-Object { try { $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/ask" -Method Post -Headers @{ Authorization = "Bearer $TOKEN" } -ContentType "application/json" -Body (@{ question = "Test $" } | ConvertTo-Json -Compress) -ErrorAction Stop; "REQ $ => $($r.StatusCode)" } catch { if ($.Exception.Response) { ... } } }

Security Warning: Script Execution Risk
...
REQ $ => 200
REQ $ => 200
REQ $ => 200
REQ $ => 200
REQ $ => 200
REQ $ => 200
REQ $ => 200
REQ $ => 200
REQ $ => 200

ERROR:    rate_limiter.py: Rate limit exceeded for user: student
```

- **Quan sát:**
  - Các request đầu trả `200`.
  - Script test bị lỗi cú pháp PowerShell ở khối `catch` (`$.Exception.Response` thay vì `$_.Exception.Response`), nên khi bắt đầu vào nhánh lỗi thì không in được status code thực tế.
  - Có cảnh báo `Script Execution Risk` của `Invoke-WebRequest`; đây là cảnh báo của PowerShell, không phải lỗi API.

- **Kết luận 4.3:**
  - Cấu hình limit trong code vẫn đúng: user 10 req/60s, admin 100 req/60s.
  - Chạy được khoảng vài câu thì bị rate limit. 

### Exercise 4.4: Cost guard implementation
Hàm `check_budget(self, user_id: str)` được dùng để chặn request trước khi gọi LLM nhằm tránh vượt chi phí.

1. **Lấy dữ liệu chi phí theo user**
  - `record = self._get_record(user_id)` lấy tổng chi phí hiện tại của user trong ngày (`record.total_cost_usd`).

2. **Kiểm tra ngân sách toàn hệ thống (Global budget)**
  - Nếu `self._global_cost >= self.global_daily_budget_usd` thì hệ thống đã chạm trần chi phí ngày.
  - App ghi log mức `critical` để cảnh báo nghiêm trọng.
  - Trả về `HTTPException(503)` với thông điệp tạm ngừng dịch vụ do hết budget.
  - Ý nghĩa: bảo vệ tổng chi phí vận hành, tránh phát sinh vượt mức cho toàn bộ service.

3. **Kiểm tra ngân sách theo từng user (Per-user budget)**
  - Nếu `record.total_cost_usd >= self.daily_budget_usd` thì user đã dùng hết quota trong ngày.
  - Trả về `HTTPException(402)` (Payment Required), kèm chi tiết:
    - `used_usd`: số tiền đã dùng
    - `budget_usd`: hạn mức ngày
    - `resets_at`: thời điểm reset quota (`midnight UTC`)
  - Ý nghĩa: ngăn 1 user tiêu tốn quá mức và đảm bảo công bằng tài nguyên.

4. **Cảnh báo khi gần hết budget**
  - Nếu user đã dùng đến ngưỡng cảnh báo `daily_budget_usd * warn_at_pct` (ví dụ 80%) thì ghi log `warning`.
  - Không chặn request ở bước này, chỉ cảnh báo để theo dõi và chủ động can thiệp.

Tóm lại, cơ chế này áp dụng **2 lớp bảo vệ chi phí** (toàn hệ thống + theo user), trả mã lỗi rõ ràng để client xử lý, đồng thời có cảnh báo sớm trước khi vượt ngưỡng.

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Implementation notes
#### Exercise 5.1: Health & Readiness endpoints (đã implement)

1. **`GET /health` (Liveness probe)**
  - Mục tiêu: kiểm tra process còn sống để platform quyết định có cần restart container hay không.
  - Endpoint luôn trả về HTTP `200` khi app còn chạy và trả JSON trạng thái vận hành.
  - Thông tin trả về gồm:
    - `status`: `ok` hoặc `degraded` (dựa trên các check nội bộ)
    - `uptime_seconds`: thời gian chạy từ lúc start
    - `environment`, `timestamp`
    - `checks`: thông tin kiểm tra phụ trợ (ví dụ memory/dependency)
  - Ý nghĩa thực tế: nếu endpoint này fail/timeout, hệ thống orchestration sẽ xem instance là "chết" và tự restart.

2. **`GET /ready` (Readiness probe)**
  - Mục tiêu: kiểm tra instance đã sẵn sàng nhận traffic hay chưa.
  - Logic:
    - Nếu cờ sẵn sàng chưa bật (`_is_ready == False`) -> trả `HTTP 503` (Not Ready).
    - Nếu đã sẵn sàng -> trả `HTTP 200` với payload `{"ready": true}` (kèm thông tin runtime như `in_flight_requests` tùy phiên bản).
  - Ý nghĩa thực tế: load balancer chỉ route request vào instance khi `/ready` trả `200`; nếu `503` thì tạm ngừng route để tránh lỗi cho người dùng.

3. **Tại sao cần cả 2 endpoint thay vì chỉ 1 endpoint?**
  - `/health`: trả lời câu hỏi "process còn sống không?"
  - `/ready`: trả lời câu hỏi "process có sẵn sàng phục vụ request không?"
  - Tách riêng giúp hệ thống triển khai rolling update và autoscaling an toàn hơn (container có thể còn sống nhưng chưa sẵn sàng nhận traffic).

4. **Kết luận 5.1**
  - Cặp endpoint này giúp giảm downtime và tránh route nhầm vào instance đang khởi động/chưa ổn định.
  - Đây là nền tảng quan trọng cho deployment production trên Railway/Render/Kubernetes.

#### Exercise 5.4: Load balancing

1. **Kết quả chạy stack với Nginx**
  - `docker compose up --scale agent=3` đã khởi tạo 3 agent instances.
  - Nginx phân tán request qua nhiều replica thay vì dồn vào một container.
  - Output thực tế từ request loop:

```powershell
n served_by       session_id                           turn
- ---------       ----------                           ----
1 instance-4d051f 212c094c-091c-4867-85c1-98f0c89af64f    2
2 instance-4755b9 212c094c-091c-4867-85c1-98f0c89af64f    3
3 instance-4a0932 212c094c-091c-4867-85c1-98f0c89af64f    4
4 instance-4d051f 212c094c-091c-4867-85c1-98f0c89af64f    5
5 instance-4755b9 212c094c-091c-4867-85c1-98f0c89af64f    6
```

2. **Nếu 1 instance die thì sao?**
  - Trong mô hình này, traffic vẫn có thể đi sang các instance còn sống vì nginx chỉ route đến upstream healthy.
  - Thực tế trong quá trình test, 3 replica đã cùng phục vụ request và state không nằm trong từng container.

3. **Kết luận 5.4**
  - Load balancing hoạt động đúng: request được phân tán giữa 3 agents.
  - Hệ thống có khả năng tiếp tục phục vụ khi một instance không còn sẵn sàng, miễn các instance khác vẫn healthy.

#### Exercise 5.5: Test stateless

1. **Script làm gì**
  - `python test_stateless.py` tạo một conversation mới, gửi 5 câu hỏi liên tiếp, rồi đọc history của session từ Redis.
  - Đây là test để kiểm tra state có bị mất khi request đi qua nhiều instance hay không.

2. **Kết quả chạy thật**
  - Output thực tế:

```text
============================================================
Stateless Scaling Demo
============================================================

Session ID: c56a177a-c9ca-4b0e-b9fa-e491b265b6cf

Request 1: [instance-4d051f]
  Q: What is Docker?
  A: Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!...

Request 2: [instance-4755b9]
  Q: Why do we need containers?
  A: Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ O...

Request 3: [instance-4a0932]
  Q: What is Kubernetes?
  A: Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận....

Request 4: [instance-4d051f]
  Q: How does load balancing work?
  A: Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ O...

Request 5: [instance-4755b9]
  Q: What is Redis used for?
  A: Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé....

------------------------------------------------------------
Total requests: 5
Instances used: {'instance-4a0932', 'instance-4755b9', 'instance-4d051f'}
✅ All requests served despite different instances!

--- Conversation History ---
Total messages: 10
  [user]: What is Docker?...
  [assistant]: Container là cách đóng gói app để chạy ở mọi nơi. Build once...
  [user]: Why do we need containers?... 
  [assistant]: Đây là câu trả lời từ AI agent (mock). Trong production, đây...
  [user]: What is Kubernetes?...
  [assistant]: Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã đư...
  [user]: How does load balancing work?...
  [assistant]: Đây là câu trả lời từ AI agent (mock). Trong production, đây...
  [user]: What is Redis used for?...
  [assistant]: Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đ...

✅ Session history preserved across all instances via Redis!
```

3. **Nếu kill random instance thì sao?**
  - Conversation vẫn còn vì history/session được lưu trong Redis, không phụ thuộc vào RAM của từng container.
  - Khi request tiếp theo đi sang instance khác, nó vẫn load lại được cùng session_id và tiếp tục hội thoại.

4. **Kết luận 5.5**
  - Test stateless thành công: conversation vẫn giữ nguyên dù requests đi qua nhiều instance.
  - Việc tách state ra Redis giúp hệ thống chịu được đổi instance, restart, hoặc scale ngang tốt hơn.

#### Exercise 5.2: Graceful shutdown (signal handler)

1. **Giải pháp đã implement trong code**
  - Tạo file `signal_handler.py` và đăng ký xử lý `SIGTERM`/`SIGINT`.
  - Luồng xử lý khi nhận signal:
    - (1) Stop accepting new requests: bật cờ không nhận request mới.
    - (2) Finish current requests: chờ request đang xử lý hoàn tất (có timeout).
    - (3) Close connections: thực hiện cleanup kết nối/tài nguyên.
    - (4) Exit: thoát process sau khi hoàn tất shutdown.

2. **Test đã chạy (thực tế trên máy local)**
  - Chạy app ở develop và gửi request `/ask?question=Long task` đồng thời gửi signal tắt ngay sau đó.
  - Kết quả lần test "kill ngay lập tức":
    - `REQUEST_STDERR = curl: (56) Recv failure: Connection was reset`
    - Kết luận: request **không hoàn thành** trong kịch bản race cực nhanh này.

3. **Quan sát bổ sung**
  - Khi delay rất ngắn trước khi signal (đủ để request bắt đầu xử lý), request có thể trả về `200` trước khi process dừng.
  - Điều này phù hợp bản chất race-condition của shutdown test: nếu signal tới trước khi request vào pipeline, client có thể nhận reset kết nối.

4. **Kết luận 5.2**
  - Signal handler đã được tích hợp và hoạt động theo mô hình graceful shutdown.
  - Tuy nhiên trong kịch bản "kill ngay lập tức", vẫn có khả năng request không hoàn tất do race timing; đây là hành vi thực tế cần được chấp nhận và ghi nhận trong báo cáo test.

#### Exercise 5.3: Stateless design

1. **Anti-pattern (state trong memory)**
  - Nếu lưu `conversation_history = {}` trong RAM của từng instance, khi scale nhiều instance thì mỗi instance có state riêng.
  - Hệ quả: request 1 đi vào instance A, request 2 đi vào instance B thì mất ngữ cảnh hội thoại, gây lỗi logic chat multi-turn.

2. **Solution đã implement (state trong Redis)**
  - Refactor phần session/history sang Redis bằng các hàm:
    - `save_session(session_id, data)`
    - `load_session(session_id)`
    - `append_to_history(session_id, role, content)`
  - Endpoint `/chat` đọc và ghi history theo `session_id` trong Redis thay vì giữ state cục bộ trong process.
  - Endpoint `/chat/{session_id}/history` và `DELETE /chat/{session_id}` cũng thao tác trực tiếp trên Redis key `session:<session_id>`.

3. **Vì sao stateless giúp scale tốt hơn**
  - Bất kỳ instance nào sau load balancer cũng có thể xử lý request vì state đã nằm ở shared store (Redis).
  - Khi scale ngang (N instances), user vẫn giữ được hội thoại liên tục.
  - Khi 1 instance restart/crash, state không mất vì không nằm trong memory của instance đó.

4. **Kết luận 5.3**
  - Thiết kế stateless với Redis đã giải quyết đúng bài toán scaling reliability.
  - Đây là điều kiện bắt buộc để triển khai production với nhiều replicas phía sau load balancer.
```

---

### 2. Full Source Code - Lab 06 Complete (60 points)

Your final production-ready agent with all files:

```
your-repo/
├── app/
│   ├── main.py              # Main application
│   ├── config.py            # Configuration
│   ├── auth.py              # Authentication
│   ├── rate_limiter.py      # Rate limiting
│   └── cost_guard.py        # Cost protection
├── utils/
│   └── mock_llm.py          # Mock LLM (provided)
├── Dockerfile               # Multi-stage build
├── docker-compose.yml       # Full stack
├── requirements.txt         # Dependencies
├── .env.example             # Environment template
├── .dockerignore            # Docker ignore
├── railway.toml             # Railway config (or render.yaml)
└── README.md                # Setup instructions
```

**Requirements:**
-  All code runs without errors
-  Multi-stage Dockerfile (image < 500 MB)
-  API key authentication
-  Rate limiting (10 req/min)
-  Cost guard ($10/month)
-  Health + readiness checks
-  Graceful shutdown
-  Stateless design (Redis)
-  No hardcoded secrets

---

### 3. Service Domain Link

Create a file `DEPLOYMENT.md` with your deployed service information:

```markdown
# Deployment Information

## Public URL
https://your-agent.railway.app

## Platform
Railway / Render / Cloud Run

## Test Commands

### Health Check
```bash
curl https://your-agent.railway.app/health
# Expected: {"status": "ok"}
```

### API Test (with authentication)
```bash
curl -X POST https://your-agent.railway.app/ask \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "question": "Hello"}'
```

## Environment Variables Set
- PORT
- REDIS_URL
- AGENT_API_KEY
- LOG_LEVEL

## Screenshots
- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)
```

##  Pre-Submission Checklist

- [ ] Repository is public (or instructor has access)
- [ ] `MISSION_ANSWERS.md` completed with all exercises
- [ ] `DEPLOYMENT.md` has working public URL
- [ ] All source code in `app/` directory
- [ ] `README.md` has clear setup instructions
- [ ] No `.env` file committed (only `.env.example`)
- [ ] No hardcoded secrets in code
- [ ] Public URL is accessible and working
- [ ] Screenshots included in `screenshots/` folder
- [ ] Repository has clear commit history

---

##  Self-Test

Before submitting, verify your deployment:

```bash
# 1. Health check
curl https://your-app.railway.app/health

# 2. Authentication required
curl https://your-app.railway.app/ask
# Should return 401

# 3. With API key works
curl -H "X-API-Key: YOUR_KEY" https://your-app.railway.app/ask \
  -X POST -d '{"user_id":"test","question":"Hello"}'
# Should return 200

# 4. Rate limiting
for i in {1..15}; do 
  curl -H "X-API-Key: YOUR_KEY" https://your-app.railway.app/ask \
    -X POST -d '{"user_id":"test","question":"test"}'; 
done
# Should eventually return 429
```

---

##  Submission

**Submit your GitHub repository URL:**

```
https://github.com/your-username/day12-agent-deployment
```

**Deadline:** 17/4/2026

---

##  Quick Tips

1.  Test your public URL from a different device
2.  Make sure repository is public or instructor has access
3.  Include screenshots of working deployment
4.  Write clear commit messages
5.  Test all commands in DEPLOYMENT.md work
6.  No secrets in code or commit history

---

##  Need Help?

- Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Review [CODE_LAB.md](CODE_LAB.md)
- Ask in office hours
- Post in discussion forum

---

**Good luck! **
