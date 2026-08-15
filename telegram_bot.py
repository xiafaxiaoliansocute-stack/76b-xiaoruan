import asyncio
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from telegram import Update
from telegram.error import BadRequest, NetworkError, RetryAfter, TimedOut
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

BOT_VERSION = "DIRECT_LOG_ROWS_SAFE_V3"

# =====================================================
# CONFIG
# =====================================================

BOT_TOKEN = "8994992623:AAGc4TRHHEPHujeOUCa9VBPCYIR3bff6r6Y"
CHAT_ID = -5268959413
BASE_DIR = Path(__file__).resolve().parent
LINE = "━━━━━━━━━━━━━━━━━━━━━━"

# =====================================================
# TASKS
# =====================================================

TASKS = {
    "23E-计算留存": [
        ("💰 充值用户", "23E-liucun/23echongzhi.py", 5),
        ("👤 首充用户", "23E-liucun/23eshoucun.py", 10),
        ("📊 留存计算", "23E-liucun/23eliucun.py", 0),
    ],
    "73J-计算留存": [
        ("💰 充值用户", "73J-liucun/73jchongzhi.py", 5),
        ("👤 首充用户", "73J-liucun/73jshouchong.py", 10),
        ("📊 留存计算", "73J-liucun/73jliucun.py", 0),
    ],
}

# =====================================================
# GLOBAL
# =====================================================

running = False
current_task = ""
task_start_time = None

# =====================================================
# TOOLS
# =====================================================


def allow(update: Update) -> bool:
    return bool(update.effective_chat and update.effective_chat.id == CHAT_ID)


def fmt(sec) -> str:
    sec = max(0, int(sec))
    m, s = divmod(sec, 60)
    if m:
        return f"{m}分{s}秒"
    return f"{s}秒"


def execute_script(script: str):
    """
    Chạy script và đọc log trực tiếp.

    充值用户:
        lấy từ: 原始充值数量: 323416

    首充用户:
        lấy từ: ✅ 保存 SQLite，新增 10824 条

    Trả về số lượng dữ liệu tải được; 留存脚本 trả về None.
    """
    path = (BASE_DIR / script).resolve()

    if not path.exists():
        raise FileNotFoundError(f"找不到脚本: {path}")

    if not path.is_file():
        raise RuntimeError(f"不是文件: {path}")

    script_lower = script.lower()

    downloaded_rows = None

    process = subprocess.Popen(
        [sys.executable, str(path)],
        cwd=str(BASE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
    )

    assert process.stdout is not None

    for raw_line in process.stdout:
        line = raw_line.rstrip("\n")

        # Giữ nguyên log hiển thị ở terminal
        print(line, flush=True)

        # =================================================
        # 充值用户
        # Ví dụ:
        # [TELEGRAM_BOT] 原始充值数量: 323416
        # 原始充值数量: 323416
        # =================================================
        if "chongzhi" in script_lower:
            match = re.search(
                r"原始充值数量\s*[:：]\s*([\d,]+)",
                line,
            )
            if match:
                downloaded_rows = int(
                    match.group(1).replace(",", "")
                )

        # =================================================
        # 首充用户
        # Ví dụ:
        # [TELEGRAM_BOT] ✅ 保存 SQLite，新增 10824 条
        # ✅ 保存 SQLite，新增 10824 条
        # =================================================
        elif (
            "shouchong" in script_lower
            or "shoucun" in script_lower
        ):
            match = re.search(
                r"保存\s*SQLite.*?新增\s*([\d,]+)\s*条",
                line,
            )
            if match:
                downloaded_rows = int(
                    match.group(1).replace(",", "")
                )

    return_code = process.wait()

    if return_code != 0:
        raise RuntimeError(
            f"{script} 执行失败，退出码: {return_code}"
        )

    return downloaded_rows


# =====================================================
# DELETE FUNCTIONS
# Hai lệnh độc lập:
# /del_shouchong -> chỉ xóa shouchong
# /del_recharge  -> chỉ xóa recharge
# =====================================================


def get_project_db(project_type: str) -> Path:
    project_lower = project_type.lower().strip()

    if project_lower == "23e":
        folder = BASE_DIR / "23E-liucun"
        expected = folder / "23E.db"
    elif project_lower == "73j":
        folder = BASE_DIR / "73J-liucun"
        expected = folder / "73J.db"
    else:
        raise ValueError("项目名称错误，只能使用 23e 或 73j")

    if expected.exists() and expected.is_file():
        return expected

    # Linux phân biệt chữ hoa/chữ thường. Nếu tên DB hơi khác,
    # chỉ tự chọn khi trong thư mục có đúng 1 file .db.
    if folder.exists() and folder.is_dir():
        db_files = sorted(
            p for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() == ".db"
        )
        if len(db_files) == 1:
            return db_files[0]
        if len(db_files) > 1:
            names = ", ".join(p.name for p in db_files)
            raise FileNotFoundError(
                f"找不到指定数据库 {expected.name}；目录里有多个 DB: {names}"
            )

    raise FileNotFoundError(f"找不到数据库: {expected}")


def check_date(date_str: str) -> None:
    try:
        parsed = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("日期格式错误，正确格式: YYYY-MM-DD") from exc

    # datetime.strptime accepts only a real calendar date, so no extra check needed.
    if parsed.strftime("%Y-%m-%d") != date_str:
        raise ValueError("日期格式错误，正确格式: YYYY-MM-DD")


def ensure_table_column(
    conn: sqlite3.Connection,
    table_name: str,
    column_name: str,
) -> None:
    cursor = conn.cursor()

    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    )
    if cursor.fetchone() is None:
        raise RuntimeError(f"数据库中找不到表: {table_name}")

    cursor.execute(f'PRAGMA table_info("{table_name}")')
    columns = {row[1] for row in cursor.fetchall()}

    if column_name not in columns:
        raise RuntimeError(
            f"表 {table_name} 中找不到字段: {column_name}"
        )


