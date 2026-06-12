# News Duplicate MVP

เว็บเล็กสำหรับกองข่าวคริปโต: วางลิงก์ข่าวหลายลิงก์ ระบบบันทึกข่าวของวันนั้น, extract keyword, และเตือนข่าวซ้ำจาก URL/keyword overlap

## Run

```bash
cd /home/ubuntu/news-duplicate-mvp
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m app.server
# หรือถ้า port 5000 ชนกับ service อื่น:
PORT=5050 python -m app.server
```

เปิดเว็บ:

```text
http://SERVER_IP:5000
# หรือ http://SERVER_IP:5050 ถ้าใช้ PORT=5050
```

ถ้ารันบน AWS ต้องเปิด Security Group port ที่ใช้ก่อน

## Deploy บน Render

1. ไปที่ Render → New + → Web Service
2. Connect GitHub repo: `Gokgokz/news-duplicate-mvp`
3. ตั้งค่า:
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn 'app.server:create_app()'`
4. Instance type: Free
5. กด Deploy
6. หลัง deploy เสร็จ Render จะให้ URL เช่น:
   `https://news-duplicate-mvp.onrender.com`

ถ้าเปิดแล้ว error ให้ดู Logs ใน Render ก่อนเป็นอย่างแรก

หมายเหตุ:
- Free tier ของ Render จะ sleep ได้เมื่อไม่มีคนใช้งาน
- `news.db` บน Render เป็น ephemeral storage — เหมาะกับ demo/test ชั่วคราว ถ้า redeploy ข้อมูลอาจหาย

## Test

```bash
cd /home/ubuntu/news-duplicate-mvp
. .venv/bin/activate
pytest -q
```

## ฟีเจอร์ MVP

- หน้าเพิ่มลิงก์ข่าวหลายลิงก์พร้อมชื่อคนเขียน
- Auto title/source จาก URL หรือ metadata หน้าเว็บจริง
- Auto keyword/entity เช่น Michael Saylor, Strategy, Bitcoin, Tom Lee, ETF
- กันซ้ำรายวัน:
  - URL ซ้ำ แม้มี utm tracking
  - keyword overlap ตั้งแต่ 2 คำขึ้นไป
- หน้า “ข่าววันนี้”
- Keyword dashboard ประจำวัน
- ค้นหาข่าวจาก keyword/headline/source/นักข่าว
- SQLite database: `news.db`

## API

เพิ่มลิงก์:

```bash
curl -X POST http://127.0.0.1:5000/api/links \
  -H 'Content-Type: application/json' \
  -d '{"journalist":"โจ","links":["https://example.com/michael-saylor-strategy-bitcoin"]}'
```

ดูข่าววันนี้:

```bash
curl http://127.0.0.1:5000/api/today
```

## Next step ที่ควรต่อ

1. Login/ชื่อกะนักข่าว
2. Google Sheet sync จาก database กลับ sheet เดิม
3. Semantic duplicate ด้วย LLM สำหรับ headline/summary คล้ายกัน
4. เลือกวันที่ย้อนหลัง
5. ปุ่ม export CSV/Google Sheet
