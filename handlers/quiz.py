import json
import random
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from db.models import upsert_user, update_quiz_result, get_quiz_result

_FILE = Path(__file__).parent.parent / "data" / "quiz.json"
QUIZ_SIZE = 5  # вопросов за одну сессию


def _load() -> list[dict]:
    with open(_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _quiz_keyboard(question: dict, q_index: int, session_id: str) -> InlineKeyboardMarkup:
    buttons = []
    for i, option in enumerate(question["options"]):
        buttons.append([InlineKeyboardButton(
            option,
            callback_data=f"quiz_ans_{session_id}_{q_index}_{i}"
        )])
    return InlineKeyboardMarkup(buttons)


async def cmd_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await upsert_user(user.id, user.username, user.first_name)

    questions = _load()
    selected = random.sample(questions, min(QUIZ_SIZE, len(questions)))

    # Сохраняем сессию квиза в user_data
    import time
    session_id = str(int(time.time()))[-6:]
    context.user_data[f"quiz_{session_id}"] = {
        "questions": selected,
        "current": 0,
        "correct": 0,
    }

    result = await get_quiz_result(user.id)
    total_stat = f"Всего пройдено: {result['total']} вопросов, правильно: {result['correct']}" if result["total"] > 0 else ""

    text = f"🧠 *Квиз по SQL*\nБудет {len(selected)} вопросов.\n{total_stat}\n\nНачинаем!"
    if hasattr(update, "message") and update.message:
        msg = await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    else:
        msg = await update.callback_query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    await _send_question(context, msg.chat_id, session_id, 0)


async def _send_question(context, chat_id: int, session_id: str, q_index: int):
    session = context.user_data.get(f"quiz_{session_id}")
    if not session:
        return

    questions = session["questions"]
    if q_index >= len(questions):
        return

    q = questions[q_index]
    text = f"*Вопрос {q_index + 1}/{len(questions)}:*\n\n{q['question']}"
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_quiz_keyboard(q, q_index, session_id),
    )


async def handle_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE, session_id: str, q_index: int, answer: int):
    query = update.callback_query
    user = query.from_user
    session = context.user_data.get(f"quiz_{session_id}")

    if not session:
        await query.answer("Квиз устарел. Начни новый: /quiz")
        return

    questions = session["questions"]
    q = questions[q_index]
    is_correct = (answer == q["correct"])

    if is_correct:
        session["correct"] += 1
        feedback = "✅ Правильно!"
    else:
        correct_text = q["options"][q["correct"]]
        feedback = f"❌ Неверно. Правильный ответ: *{correct_text}*"

    await query.answer()
    await query.message.edit_text(
        f"*Вопрос {q_index + 1}/{len(questions)}:*\n\n{q['question']}\n\n{feedback}",
        parse_mode=ParseMode.MARKDOWN,
    )

    next_index = q_index + 1
    if next_index < len(questions):
        await _send_question(context, query.message.chat_id, session_id, next_index)
    else:
        # Конец квиза
        correct = session["correct"]
        total = len(questions)
        await update_quiz_result(user.id, correct, total)

        pct = round(correct / total * 100)
        if pct == 100:
            grade = "Отлично! 🏆"
        elif pct >= 70:
            grade = "Хорошо! 👍"
        elif pct >= 40:
            grade = "Неплохо, но есть над чем поработать 📚"
        else:
            grade = "Стоит повторить материал 💪"

        all_result = await get_quiz_result(user.id)

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                f"🏁 *Квиз завершён!*\n\n"
                f"Результат: {correct}/{total} ({pct}%)\n"
                f"{grade}\n\n"
                f"Всего за всё время: {all_result['correct']}/{all_result['total']}"
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Ещё раз", callback_data="start_quiz")],
                [InlineKeyboardButton("◀️ Главное меню", callback_data="main_menu")],
            ]),
        )
        del context.user_data[f"quiz_{session_id}"]
