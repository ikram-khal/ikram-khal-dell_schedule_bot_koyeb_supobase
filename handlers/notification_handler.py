"""
Notification handler for the Combined Telegram Bot
"""
import pandas as pd
from telegram.ext import ContextTypes

from config.settings import ALLOWED_USERS, GROUP_UNIONS, EXAM_GROUP_UNIONS
from models.data_models import BotData
from database.db_operations import get_from_db
from utils.helpers import parse_groups


class NotificationHandler:
    async def notify_users(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        is_original: bool,
        uploader_id: int,
        schedule_type: str,
    ):
        bot_data: BotData = context.bot_data.get('bot_data')
        if not bot_data:
            return

        group_unions = GROUP_UNIONS if schedule_type == "schedule" else EXAM_GROUP_UNIONS
        msg_new = "Jańa keste júklendi. Iltimas kesteńizdi kóriń!"
        msg_change = "Kesteńizde ózgeris boldı. Iltimas qayta tekserip kóriń!"

        if is_original:
            for user_id in bot_data.subscribed_users:
                if user_id != uploader_id:
                    try:
                        await context.bot.send_message(chat_id=user_id, text=msg_new)
                    except Exception:
                        pass
            if uploader_id in ALLOWED_USERS:
                try:
                    await context.bot.send_message(chat_id=uploader_id, text=msg_new)
                except Exception:
                    pass
            return

        old_df = get_from_db("original_schedule" if schedule_type == "schedule" else "exam_schedule", bot_data)
        new_df = get_from_db("changes_schedule" if schedule_type == "schedule" else "exam_schedule", bot_data)

        if old_df.empty or new_df.empty:
            return

        old_df = old_df.copy()
        new_df = new_df.copy()
        old_df["Oqitiwshi"] = old_df["Oqitiwshi"].astype(str).str.strip().str.lower()
        old_df["Topar"] = old_df["Topar"].astype(str).str.strip()
        new_df["Oqitiwshi"] = new_df["Oqitiwshi"].astype(str).str.strip().str.lower()
        new_df["Topar"] = new_df["Topar"].astype(str).str.strip()

        changes = pd.concat([old_df, new_df]).drop_duplicates(keep=False)
        if changes.empty:
            return

        affected_teachers = set(changes['Oqitiwshi'].dropna())
        affected_groups = set()
        for group_str in changes['Topar'].dropna():
            affected_groups.update(parse_groups(group_str))

        notified = set()
        for user_id, user_data in bot_data.users.items():
            if user_id in notified or (not user_data.notifications and user_id not in ALLOWED_USERS):
                continue
            should_notify = False
            if user_data.role == "Oqıtıwshı" and user_data.teacher_name:
                if user_data.teacher_name.lower() in affected_teachers:
                    should_notify = True
            elif user_data.role == "Student" and user_data.group in group_unions:
                if any(g in affected_groups for g in group_unions[user_data.group]):
                    should_notify = True
            if should_notify:
                try:
                    await context.bot.send_message(chat_id=user_id, text=msg_change)
                    notified.add(user_id)
                except Exception:
                    pass

        if uploader_id in ALLOWED_USERS and uploader_id not in notified:
            try:
                await context.bot.send_message(chat_id=uploader_id, text=msg_change)
            except Exception:
                pass
