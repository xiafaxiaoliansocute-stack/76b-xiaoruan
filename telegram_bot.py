import asyncio
import subprocess
import time
from pathlib import Path
from datetime import datetime

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# =====================================================
# CONFIG
# =====================================================

BOT_TOKEN = "8994992623:AAGc4TRHHEPHujeOUCa9VBPCYIR3bff6r6Y"

CHAT_ID = -5268959413

BASE_DIR = Path(__file__).parent

LINE = "━━━━━━━━━━━━━━━━━━━━━━"

# =====================================================
# TASKS
# =====================================================

TASKS = {

    "23E-计算留存": [

        ("💰 充值用户", "23E-liucun/23echongzhi.py", 10),

        ("👤 首充用户", "23E-liucun/23eshoucun.py", 30),

        ("📊 留存计算", "23E-liucun/23eliucun.py", 0),

    ],

    "73J-计算留存": [

        ("💰 充值用户", "73J-liucun/73jchongzhi.py", 10),
        
        ("👤 首充用户", "73J-liucun/73jshouchong.py", 30),
        
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

def allow(update):

    return update.effective_chat.id == CHAT_ID


def fmt(sec):

    sec = int(sec)

    m, s = divmod(sec, 60)

    if m:

        return f"{m}分{s}秒"

    return f"{s}秒"


def execute_script(script):

    path = BASE_DIR / script

    if not path.exists():

        raise FileNotFoundError(script)

    result = subprocess.run(

        ["/usr/bin/python3", str(path)],

        cwd=BASE_DIR

    )

    if result.returncode != 0:

        raise RuntimeError(f"{script} 执行失败")
# =====================================================
# TASK MANAGER
# =====================================================

async def run_group(group_name, message):

    global running
    global current_task
    global task_start_time


    if running:

        elapsed = fmt(time.time() - task_start_time)
        await message.reply_text(

            f"""⚠️ 当前已有任务正在运行

            📌 当前任务：{current_task}

            ⏱ 已运行：{elapsed}
            
            请等待当前任务结束后再执行新的任务。""")

        return


    running = True
    current_task = group_name
    task_start_time = time.time()


    tasks = TASKS[group_name]


    total_start = time.time()


    # 保存状态

    task_status = []

    for title, script, wait in tasks:

        task_status.append(
            {
                "title": title,
                "status": "waiting",
                "time": ""
            }
        )


    msg = await message.reply_text(
        "🚀 初始化任务..."
    )


    def render():

        done = 0

        for t in task_status:

            if t["status"] == "done":

                done += 1


        percent = int(
            done / len(task_status) * 100
        )


        bar_count = percent // 10


        bar = (
            "🟩" * bar_count
            +
            "⬜" * (10-bar_count)
        )


        lines = []


        for t in task_status:


            if t["status"] == "done":

                icon = "🟢"


            elif t["status"] == "running":

                icon = "🟡"


            elif t["status"] == "error":

                icon = "🔴"


            else:

                icon = "⚪"



            line = (
                f"{icon} {t['title']}"
            )


            if t["time"]:

                line += (
                    f"  ({t['time']})"
                )


            lines.append(line)



        return (

            f"🚀 {group_name}开始任务数据\n\n"

            f"{LINE}\n\n"

            f"{bar} {percent}%\n\n"

            +
            "\n".join(lines)

            +

            "\n\n"

            f"{LINE}\n"

            f"⏱ 运行时间："
            f"{fmt(time.time()-total_start)}"

        )



    try:


        for index, (title, script, wait_time) in enumerate(tasks):


            task_status[index]["status"] = "running"


            await msg.edit_text(
                render()
            )


            start = time.time()


            try:


                await asyncio.to_thread(

                    execute_script,

                    script

                )


            except Exception as e:


                task_status[index]["status"] = "error"


                task_status[index]["time"] = (
                    str(e)
                )


                await msg.edit_text(
                    render()
                    +
                    f"\n\n❌ 错误:\n{e}"
                )


                return



            cost = fmt(
                time.time()-start
            )


            task_status[index]["status"] = "done"


            task_status[index]["time"] = cost



            await msg.edit_text(
                render()
            )



            if wait_time:

                await asyncio.sleep(
                    wait_time
                )



        total = fmt(
            time.time()-total_start
        )


        await msg.edit_text(

            render()

            +

            "\n\n"

            "✅ 留存计算-上传完成\n"

            f"⏱ 总耗时：{total}\n"

            f"🕒 {datetime.now():%Y-%m-%d %H:%M:%S}"

        )



    finally:


        running = False
        current_task = ""
        task_start_time = None

# =====================================================
# COMMANDS
# =====================================================

async def run23e(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not allow(update):
        return

    asyncio.create_task(
    run_group(
        "23E-计算留存",
        update.message
    )
)


async def run73j(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not allow(update):
        return

    asyncio.create_task(
    run_group(
        "73J-计算留存",
        update.message
    )
)


async def run16013(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not allow(update):
        return

    asyncio.create_task(
    run_group(
        "16013",
        update.message
    )
)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not allow(update):
        return

    if running:

        await update.message.reply_text(

            f"🟢 当前任务：{current_task}"

        )

    else:

        await update.message.reply_text(

            "✅ 当前没有任务运行。"

        )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not allow(update):
        return

    await update.message.reply_text(

"""
🤖 数据机器人

/23e_start
/73j_start
/leuleu

/status
/help
"""

    )


# =====================================================
# REGISTER
# =====================================================

def register(app):

    app.add_handler(

        CommandHandler(
            "23e_start",
            run23e
        )
    )

    app.add_handler(

        CommandHandler(
            "73j_start",
            run73j
        )
    )

    app.add_handler(

        CommandHandler(
            "data",
            run16013
        )
    )

    app.add_handler(

        CommandHandler(
            "status",
            status
        )
    )

    app.add_handler(

        CommandHandler(
            "help",
            help_cmd
        )
    )


# =====================================================
# MAIN
# =====================================================

def main():

    print("=" * 50)
    print("Telegram Bot Starting...")
    print("=" * 50)

    app = (

        ApplicationBuilder()

        .token(BOT_TOKEN)

        .build()

    )

    register(app)

    print("Bot Started.")

    app.run_polling(

        drop_pending_updates=True

    )


# =====================================================
# ENTRY
# =====================================================

if __name__ == "__main__":

    main()
