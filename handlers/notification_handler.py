"""
Notification handler for the Combined Telegram Bot
"""
import pandas as pd
from telegram.ext import ContextTypes
from typing import Set

from config.settings import ALLOWED_USERS, GROUP_UNIONS, EXAM_GROUP_UNIONS
from models.data_models import BotData
from database.db_operations import get_from_db
from utils.helpers import parse_groups


class NotificationHandler:
    def __init__(self):
        pass
    
    async def notify_users(self, context: ContextTypes.DEFAULT_TYPE, is_original: bool, uploader_id: int, schedule_type: str):
        """Notify users about schedule changes or new uploads"""
        bot_data: BotData = context.bot_data.get('bot_data')
        if not bot_data:
            return
        
        group_unions = GROUP_UNIONS if schedule_type == "schedule" else EXAM_GROUP_UNIONS
        message_new = "Jańa keste júklendi. Iltimas kesteńizdi kóriń!"
        message_change = "Kesteńizde ózgeris boldı. Iltimas qayta tekserip kóriń!"
        
        # Handle new original schedule upload
        if is_original:
            for user_id in bot_data.subscribed_users:
                if user_id != uploader_id:
                    try:
                        await context.bot.send_message(chat_id=user_id, text=message_new)
                    except Exception as e:
                        print(f"Failed to send notification to user {user_id}: {e}")
            
            # Notify admin uploader
            if uploader_id in ALLOWED_USERS:
                try:
                    await context.bot.send_message(chat_id=uploader_id, text=message_new)
                except Exception as e:
                    print(f"Failed to send notification to admin {uploader_id}: {e}")
            return
        
        # Handle schedule changes
        old_df = get_from_db("original_schedule" if schedule_type == "schedule" else "exam_schedule", bot_data.drive_service, bot_data)
        new_df = get_from_db("changes_schedule" if schedule_type == "schedule" else "exam_schedule", bot_data.drive_service, bot_data)
        
        if old_df.empty or new_df.empty:
            return
        
        # Normalize data for comparison
        old_df = old_df.copy()
        new_df = new_df.copy()
        old_df["Oqitiwshi"] = old_df["Oqitiwshi"].astype(str).str.strip().str.lower()
        old_df["Topar"] = old_df["Topar"].astype(str).str.strip()
        new_df["Oqitiwshi"] = new_df["Oqitiwshi"].astype(str).str.strip().str.lower()
        new_df["Topar"] = new_df["Topar"].astype(str).str.strip()
        
        # Find changes
        changes = pd.concat([old_df, new_df]).drop_duplicates(keep=False)
        if changes.empty:
            return
        
        # Get affected teachers and groups
        affected_teachers = set(changes['Oqitiwshi'].dropna())
        affected_groups = set()
        for group_str in changes['Topar'].dropna():
            affected_groups.update(parse_groups(group_str))
        
        # Notify affected users
        notified_users = set()
        for user_id, user_data in bot_data.users.items():
            if user_id in notified_users or (not user_data.notifications and user_id not in ALLOWED_USERS):
                continue
            
            should_notify = False
            
            # Check if teacher is affected
            if user_data.role == "Oqıtıwshı" and user_data.teacher_name:
                if user_data.teacher_name.lower() in affected_teachers:
                    should_notify = True
            
            # Check if student group is affected
            elif user_data.role == "Student" and user_data.group in group_unions:
                if any(group in affected_groups for group in group_unions[user_data.group]):
                    should_notify = True
            
            if should_notify:
                try:
                    await context.bot.send_message(chat_id=user_id, text=message_change)
                    notified_users.add(user_id)
                except Exception as e:
                    print(f"Failed to send notification to user {user_id}: {e}")
        
        # Notify admin uploader if not already notified
        if uploader_id in ALLOWED_USERS and uploader_id not in notified_users:
            try:
                await context.bot.send_message(chat_id=uploader_id, text=message_change)
            except Exception as e:
                print(f"Failed to send notification to admin {uploader_id}: {e}")
    
    async def send_daily_reminders(self, context: ContextTypes.DEFAULT_TYPE):
        """Send daily reminders about upcoming classes/exams (for future implementation)"""
        # This function can be implemented later for scheduled daily notifications
        pass
    
    async def notify_attendance_update(self, context: ContextTypes.DEFAULT_TYPE, student_name: str, action: str, group: str):
        """Notify teachers about student attendance updates"""
        bot_data: BotData = context.bot_data.get('bot_data')
        if not bot_data:
            return
        
        message = f"📋 Qatnastı jańalanıwı: {student_name} ({group}) - {action}"
        
        # Find teachers for this group and notify them
        for user_id, user_data in bot_data.users.items():
            if (user_data.role == "Oqıtıwshı" and 
                hasattr(user_data, 'group') and 
                user_data.group == group and
                getattr(user_data, 'notifications', True)):
                try:
                    await context.bot.send_message(chat_id=user_id, text=message)
                except Exception as e:
                    print(f"Failed to send attendance notification to teacher {user_id}: {e}")


# Standalone functions for backward compatibility
async def notify_users(context: ContextTypes.DEFAULT_TYPE, is_original: bool, uploader_id: int, schedule_type: str):
    """Notify users about schedule changes or new uploads"""
    handler = NotificationHandler()
    await handler.notify_users(context, is_original, uploader_id, schedule_type)


async def send_daily_reminders(context: ContextTypes.DEFAULT_TYPE):
    """Send daily reminders about upcoming classes/exams (for future implementation)"""
    handler = NotificationHandler()
    await handler.send_daily_reminders(context)
