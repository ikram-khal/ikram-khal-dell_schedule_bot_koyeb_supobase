"""
Combined Message handlers for the Combined Bot (Attendance + Schedule)
30-second location timeout REMOVED for real-time location tracking
"""
import os
import pandas as pd
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
import logging

from config.settings import ADMIN_USER_ID, ALLOWED_USERS, DATA_DIR, DRIVE_FOLDER_ID, GROUP_UNIONS, MIN_LIVE_PERIOD
from models.data_models import BotData, UserData
from database.db_operations import save_user_to_db, save_to_db
from services.drive_service import upload_to_drive

logger = logging.getLogger(__name__)

class MessageHandlers:
    def __init__(self, csv_handler, attendance_service, conversation_handlers, bot_data, notification_handler):
        self.csv_handler = csv_handler
        self.attendance_service = attendance_service
        self.conversation_handlers = conversation_handlers
        self.bot_data = bot_data
        self.notification_handler = notification_handler
        self.admin_user_id = ADMIN_USER_ID
    
    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /reset command to clear user data and allow re-registration"""
        user_id = str(update.effective_user.id)
        bot_data: BotData = context.bot_data.get('bot_data')

        if bot_data and user_id in bot_data.users:
            # Remove from subscribed users
            bot_data.subscribed_users.discard(user_id)
            # Reset user data
            bot_data.users[user_id] = UserData()
            # The user will be removed from Google Sheets when save_user_to_db is called next time
            # For now, just reset in memory

        # Remove from attendance database (AttendanceBotData)
        self.csv_handler.remove_teacher(user_id)
        self.csv_handler.remove_student(user_id)

        from ui.keyboards import ROLE_KEYBOARD
        await update.message.reply_text(
            "Sizdiń maǵlıwmatlarıńız óshirildi. Qayta dizimnen ótiw ushın óz rolińizdi tańlań:",
            reply_markup=ROLE_KEYBOARD
        )

    # Combined start command
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command for combined bot with proper registration flow"""
        user_id = update.effective_user.id
        bot_data = context.bot_data.setdefault('bot_data', BotData())
        
        # Schedule bot initialization
        if not bot_data.users:
            from database.db_operations import load_users_from_db
            bot_data.users = load_users_from_db(bot_data.drive_service)
            bot_data.subscribed_users = {uid for uid, ud in bot_data.users.items() if ud.notifications}
        
        if user_id not in bot_data.users:
            bot_data.users[user_id] = UserData()
            save_user_to_db(user_id, bot_data.users[user_id], bot_data.drive_service)
        else:
            bot_data.subscribed_users.add(user_id)
        
        # Import keyboards
        from ui.keyboards import MAIN_MENU_KEYBOARD, ROLE_KEYBOARD
        
        user_data = bot_data.users[user_id]
        if user_data.role:
            await update.message.reply_text(
                f"Salem! Siz {user_data.role} sıpatında rol oynaysız. Kesteni kóriw ushın túymeni basıń:",
                reply_markup=MAIN_MENU_KEYBOARD
            )
        else:
            await update.message.reply_text(
                "Salem! Botqa xosh keldińiz. Óz rolińizdi tańlań:",
                reply_markup=ROLE_KEYBOARD
            )
    
    # Schedule functionality
    async def notify_users_on(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /notify_users_on command"""
        user_id = update.message.from_user.id
        bot_data: BotData = context.bot_data.get('bot_data')
        
        if not bot_data or user_id not in bot_data.users:
            await update.message.reply_text("Iltimas, /start buyrıǵın baslań!")
            return
        
        user_data = bot_data.users[user_id]
        user_data.notifications = True
        bot_data.subscribed_users.add(user_id)
        save_user_to_db(user_id, user_data, bot_data.drive_service)
        await update.message.reply_text(
            "Xabarlandırıwlar qosıldı! Erteń sabaq/imtixan bolsa, sizge xabar jiberiledi."
        )
    
    async def notify_users_off(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /notify_users_off command"""
        user_id = update.message.from_user.id
        bot_data: BotData = context.bot_data.get('bot_data')
        
        if not bot_data or user_id not in bot_data.users:
            await update.message.reply_text("Iltimas, /start buyrıǵın baslań!")
            return
        
        user_data = bot_data.users[user_id]
        user_data.notifications = False
        bot_data.subscribed_users.discard(user_id)
        save_user_to_db(user_id, user_data, bot_data.drive_service)
        await update.message.reply_text("Xabarlandırıwlar óshirildi!")
    
    async def handle_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle file uploads for schedule"""
        user_id = update.message.from_user.id
        if user_id not in ALLOWED_USERS:
            await update.message.reply_text("Sizde fayldı júklew ruxsatı joq!")
            return
        
        bot_data: BotData = context.bot_data.setdefault('bot_data', BotData())
        file_name = update.message.document.file_name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        file_configs = {
            "keste_bot_orig.xlsx": ("original_schedule", "schedule", True),
            "keste_bot_ozgeris.xlsx": ("changes_schedule", "schedule", False),
            "imtixan_keste.xlsx": ("exam_schedule", "exam", True)
        }
        
        if file_name not in file_configs:
            await update.message.reply_text(
                "Qátelik! Fayl atı durıs emes. 'keste_bot_orig.xlsx', 'keste_bot_ozgeris.xlsx' yamasa 'imtixan_keste.xlsx' bolıwı kerek."
            )
            return
        
        table_name, schedule_type, is_original = file_configs[file_name]
        file_path = os.path.join(DATA_DIR, f"{file_name.split('.')[0]}_{timestamp}.xlsx")
        
        # Download file
        file = await update.message.document.get_file()
        await file.download_to_drive(file_path)
        
        # Update bot data file paths
        if schedule_type == "schedule":
            bot_data.last_schedule_file = file_path
            if is_original:
                bot_data.original_schedule_file = file_path
        else:
            bot_data.exam_file = file_path
        
        # Save to database
        df = pd.read_excel(file_path, sheet_name="keste", engine="openpyxl")
        save_to_db(df, table_name, bot_data.drive_service)
        upload_to_drive(bot_data.drive_service, file_path, DRIVE_FOLDER_ID)
        
        # Update cache
        if table_name == "exam_schedule":
            bot_data.exam_cache = df
        else:
            bot_data.schedule_cache = df

        # Send notifications
        await self.notification_handler.notify_users(context, is_original, user_id, schedule_type)

        await update.message.reply_text("Fayl sátli júklendi hám tekserildi!")
    
    # Attendance functionality
    async def check_attendance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle attendance checking"""
        user_id = str(update.effective_user.id)
        teachers = self.csv_handler.get_teachers()
        
        teacher = next((t for t in teachers if str(t.get("user_id", "")).strip() == user_id), None)
        if not teacher:
            keyboard = [[InlineKeyboardButton("Oqıtıwshı", callback_data="teacher")]]
            await update.message.reply_text(
                "Siz oqıtıwshı sıpatında dizimnen ótpegensiz.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ConversationHandler.END
        
        teacher_group = teacher.get("group", "")
        if not teacher_group:
            keyboard = [
                [InlineKeyboardButton("Qatnastı tekseriw", callback_data="check_attendance")],
                [InlineKeyboardButton("Mektep koordinatların jańalaw", callback_data="update_coordinates")]
            ]
            await update.message.reply_text(
                "Qátelik: sizde topar kórsetilmegen.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ConversationHandler.END
        
        report = self.attendance_service.get_attendance_report(teacher_group)
        keyboard = [
            [InlineKeyboardButton("Qatnastı tekseriw", callback_data="check_attendance")],
            [InlineKeyboardButton("Mektep koordinatların jańalaw", callback_data="update_coordinates")]
        ]
        await update.message.reply_text(report, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
    
    async def update_school_coordinates(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle school coordinates update"""
        user_id = str(update.effective_user.id)
        teachers = self.csv_handler.get_teachers()
        
        teacher = next((t for t in teachers if str(t.get("user_id", "")).strip() == user_id), None)
        if not teacher:
            keyboard = [[InlineKeyboardButton("Oqıtıwshı", callback_data="teacher")]]
            await update.message.reply_text(
                "Siz oqıtıwshı sıpatında dizimnen ótpegensiz.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ConversationHandler.END
        
        context.user_data["role"] = "teacher"
        context.user_data["school"] = teacher.get("school", "")
        await update.message.reply_text(
            "Mekteptiń jańa geolokaciyasın jiberiń (waqıt sheklew joq)."
        )
        return await self.conversation_handlers.teacher_location(update, context)
    
    # Combined message handling
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages for both functionalities"""
        user_id = update.message.from_user.id
        text = update.message.text.strip()
        bot_data: BotData = context.bot_data.get('bot_data')
        
        # Attendance functionality
        if text == "Oqıtıwshı":
            return await self.conversation_handlers.teacher_flow_start(update, context)
        elif text == "Student":
            return await self.conversation_handlers.student_flow_start(update, context)
        elif text == "Qatnastı tekseriw":
            return await self.check_attendance(update, context)
        elif text == "Mektep koordinatların jańalaw":
            return await self.update_school_coordinates(update, context)
        
        # Schedule functionality
        if not bot_data or user_id not in bot_data.users:
            await update.message.reply_text("Iltimas, /start buyrıǵın baslań!")
            return
        
        user_data = bot_data.users[user_id]
        
        # Handle teacher name input
        if user_data.role == "Oqıtıwshı" and not user_data.teacher_name:
            user_data.teacher_name = text.strip()
            save_user_to_db(user_id, user_data, bot_data.drive_service)
            from ui.keyboards import MAIN_MENU_KEYBOARD
            await update.message.reply_text(
                f"Siz {text} sıpatında dizimnen óttińiz. Kesteni kóriw ushın túymeni basıń:",
                reply_markup=MAIN_MENU_KEYBOARD
            )
        
        # Handle student group input
        elif user_data.role == "Student" and not user_data.group:
            if text not in GROUP_UNIONS:
                await update.message.reply_text(f"Topar '{text}' tabılmadı. Durıs topar atın jazıń!")
                return
            
            user_data.group = text
            save_user_to_db(user_id, user_data, bot_data.drive_service)
            from ui.keyboards import MAIN_MENU_KEYBOARD
            await update.message.reply_text(
                f"Siz {text} toparı sıpatında dizimnen óttińiz. Kesteni kóriw ushın túymeni basıń:",
                reply_markup=MAIN_MENU_KEYBOARD
            )
    
    # Location handling - ONLY LIVE LOCATION ACCEPTED
    async def handle_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle location messages outside of conversation - ONLY LIVE LOCATION ACCEPTED"""
        location = update.message.location
        keyboard = [
            [InlineKeyboardButton("Keldim", callback_data="came")],
            [InlineKeyboardButton("Kettim", callback_data="left")],
            [InlineKeyboardButton("Artqa qaytıw", callback_data="back_main")]
        ]
        
        # Check if location is forwarded or not live location
        if (hasattr(update.message, 'forward_date') and update.message.forward_date) or \
           not hasattr(location, 'live_period') or location.live_period is None:
            await update.message.reply_text(
                'Iltimas, tek "Транслировать геопозицию" túymesi arqalı ózińizdiń real ornıńızdı jiberiń! Basqa birewden alınǵan yáki ózgertilgen geolokaciyalar qabıl etilmeydi.',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ConversationHandler.END
        
        await update.message.reply_text(
            "'Keldim' yamasa 'Kettim' túymesin basıń, soń geolokaciyańızdı jiberiń (real waqıt).",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END
    
    async def handle_restricted_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle forwarded locations"""
        keyboard = [
            [InlineKeyboardButton("Keldim", callback_data="came")],
            [InlineKeyboardButton("Kettim", callback_data="left")],
            [InlineKeyboardButton("Artqa qaytıw", callback_data="back_main")]
        ]
        await update.message.reply_text(
            'Iltimas, tek "Транслировать геопозицию" túymesi arqalı ózińizdiń real ornıńızdı jiberiń! Basqa birewden alınǵan yáki ózgertilgen geolokaciyalar qabıl etilmeydi.',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END
    
    # Common handlers
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /cancel command"""
        from ui.keyboards import MAIN_MENU_KEYBOARD
        await update.message.reply_text(
            "Operaciya toxtatıldı. Jańadan baslaw ushın /start buyrıǵın basıń.",
            reply_markup=MAIN_MENU_KEYBOARD
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    async def handle_invalid_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle invalid input"""
        keyboard = [
            [InlineKeyboardButton("📚 Keste", callback_data="schedule_menu")],
            [InlineKeyboardButton("📍 Qatnas", callback_data="attendance_menu")]
        ]
        await update.message.reply_text(
            "Tiyisli túymeni basıń yáki komandanı qayta jiberiń.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error("Error occurred: %s", context.error, exc_info=True)
        if update and update.message:
            keyboard = [
                [InlineKeyboardButton("📚 Keste", callback_data="schedule_menu")],
                [InlineKeyboardButton("📍 Qatnas", callback_data="attendance_menu")]
            ]
            await update.message.reply_text(
                "Qátelik júz berdi. Birazdan qaytadan urınıp kóriń.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