def execute_delete_shouchong(project_type: str, date_str: str) -> int:
    check_date(date_str)
    db_path = get_project_db(project_type)

    conn = sqlite3.connect(str(db_path), timeout=30)
    try:
        ensure_table_column(conn, "shouchong", "统计时间")
        cursor = conn.cursor()

        # Hỗ trợ cả giá trị chỉ có ngày và giá trị có thêm giờ phía sau.
        cursor.execute(
            '''
            DELETE FROM "shouchong"
            WHERE CAST("统计时间" AS TEXT) = ?
               OR CAST("统计时间" AS TEXT) LIKE ?
            ''',
            (date_str, f"{date_str}%"),
        )

        deleted_count = cursor.rowcount
        conn.commit()
        return deleted_count

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute_delete_recharge(project_type: str, date_str: str) -> int:
    check_date(date_str)
    db_path = get_project_db(project_type)

    conn = sqlite3.connect(str(db_path), timeout=30)
    try:
        ensure_table_column(conn, "recharge", "完成时间")
        cursor = conn.cursor()

        # Hỗ trợ cả YYYY-MM-DD và YYYY-MM-DD HH:MM:SS.
        cursor.execute(
            '''
            DELETE FROM "recharge"
            WHERE CAST("完成时间" AS TEXT) = ?
               OR CAST("完成时间" AS TEXT) LIKE ?
            ''',
            (date_str, f"{date_str}%"),
        )

        deleted_count = cursor.rowcount
        conn.commit()
        return deleted_count

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()





# =====================================================
# TELEGRAM SAFE MESSAGE
# Không để lỗi edit/network làm dừng task dữ liệu
# =====================================================

async def safe_edit_status(status_msg, source_message, text):
    """
    Cập nhật tin nhắn trạng thái an toàn.

    - Message is not modified -> bỏ qua
    - Message to edit not found -> tự gửi một tin trạng thái mới
    - RetryAfter -> chờ rồi thử lại
    - NetworkError / TimedOut -> retry
    - Nếu Telegram vẫn lỗi sau retry -> chỉ ghi log, task dữ liệu vẫn tiếp tục

    Return:
        Message hiện tại hoặc Message mới nếu phải gửi lại.
    """
    last_error = None

    for attempt in range(3):
        try:
            await status_msg.edit_text(text)
            return status_msg

        except BadRequest as exc:
            error_text = str(exc).lower()

            if "message is not modified" in error_text:
                return status_msg

            if "message to edit not found" in error_text:
                print(
                    "[TELEGRAM_BOT] ⚠️ 状态消息不存在，重新发送一条...",
                    flush=True,
                )

                # Tin cũ không còn tồn tại -> gửi tin mới.
                for send_attempt in range(3):
                    try:
                        return await source_message.reply_text(text)

                    except RetryAfter as retry_exc:
                        delay = retry_exc.retry_after
                        if hasattr(delay, "total_seconds"):
                            delay = delay.total_seconds()
                        await asyncio.sleep(float(delay) + 0.5)

                    except (NetworkError, TimedOut) as send_exc:
                        last_error = send_exc
                        if send_attempt < 2:
                            await asyncio.sleep(1.5 * (send_attempt + 1))
                            continue

                print(
                    f"[TELEGRAM_BOT] ⚠️ 无法重新发送状态消息: {last_error}",
                    flush=True,
                )
                return status_msg

            # BadRequest khác: không cho làm chết task chính.
            print(
                f"[TELEGRAM_BOT] ⚠️ Telegram状态更新失败: {exc}",
                flush=True,
            )
            return status_msg

        except RetryAfter as exc:
            delay = exc.retry_after
            if hasattr(delay, "total_seconds"):
                delay = delay.total_seconds()
            await asyncio.sleep(float(delay) + 0.5)
            last_error = exc

        except (NetworkError, TimedOut) as exc:
            last_error = exc
            if attempt < 2:
                await asyncio.sleep(1.5 * (attempt + 1))
                continue

    print(
        f"[TELEGRAM_BOT] ⚠️ 状态消息更新网络失败，任务继续运行: {last_error}",
        flush=True,
    )
    return status_msg


