"""
Combined Message handlers for the Combined Bot (Attendance + Schedule)
"""
import os
import tempfile
import pandas as pd
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
import logging

from config.settings import ADMIN_USER_ID, ALLOWED_USERS, GROUP_UNIONS, MIN_LIVE_PERIOD
from models.data_models import BotData, UserData
from database.db_operations import save_user_to_db, save_to_db, delete_user_from_db

logger = logging.getLogger(__name__)


class MessageHandlers:
    def __init__(self, db_handler, attendance_service, conversation_handlers, bot_data, notification_handler):
        self.db_handler = db_handler
        self.attendance_service = attendance_service
        self.conversation_handlers = conversation_handlers
        self.bot_data = bot_data
        self.notification_handler = notification_handler
        self.admin_user_id = ADMIN_USER_ID

    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /reset command"""
        user_id = str(update.effective_user.id)
        bot_data: BotData = context.bot_data.get('bot_data')

        int_uid = int(user_id)

        # Clear from Supabase (all 3 tables)
        delete_user_from_db(int_uid)
        self.db_handler.remove_teacher(user_id)
        self.db_handler.remove_student(user_id)

        # Clear from in-memory cache
        if bot_data:
            bot_data.subscribed_users.discard(int_uid)
            bot_data.users.pop(int_uid, None)

        from ui.keyboards import ROLE_KEYBOARD
        await update.message.reply_text(
            "Sizdiń maǵlıwmatlarıńız óshirildi. Qayta dizimnen ótiw ushın óz rolińizdi tańlań:",
            reply_markup=ROLE_KEYBOARD,
        )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        bot_data: BotData = context.bot_data.setdefault('bot_data', BotData())

        if not bot_data.users:
            from database.db_operations import load_users_from_db
            bot_data.users = load_users_from_db()
            bot_data.subscribed_users = {uid for uid, ud in bot_data.users.items() if ud.notifications}

        if user_id not in bot_data.users:
            bot_data.users[user_id] = UserData()
            save_user_to_db(user_id, bot_data.users[user_id])
        else:
            bot_data.subscribed_users.add(user_id)

        from ui.keyboards import MAIN_MENU_KEYBOARD, ROLE_KEYBOARD
        user_data = bot_data.users[user_id]
        if user_data.role:
            await update.message.reply_text(
                f"Salem! Siz {user_data.role} sıpatında rol oynaysız. Kesteni kóriw ushın túymeni basıń:",
                reply_markup=MAIN_MENU_KEYBOARD,
            )
        else:
            await update.message.reply_text(
                "Salem! Botqa xosh keldińiz. Óz rolińizdi tańlań:",
                reply_markup=ROLE_KEYBOARD,
            )

    async def notify_users_on(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        bot_data: BotData = context.bot_data.get('bot_data')
        if not bot_data or user_id not in bot_data.users:
            await update.message.reply_text("Iltimas, /start buyrıǵın baslań!")
            return
        user_data = bot_data.users[user_id]
        user_data.notifications = True
        bot_data.subscribed_users.add(user_id)
        save_user_to_db(user_id, user_data)
        await update.message.reply_text("Xabarlandırıwlar qosıldı!")

    async def notify_users_off(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        bot_data: BotData = context.bot_data.get('bot_data')
        if not bot_data or user_id not in bot_data.users:
            await update.message.reply_text("Iltimas, /start buyrıǵın baslań!")
            return
        user_data = bot_data.users[user_id]
        user_data.notifications = False
        bot_data.subscribed_users.discard(user_id)
        save_user_to_db(user_id, user_data)
        await update.message.reply_text("Xabarlandırıwlar óshirildi!")

    async def handle_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle .xlsx file uploads for schedule — saves directly to Supabase"""
        user_id = update.message.from_user.id
        if user_id not in ALLOWED_USERS:
            await update.message.reply_text("Sizde fayldı júklew ruxsatı joq!")
            return

        bot_data: BotData = context.bot_data.setdefault('bot_data', BotData())
        file_name = update.message.document.file_name

        file_configs = {
            "keste_bot_orig.xlsx": ("original_schedule", "schedule", True),
            "keste_bot_ozgeris.xlsx": ("changes_schedule", "schedule", False),
            "imtixan_keste.xlsx": ("exam_schedule", "exam", True),
        }

        if file_name not in file_configs:
            await update.message.reply_text(
                "Qátelik! Fayl atı durıs emes.\n"
                "Kerekli atlar: 'keste_bot_orig.xlsx', 'keste_bot_ozgeris.xlsx' yamasa 'imtixan_keste.xlsx'"
            )
            return

        table_name, schedule_type, is_original = file_configs[file_name]

        # Download to temp file
        tmp_path = os.path.join(tempfile.gettempdir(), file_name)
        tg_file = await update.message.document.get_file()
        await tg_file.download_to_drive(tmp_path)

        try:
            df = pd.read_excel(tmp_path, sheet_name="keste", engine="openpyxl")
            save_to_db(df, table_name)

            # Update in-memory cache
            if table_name == "exam_schedule":
                bot_data.exam_cache = df
            else:
                bot_data.schedule_cache = df

        except Exception as e:
            logger.error(f"Error processing schedule file: {e}")
            await update.message.reply_text(f"Fayl óńlew qátesi: {e}")
            return
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

        await self.notification_handler.notify_users(context, is_original, user_id, schedule_type)
        await update.message.reply_text("Fayl sátli júklendi hám Supabase'ge saqlandı!")

    async def check_attendance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle attendance checking for teachers"""
        user_id = str(update.effective_user.id)
        teachers = self.db_handler.get_teachers()
        teacher = next((t for t in teachers if str(t.get("user_id", "")).strip() == user_id), None)

        if not teacher:
            keyboard = [[InlineKeyboardButton("Oqıtıwshı", callback_data="teacher")]]
            await update.message.reply_text(
                "Siz oqıtıwshı sıpatında dizimnen ótpegensiz.",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return ConversationHandler.END

        teacher_group = teacher.get("group", "")
        if not teacher_group:
            keyboard = [
                [InlineKeyboardButton("Qatnastı tekseriw", callback_data="check_attendance")],
                [InlineKeyboardButton("Mektep koordinatların jańalaw", callback_data="update_coordinates")],
            ]
            await update.message.reply_text(
                "Qátelik: sizde topar kórsetilmegen.",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return ConversationHandler.END

        report = self.attendance_service.get_attendance_report(teacher_group)
        keyboard = [
            [InlineKeyboardButton("Qatnastı tekseriw", callback_data="check_attendance")],
            [InlineKeyboardButton("Mektep koordinatların jańalaw", callback_data="update_coordinates")],
        ]
        await update.message.reply_text(report, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END

    async def update_school_coordinates(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        teachers = self.db_handler.get_teachers()
        teacher = next((t for t in teachers if str(t.get("user_id", "")).strip() == user_id), None)

        if not teacher:
            keyboard = [[InlineKeyboardButton("Oqıtıwshı", callback_data="teacher")]]
            await update.message.reply_text(
                "Siz oqıtıwshı sıpatında dizimnen ótpegensiz.",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return ConversationHandler.END

        context.user_data["role"] = "teacher"
        context.user_data["school"] = teacher.get("school", "")
        await update.message.reply_text("Mekteptiń jańa geolokaciyasın jiberiń.")
        return await self.conversation_handlers.teacher_location(update, context)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        user_id = update.message.from_user.id
        text = update.message.text.strip()
        bot_data: BotData = context.bot_data.get('bot_data')

        if text == "Oqıtıwshı":
            return await self.conversation_handlers.teacher_flow_start(update, context)
        elif text == "Student":
            return await self.conversation_handlers.student_flow_start(update, context)
        elif text == "Qatnastı tekseriw":
            return await self.check_attendance(update, context)
        elif text == "Mektep koordinatların jańalaw":
            return await self.update_school_coordinates(update, context)

        if not bot_data or user_id not in bot_data.users:
            await update.message.reply_text("Iltimas, /start buyrıǵın baslań!")
            return

        user_data = bot_data.users[user_id]

        if user_data.role == "Oqıtıwshı" and not user_data.teacher_name:
            user_data.teacher_name = text.strip()
            save_user_to_db(user_id, user_data)
            from ui.keyboards import MAIN_MENU_KEYBOARD
            await update.message.reply_text(
                f"Siz {text} sıpatında dizimnen óttińiz. Kesteni kóriw ushın túymeni basıń:",
                reply_markup=MAIN_MENU_KEYBOARD,
            )

        elif user_data.role == "Student" and not user_data.group:
            # Group selection is now button-based — redirect to course selection
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = [
                [InlineKeyboardButton("1-kurs", callback_data="sch_c_1")],
                [InlineKeyboardButton("2-kurs", callback_data="sch_c_2")],
                [InlineKeyboardButton("3-kurs", callback_data="sch_c_3")],
                [InlineKeyboardButton("4-kurs", callback_data="sch_c_4")],
            ]
            await update.message.reply_text("Kursıńızdı tańlań:", reply_markup=InlineKeyboardMarkup(keyboard))

    async def handle_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle location messages outside conversation — only live location accepted"""
        location = update.message.location
        keyboard = [
            [InlineKeyboardButton("Keldim", callback_data="came")],
            [InlineKeyboardButton("Kettim", callback_data="left")],
            [InlineKeyboardButton("Artqa qaytıw", callback_data="back_main")],
        ]
        if (hasattr(update.message, 'forward_date') and update.message.forward_date) or \
                not hasattr(location, 'live_period') or location.live_period is None:
            await update.message.reply_text(
                'Iltimas, tek "Транслировать геопозицию" túymesi arqalı ózińizdiń real ornıńızdı jiberiń!',
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return ConversationHandler.END
        await update.message.reply_text(
            "'Keldim' yamasa 'Kettim' túymesin basıń, soń geolokaciyańızdı jiberiń.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return ConversationHandler.END

    async def handle_restricted_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("Keldim", callback_data="came")],
            [InlineKeyboardButton("Kettim", callback_data="left")],
            [InlineKeyboardButton("Artqa qaytıw", callback_data="back_main")],
        ]
        await update.message.reply_text(
            'Iltimas, tek "Транслировать геопозицию" túymesi arqalı ózińizdiń real ornıńızdı jiberiń!',
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from ui.keyboards import MAIN_MENU_KEYBOARD
        await update.message.reply_text(
            "Operaciya toxtatıldı.",
            reply_markup=MAIN_MENU_KEYBOARD,
        )
        context.user_data.clear()
        return ConversationHandler.END

    async def handle_invalid_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("📚 Keste", callback_data="schedule_menu")],
            [InlineKeyboardButton("📍 Qatnas", callback_data="attendance_menu")],
        ]
        await update.message.reply_text(
            "Tiyisli túymeni basıń yáki komandanı qayta jiberiń.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return ConversationHandler.END

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error("Error occurred: %s", context.error, exc_info=True)
        if update and update.message:
            keyboard = [
                [InlineKeyboardButton("📚 Keste", callback_data="schedule_menu")],
                [InlineKeyboardButton("📍 Qatnas", callback_data="attendance_menu")],
            ]
            await update.message.reply_text(
                "Qátelik júz berdi. Birazdan qaytadan urınıp kóriń.",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
