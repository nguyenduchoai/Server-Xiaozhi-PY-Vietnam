"""
Seed Education Demo Data — matches production schema exactly.
Run: docker exec xiaozhi-backend python3 /app/src/app/scripts/seed_education_demo.py
"""
import asyncio
import uuid
from datetime import datetime, timezone


async def seed():
    from app.core.db.database import local_session
    from sqlalchemy import text

    async with local_session() as db:
        r = await db.execute(text("SELECT COUNT(*) FROM edu_course"))
        existing = r.scalar()
        if existing >= 3:
            print(f"Already have {existing} courses. Skipping seed.")
            return

        print("🌱 Seeding Education Demo Data...")

        r = await db.execute(text('SELECT id FROM "user" ORDER BY created_at ASC LIMIT 1'))
        user_id = str(r.scalar())
        r = await db.execute(text("SELECT id FROM agent WHERE is_deleted = false LIMIT 1"))
        agent_id = str(r.scalar())
        print(f"  user_id={user_id}, agent_id={agent_id}")

        now = datetime.utcnow()  # DB uses naive timestamps

        # ── helpers ──
        def uid():
            return str(uuid.uuid4())

        # ════════════════════════════════════════════
        # COURSES
        # ════════════════════════════════════════════
        courses = [
            {
                "id": uid(), "name": "Tiếng Anh Giao Tiếp Cơ Bản",
                "description": "Khóa học tiếng Anh giao tiếp: chào hỏi, giới thiệu, mua sắm, nhà hàng, du lịch.",
                "difficulty": "beginner", "language": "en", "estimated_hours": 10,
            },
            {
                "id": uid(), "name": "Tiếng Nhật N5 Cho Người Mới",
                "description": "Hiragana, Katakana, chào hỏi, số đếm, mẫu câu cơ bản tiếng Nhật.",
                "difficulty": "beginner", "language": "ja", "estimated_hours": 15,
            },
            {
                "id": uid(), "name": "Kỹ Năng Giao Tiếp Doanh Nghiệp",
                "description": "Email chuyên nghiệp, thuyết trình, đàm phán, họp trực tuyến, phản hồi khách hàng.",
                "difficulty": "intermediate", "language": "vi", "estimated_hours": 12,
            },
        ]

        for c in courses:
            await db.execute(text("""
                INSERT INTO edu_course (id, user_id, name, description, difficulty, language, estimated_hours,
                                        is_published, is_public, is_free, created_at, updated_at)
                VALUES (:id, :uid, :name, :desc, :diff, :lang, :hrs, true, true, true, :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": c["id"], "uid": user_id, "name": c["name"], "desc": c["description"],
                   "diff": c["difficulty"], "lang": c["language"], "hrs": c["estimated_hours"], "now": now})
        print(f"  ✅ {len(courses)} courses created")

        # ════════════════════════════════════════════
        # LESSONS  (content is JSONB)
        # ════════════════════════════════════════════
        import json as _json
        all_lessons = {
            courses[0]["id"]: [
                ("Chào hỏi & Giới thiệu", "vocabulary", [
                    {"type": "text", "body": "Hello / Hi / Good morning. My name is ... I'm from ..."},
                ], 1),
                ("Hỏi đường & Chỉ đường", "vocabulary", [
                    {"type": "text", "body": "Excuse me, how do I get to...? Turn left/right. Go straight."},
                ], 2),
                ("Mua sắm & Trả giá", "conversation", [
                    {"type": "text", "body": "How much is this? Can I try it on? I'll take it."},
                ], 3),
                ("Tại nhà hàng", "conversation", [
                    {"type": "text", "body": "Can I see the menu? I'd like to order... The bill, please."},
                ], 4),
                ("Gọi điện thoại", "conversation", [
                    {"type": "text", "body": "May I speak to...? Could you hold on? I'll call back later."},
                ], 5),
                ("Ở sân bay & Du lịch", "vocabulary", [
                    {"type": "text", "body": "Where is check-in? Window/aisle seat. My luggage is missing."},
                ], 6),
                ("Tại bệnh viện", "vocabulary", [
                    {"type": "text", "body": "I have a headache. I need to see a doctor. I'm allergic to..."},
                ], 7),
                ("Phỏng vấn xin việc", "conversation", [
                    {"type": "text", "body": "Tell me about yourself. Why do you want to work here?"},
                ], 8),
            ],
            courses[1]["id"]: [
                ("Hiragana - Bảng chữ cái", "vocabulary", [
                    {"type": "text", "body": "あいうえお (a-i-u-e-o), かきくけこ (ka-ki-ku-ke-ko)"},
                ], 1),
                ("Chào hỏi tiếng Nhật", "vocabulary", [
                    {"type": "text", "body": "おはようございます - Chào buổi sáng. こんにちは - Xin chào."},
                ], 2),
                ("Giới thiệu bản thân", "conversation", [
                    {"type": "text", "body": "はじめまして. 私の名前は___です."},
                ], 3),
                ("Số đếm 1-100", "vocabulary", [
                    {"type": "text", "body": "いち(1) に(2) さん(3) し(4) ご(5) ろく(6) なな(7) はち(8) く(9) じゅう(10)"},
                ], 4),
                ("Mua sắm tại Nhật", "conversation", [
                    {"type": "text", "body": "いくらですか - Bao nhiêu? これをください - Cho tôi cái này."},
                ], 5),
            ],
            courses[2]["id"]: [
                ("Email chuyên nghiệp", "reading", [
                    {"type": "text", "body": "Subject → Greeting → Body → CTA → Signature"},
                ], 1),
                ("Kỹ năng thuyết trình", "reading", [
                    {"type": "text", "body": "Mở đầu thu hút, storytelling, xử lý Q&A, kết thúc ấn tượng."},
                ], 2),
                ("Đàm phán hợp đồng", "reading", [
                    {"type": "text", "body": "BATNA, Zone of Possible Agreement, win-win strategy."},
                ], 3),
                ("Họp trực tuyến hiệu quả", "reading", [
                    {"type": "text", "body": "Agenda, time-boxing, action items, follow-up email."},
                ], 4),
                ("Phản hồi khách hàng", "reading", [
                    {"type": "text", "body": "HEAT: Hear → Empathize → Apologize → Take action."},
                ], 5),
                ("Báo cáo KPI", "reading", [
                    {"type": "text", "body": "Dashboard, charts, insights, recommendations. Data storytelling."},
                ], 6),
            ],
        }

        lesson_ids = {}  # course_id -> [lesson_id, ...]
        total_lessons = 0
        for cid, lessons in all_lessons.items():
            lesson_ids[cid] = []
            for name, ltype, content_blocks, order in lessons:
                lid = uid()
                lesson_ids[cid].append(lid)
                await db.execute(text("""
                    INSERT INTO edu_lesson (id, course_id, title, lesson_type, content, lesson_order,
                                           duration_minutes, is_published, created_at, updated_at)
                    VALUES (:id, :cid, :name, :lt, CAST(:content AS jsonb), :ord, 15, true, :now, :now)
                    ON CONFLICT DO NOTHING
                """), {"id": lid, "cid": cid, "name": name, "lt": ltype,
                       "content": _json.dumps(content_blocks, ensure_ascii=False), "ord": order, "now": now})
                total_lessons += 1
        print(f"  ✅ {total_lessons} lessons created")

        # ════════════════════════════════════════════
        # QUIZZES & QUESTIONS
        # ════════════════════════════════════════════
        quizzes = [
            {
                "id": uid(), "course_id": courses[0]["id"],
                "title": "Kiểm tra Tiếng Anh Giao Tiếp",
                "description": "Bài kiểm tra tổng hợp giao tiếp tiếng Anh cơ bản",
                "passing_score": 70, "time_limit_seconds": 900,
                "questions": [
                    ("Cách chào buổi sáng?", '["Good morning","Good evening","Good night","Goodbye"]', "Good morning"),
                    ("\"The bill, please\" nghĩa là?", '["Cho tôi hóa đơn","Bao nhiêu tiền","Tôi muốn gọi","Cảm ơn"]', "Cho tôi hóa đơn"),
                    ("Hỏi giá tiền?", '["How much is this?","What is this?","Where is this?","When?"]', "How much is this?"),
                    ("\"I\\'m allergic to peanuts\" nghĩa gì?", '["Dị ứng đậu phộng","Thích đậu phộng","Muốn mua","Không có"]', "Dị ứng đậu phộng"),
                    ("Giới thiệu tên đúng cách?", '["My name is Lan","I name Lan","Name Lan","Lan is my"]', "My name is Lan"),
                ],
            },
            {
                "id": uid(), "course_id": courses[1]["id"],
                "title": "Kiểm tra Tiếng Nhật N5",
                "description": "Hiragana và mẫu câu cơ bản",
                "passing_score": 60, "time_limit_seconds": 600,
                "questions": [
                    ("おはようございます nghĩa là?", '["Chào buổi sáng","Chào buổi tối","Tạm biệt","Cảm ơn"]', "Chào buổi sáng"),
                    ("Số 5 đọc là?", '["ご (go)","さん (san)","に (ni)","いち (ichi)"]', "ご (go)"),
                    ("いくらですか dùng để?", '["Hỏi giá","Hỏi tên","Hỏi đường","Hỏi giờ"]', "Hỏi giá"),
                    ("こんにちは dùng khi nào?", '["Ban ngày","Sáng sớm","Tối khuya","Khi ngủ"]', "Ban ngày"),
                    ("ありがとうございます là?", '["Cảm ơn nhiều","Xin lỗi","Tạm biệt","Xin chào"]', "Cảm ơn nhiều"),
                ],
            },
        ]

        total_q = 0
        for q in quizzes:
            await db.execute(text("""
                INSERT INTO edu_quiz (id, course_id, title, description, passing_score, time_limit_seconds, created_at, updated_at)
                VALUES (:id, :cid, :title, :desc, :ps, :tl, :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": q["id"], "cid": q["course_id"], "title": q["title"],
                   "desc": q["description"], "ps": q["passing_score"], "tl": q["time_limit_seconds"], "now": now})
            for idx, (qt, opts, correct) in enumerate(q["questions"]):
                qid = uid()
                await db.execute(text("""
                    INSERT INTO edu_question (id, quiz_id, question_text, question_type, options, correct_answer, points, question_order, created_at)
                    VALUES (:id, :qid, :qt, 'multiple_choice', CAST(:opts AS jsonb), :ca, 10, :ord, :now)
                    ON CONFLICT DO NOTHING
                """), {"id": qid, "qid": q["id"], "qt": qt, "opts": opts, "ca": correct, "ord": idx + 1, "now": now})
                total_q += 1
        print(f"  ✅ {len(quizzes)} quizzes, {total_q} questions created")

        # ════════════════════════════════════════════
        # FLASHCARD DECKS
        # ════════════════════════════════════════════
        decks = [
            {
                "id": uid(), "course_id": courses[0]["id"], "name": "100 Từ Vựng Tiếng Anh Hàng Ngày",
                "description": "Bộ flashcard từ vựng thường dùng", "category": "vocabulary",
                "cards": [
                    ("Hello", "Xin chào"), ("Thank you", "Cảm ơn"), ("Goodbye", "Tạm biệt"),
                    ("Please", "Làm ơn"), ("Sorry", "Xin lỗi"), ("Water", "Nước"),
                    ("Food", "Thức ăn"), ("Money", "Tiền"), ("Time", "Thời gian"),
                    ("Friend", "Bạn bè"), ("Family", "Gia đình"), ("Work", "Công việc"),
                    ("School", "Trường học"), ("Hospital", "Bệnh viện"), ("Airport", "Sân bay"),
                    ("Restaurant", "Nhà hàng"), ("Beautiful", "Đẹp"), ("Delicious", "Ngon"),
                    ("Expensive", "Đắt"), ("Cheap", "Rẻ"),
                ],
            },
            {
                "id": uid(), "course_id": courses[1]["id"], "name": "Hiragana - Bảng Chữ Cái Nhật",
                "description": "Bộ flashcard học Hiragana", "category": "alphabet",
                "cards": [
                    ("あ", "a"), ("い", "i"), ("う", "u"), ("え", "e"), ("お", "o"),
                    ("か", "ka"), ("き", "ki"), ("く", "ku"), ("け", "ke"), ("こ", "ko"),
                    ("さ", "sa"), ("し", "shi"), ("す", "su"), ("せ", "se"), ("そ", "so"),
                    ("た", "ta"), ("ち", "chi"), ("つ", "tsu"), ("て", "te"), ("と", "to"),
                    ("な", "na"), ("に", "ni"), ("ぬ", "nu"), ("ね", "ne"), ("の", "no"),
                ],
            },
        ]

        total_cards = 0
        for d in decks:
            await db.execute(text("""
                INSERT INTO edu_flashcard_deck (id, course_id, user_id, name, description, category, created_at, updated_at)
                VALUES (:id, :cid, :uid, :name, :desc, :cat, :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": d["id"], "cid": d["course_id"], "uid": user_id,
                   "name": d["name"], "desc": d["description"], "cat": d["category"], "now": now})
            for idx, (front, back) in enumerate(d["cards"]):
                cid = uid()
                await db.execute(text("""
                    INSERT INTO edu_flashcard (id, deck_id, front, back, difficulty, card_order, created_at)
                    VALUES (:id, :did, :front, :back, 1, :ord, :now)
                    ON CONFLICT DO NOTHING
                """), {"id": cid, "did": d["id"], "front": front, "back": back, "ord": idx + 1, "now": now})
                total_cards += 1
        print(f"  ✅ {len(decks)} flashcard decks, {total_cards} cards created")

        # ════════════════════════════════════════════
        # ENROLLMENTS
        # ════════════════════════════════════════════
        for c in courses:
            eid = uid()
            await db.execute(text("""
                INSERT INTO edu_enrollment (id, user_id, course_id, enrolled_at)
                VALUES (:id, :uid, :cid, :now)
                ON CONFLICT DO NOTHING
            """), {"id": eid, "uid": user_id, "cid": c["id"], "now": now})
        print(f"  ✅ User enrolled in all {len(courses)} courses")

        # Enable education on agent
        await db.execute(text("UPDATE agent SET enable_education = true WHERE id = :aid"), {"aid": agent_id})
        print(f"  ✅ Education enabled for agent {agent_id}")

        await db.commit()
        print("\n🎉 Education Demo Data seeded!")
        print(f"   📚 {len(courses)} courses, {total_lessons} lessons, {len(quizzes)} quizzes, {total_q} questions, {total_cards} flashcards")


if __name__ == "__main__":
    asyncio.run(seed())