async def telegram_error_handler(update, context):
    """
    Tránh traceback dài cho lỗi mạng Telegram tạm thời.
    Lỗi logic khác vẫn được in ngắn gọn để kiểm tra.
    """
    error = context.error

    if isinstance(error, (NetworkError, TimedOut)):
        print(
            f"[TELEGRAM_BOT] ⚠️ Telegram网络波动: {error}",
            flush=True,
        )
        return

    print(
        f"[TELEGRAM_BOT] ❌ Telegram handler error: {error!r}",
        flush=True,
    )


# =====================================================
# TASK MANAGER
# =====================================================


async def run_group(group_name: str, message) -> None:
    global running
    global current_task
    global task_start_time

    if group_name not in TASKS:
        await message.reply_text(
            f"❌ 任务未配置: {group_name}"
        )
        return

    if running:
        elapsed = fmt(time.time() - task_start_time)
        await message.reply_text(
            f"⚠️ 当前已有任务正在运行\n\n"
            f"📌 当前任务：{current_task}\n"
            f"⏱ 已运行：{elapsed}\n\n"
            f"请等待当前任务结束后再执行新的任务。"
        )
        return

    running = True
    current_task = group_name
    task_start_time = time.time()

    tasks = TASKS[group_name]
    total_start = time.time()

    task_status = [
        {
            "title": title,
            "status": "waiting",
            "time": "",
            "rows": None,
        }
        for title, _script, _wait in tasks
    ]

    msg = await message.reply_text("🚀 初始化任务...")

    def render() -> str:
        done = sum(
            1
            for item in task_status
            if item["status"] == "done"
        )

        percent = (
            int(done / len(task_status) * 100)
            if task_status
            else 100
        )

        bar_count = percent // 10
        bar = (
            "🟩" * bar_count
            +
            "⬜" * (10 - bar_count)
        )

        lines = []

        for item in task_status:
            status_icon = {
                "done": "🟢",
                "running": "🟡",
                "error": "🔴",
                "waiting": "⚪",
            }.get(
                item["status"],
                "⚪",
            )

            line = f"{status_icon} {item['title']}"

            if item["time"]:
                line += f"  ({item['time']})"

            if item["rows"] is not None:
                line += (
                    f"  今日下载："
                    f"{item['rows']:,} 条数据"
                )

            lines.append(line)

        return (
            f"🚀 {group_name}开始任务数据\n\n"
            f"{LINE}\n\n"
            f"{bar} {percent}%\n\n"
            + "\n".join(lines)
            + "\n\n"
            f"{LINE}\n"
            f"⏱ 运行时间："
            f"{fmt(time.time() - total_start)}"
        )

    try:
        for index, (_title, script, wait_time) in enumerate(tasks):

            task_status[index]["status"] = "running"
            msg = await safe_edit_status(msg, message, render())

            start = time.time()

            try:
                downloaded_rows = await asyncio.to_thread(
                    execute_script,
                    script,
                )

            except Exception as exc:
                task_status[index]["status"] = "error"
                task_status[index]["time"] = str(exc)

                msg = await safe_edit_status(
                    msg,
                    message,
                    render()
                    +
                    f"\n\n❌ 错误:\n{exc}"
                )
                return

            task_status[index]["status"] = "done"
            task_status[index]["time"] = fmt(
                time.time() - start
            )

            # 充值 / 首充 sẽ nhận số trực tiếp từ log của script
            if downloaded_rows is not None:
                task_status[index]["rows"] = downloaded_rows

                print(
                    "[TELEGRAM_BOT] "
                    f"{script} 本次下载: "
                    f"{downloaded_rows:,} 条数据"
                )

            msg = await safe_edit_status(msg, message, render())

            if wait_time:
                await asyncio.sleep(wait_time)

        total = fmt(
            time.time() - total_start
        )

        msg = await safe_edit_status(
            msg,
            message,
            render()
            +
            "\n\n"
            +
            "✅ 留存计算-上传完成\n"
            +
            f"⏱ 总耗时：{total}\n"
            +
            f"🕒 {datetime.now():%Y-%m-%d %H:%M:%S}"
        )

    finally:
        running = False
        current_task = ""
        task_start_time = None


# =====================================================
# COMMANDS
# =====================================================


async def delete_shouchong_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not allow(update):
        return

    if update.message is None:
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text(
            "⚠️ 格式错误 / Sai cú pháp!\n\n"
            "📌 示例 / Ví dụ:\n"
            "/del_shouchong 23e 2026-08-11\n"
            "/del_shouchong 73j 2026-08-11"
        )
        return

    project_type = args[0].lower().strip()
    target_date = args[1].strip()

    try:
        deleted_count = await asyncio.to_thread(
            execute_delete_shouchong,
            project_type,
            target_date,
        )
        await update.message.reply_text(
            "✅ 首充删除完成\n\n"
            f"📂 项目: {project_type.upper()}\n"
            "📂 表: shouchong\n"
            f"📅 统计时间: {target_date}\n"
            f"🗑 删除: {deleted_count} 行"
        )
    except Exception as exc:
        await update.message.reply_text(
            f"❌ shouchong 删除失败\n\n{exc}"
        )


async def delete_recharge_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not allow(update):
        return

    if update.message is None:
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text(
            "⚠️ 格式错误 / Sai cú pháp!\n\n"
            "📌 示例 / Ví dụ:\n"
            "/del_recharge 23e 2026-08-11\n"
            "/del_recharge 73j 2026-08-11"
        )
        return

    project_type = args[0].lower().strip()
    target_date = args[1].strip()

    try:
        deleted_count = await asyncio.to_thread(
            execute_delete_recharge,
            project_type,
            target_date,
        )
        await update.message.reply_text(
            "✅ 充值删除完成\n\n"
            f"📂 项目: {project_type.upper()}\n"
            "📂 表: recharge\n"
            f"📅 完成时间: {target_date}\n"
            f"🗑 删除: {deleted_count} 行"
        )
    except Exception as exc:
        await update.message.reply_text(
            f"❌ recharge 删除失败\n\n{exc}"
        )


async def run23e(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not allow(update) or update.message is None:
        return
    context.application.create_task(
        run_group("23E-计算留存", update.message),
        update=update,
    )


async def run73j(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not allow(update) or update.message is None:
        return
    context.application.create_task(
        run_group("73J-计算留存", update.message),
        update=update,
    )


async def status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not allow(update) or update.message is None:
        return

    if running:
        elapsed = fmt(time.time() - task_start_time)
        await update.message.reply_text(
            f"🟢 当前任务：{current_task}\n⏱ 已运行：{elapsed}"
        )
    else:
        await update.message.reply_text("✅ 当前没有任务运行。")


async def help_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not allow(update) or update.message is None:
        return

    await update.message.reply_text(
        "🤖 数据机器人\n\n"
        "/23e_start\n"
        "/73j_start\n\n"
        "/del_shouchong 23e YYYY-MM-DD\n"
        "/del_shouchong 73j YYYY-MM-DD\n\n"
        "/del_recharge 23e YYYY-MM-DD\n"
        "/del_recharge 73j YYYY-MM-DD\n\n"
        "/status\n"
        "/help"
    )


# =====================================================
# REGISTER
# =====================================================


def register(app) -> None:
    app.add_handler(CommandHandler("23e_start", run23e))
    app.add_handler(CommandHandler("73j_start", run73j))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("help", help_cmd))

    # Hai lệnh xóa hoàn toàn độc lập.
    app.add_handler(CommandHandler("del_shouchong", delete_shouchong_cmd))
    app.add_handler(CommandHandler("del_recharge", delete_recharge_cmd))

    app.add_error_handler(telegram_error_handler)


# =====================================================
# MAIN
# =====================================================


def main() -> None:
    print("=" * 50)
    print("Telegram Bot Starting...")
    print("Version:", BOT_VERSION)
    print("=" * 50)

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    register(app)

    print("Bot Started.")
    app.run_polling(drop_pending_updates=True)


# =====================================================
# ENTRY
# =====================================================

if __name__ == "__main__":
    main()