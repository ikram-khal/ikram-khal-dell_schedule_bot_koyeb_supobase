import uuid
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
import logging

from config.settings import (
    TEACHER_NAME, TEACHER_COURSE, TEACHER_GROUP, TEACHER_SCHOOL, TEACHER_LOCATION,
    STUDENT_NAME, STUDENT_COURSE, STUDENT_GROUP, STUDENT_SCHOOL, STUDENT_LOCATION,
    GROUPS, SCHOOLS, TIMEZONE, COURSE_GROUPS
)

logger = logging.getLogger(__name__)

class ConversationHandlers:
    def __init__(self, csv_handler, location_service, attendance_service):
        self.csv_handler = csv_handler
        self.location_service = location_service
        self.attendance_service = attendance_service
    
    # Teacher Registration Flow
    async def teacher_flow_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start teacher registration flow"""
        user_id = str(update.effective_user.id)
        teachers = self.csv_handler.get_teachers()
        
        if any(str(t.get("user_id", "")).strip() == user_id for t in teachers):
            from ui.keyboards import TEACHER_ATTENDANCE_KEYBOARD
            await update.message.reply_text(
                "Siz dizimnen ótkensiz!",
                reply_markup=TEACHER_ATTENDANCE_KEYBOARD
            )
            return ConversationHandler.END
        
        context.user_data["role"] = "teacher"
        context.user_data["user_id"] = user_id
        await update.message.reply_text("Tolıq atı jónińizdi kiritiń (Familiyası, atı):")
        return TEACHER_NAME
    
    async def teacher_flow_start_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Teacher flow start for callback queries"""
        user_id = str(query.from_user.id)
        teachers = self.csv_handler.get_teachers()
        
        if any(str(t.get("user_id", "")).strip() == user_id for t in teachers):
            from ui.keyboards import TEACHER_ATTENDANCE_KEYBOARD
            await query.edit_message_text(
                "Siz dizimnen ótkensiz!",
                reply_markup=TEACHER_ATTENDANCE_KEYBOARD
            )
            return ConversationHandler.END
        
        context.user_data["role"] = "teacher"
        context.user_data["user_id"] = user_id
        await query.edit_message_text("Tolıq atı jónińizdi kiritiń (Familiyası, atı):")
        return TEACHER_NAME
    
    async def teacher_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle teacher name input"""
        name = update.message.text.strip()
        if not name:
            await update.message.reply_text("Iltimas durıs at kiritiń.")
            return TEACHER_NAME
        
        context.user_data["name"] = name
        keyboard = [[InlineKeyboardButton(course, callback_data=f"course_{course}")] for course in COURSE_GROUPS.keys()]
        await update.message.reply_text(
            "Kursıńızdı tańlań:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return TEACHER_COURSE
    
    async def teacher_course(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle teacher course selection"""
        course = update.message.text.strip()
        if course not in COURSE_GROUPS:
            keyboard = [[InlineKeyboardButton(course, callback_data=f"course_{course}")] for course in COURSE_GROUPS.keys()]
            await update.message.reply_text(
                f"Dizimnen kursıńızdı saylań: {', '.join(COURSE_GROUPS.keys())}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return TEACHER_COURSE
        
        context.user_data["course"] = course
        course_groups = COURSE_GROUPS[course]
        keyboard = [[InlineKeyboardButton(group, callback_data=f"group_{group}")] for group in course_groups]
        await update.message.reply_text(
            f"{course} toparlarınan óz toparıńızdı saylań:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return TEACHER_GROUP
    
    async def teacher_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle teacher group selection"""
        group = update.message.text.strip()
        selected_course = context.user_data.get("course", "")
        course_groups = COURSE_GROUPS.get(selected_course, GROUPS)
        
        if group not in course_groups:
            keyboard = [[InlineKeyboardButton(group, callback_data=f"group_{group}")] for group in course_groups]
            await update.message.reply_text(
                f"Dizimnen topardı saylań: {', '.join(course_groups)}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return TEACHER_GROUP
        
        context.user_data["group"] = group
        keyboard = [[InlineKeyboardButton(school, callback_data=f"school_{school}")] for school in SCHOOLS]
        await update.message.reply_text(
            "Mektepti saylań:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return TEACHER_SCHOOL
    
    async def teacher_school(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle teacher school selection"""
        school = update.message.text.strip()
        if school not in SCHOOLS:
            keyboard = [[InlineKeyboardButton(school, callback_data=f"school_{school}")] for school in SCHOOLS]
            await update.message.reply_text(
                f"Dizimnen mektepti saylań: {', '.join(SCHOOLS)}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return TEACHER_SCHOOL
        
        context.user_data["school"] = school
        success = self.csv_handler.add_teacher(
            context.user_data["user_id"],
            context.user_data["name"],
            context.user_data["group"],
            context.user_data["school"]
        )
        
        if success:
            await update.message.reply_text("Mektep geolokaciyasın jiberiń (waqıt sheklew joq).")
            return TEACHER_LOCATION
        else:
            await update.message.reply_text("Oqıtıwshı dizimge qosıwda qátelik.")
            return ConversationHandler.END
    
    async def teacher_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle teacher location for school coordinates"""
        location = update.message.location
        if not location:
            await update.message.reply_text("Geolokaciyańızdı jiberiń.")
            return TEACHER_LOCATION
        
        school_name = context.user_data.get("school", "")
        success = self.csv_handler.update_school_coordinates(school_name, location.latitude, location.longitude)
        
        if success:
            await update.message.reply_text("Mektep koordinatları sátli saqlandı!")
        else:
            await update.message.reply_text("Koordinatalar saqlaw qátesi.")
        
        from ui.keyboards import MAIN_MENU_KEYBOARD
        try:
            logger.info(f"Sending main menu to teacher: {MAIN_MENU_KEYBOARD}")
            await update.message.reply_text(
                f"Siz oqıtıwshı sıpatında dizimnen óttińiz. Kesteni kóriw ushın túymeni basıń:",
                reply_markup=MAIN_MENU_KEYBOARD
            )
            logger.info("Main menu sent successfully to teacher")
        except Exception as e:
            logger.error(f"Error sending main menu to teacher: {e}")
            await update.message.reply_text("Qátelik júz berdi. Ákimge habarlasıń.")
        
        context.user_data.clear()
        return ConversationHandler.END
    
    # Student Registration Flow
    async def student_flow_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start student registration flow"""
        user_id = str(update.effective_user.id)
        students = self.csv_handler.get_students()
        
        if any(str(s.get("user_id", "")).strip() == user_id for s in students):
            student = next(s for s in students if str(s.get("user_id", "")).strip() == user_id)
            context.user_data["student"] = {
                "student_id": student.get("student_id", ""),
                "group": student.get("group", ""),
                "school": student.get("school", "")
            }
            from ui.keyboards import ATTENDANCE_ACTION_KEYBOARD
            await update.message.reply_text(
                f"Dizimnen ótkensiz! Geolokaciyanı jiberiw ushın, 'Keldim' yamasa 'Kettim' túymesin basıń.",
                reply_markup=ATTENDANCE_ACTION_KEYBOARD
            )
            return ConversationHandler.END
        
        context.user_data["role"] = "student"
        context.user_data["user_id"] = user_id
        context.user_data["student_id"] = str(uuid.uuid4())
        await update.message.reply_text("Tolıq atı-jónińizdi kiritiń (Familiya, at):")
        return STUDENT_NAME
    
    async def student_flow_start_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Student flow start for callback queries"""
        user_id = str(query.from_user.id)
        students = self.csv_handler.get_students()
        
        if any(str(s.get("user_id", "")).strip() == user_id for s in students):
            student = next(s for s in students if str(s.get("user_id", "")).strip() == user_id)
            context.user_data["student"] = {
                "student_id": student.get("student_id", ""),
                "group": student.get("group", ""),
                "school": student.get("school", "")
            }
            from ui.keyboards import ATTENDANCE_ACTION_KEYBOARD
            await query.edit_message_text(
                f"Dizimnen ótkensiz! Geolokaciyanı jiberiw ushın, 'Keldim' yamasa 'Kettim' túymesin basıń.",
                reply_markup=ATTENDANCE_ACTION_KEYBOARD
            )
            return ConversationHandler.END
        
        context.user_data["role"] = "student"
        context.user_data["user_id"] = user_id
        context.user_data["student_id"] = str(uuid.uuid4())
        await query.edit_message_text("Tolıq atı-jónińizdi kiritiń (Familiya, at):")
        return STUDENT_NAME
    
    async def student_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle student name input"""
        name = update.message.text.strip()
        if not name:
            await update.message.reply_text("Iltimas durıs at kiritiń.")
            return STUDENT_NAME
        
        context.user_data["name"] = name
        keyboard = [[InlineKeyboardButton(course, callback_data=f"course_{course}")] for course in COURSE_GROUPS.keys()]
        await update.message.reply_text(
            "Kursıńızdı saylań:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return STUDENT_COURSE
    
    async def student_course(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle student course selection"""
        course = update.message.text.strip()
        if course not in COURSE_GROUPS:
            keyboard = [[InlineKeyboardButton(course, callback_data=f"course_{course}")] for course in COURSE_GROUPS.keys()]
            await update.message.reply_text(
                f"Dizimnen kursıńızdı saylań: {', '.join(COURSE_GROUPS.keys())}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return STUDENT_COURSE
        
        context.user_data["course"] = course
        course_groups = COURSE_GROUPS[course]
        keyboard = [[InlineKeyboardButton(group, callback_data=f"group_{group}")] for group in course_groups]
        await update.message.reply_text(
            f"{course} toparlarınan óz toparıńızdı saylań:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return STUDENT_GROUP
    
    async def student_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle student group selection"""
        group = update.message.text.strip()
        selected_course = context.user_data.get("course", "")
        course_groups = COURSE_GROUPS.get(selected_course, GROUPS)
        
        if group not in course_groups:
            keyboard = [[InlineKeyboardButton(group, callback_data=f"group_{group}")] for group in course_groups]
            await update.message.reply_text(
                f"Dizimnen toparıńızdı saylań: {', '.join(course_groups)}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return STUDENT_GROUP
        
        context.user_data["group"] = group
        keyboard = [[InlineKeyboardButton(school, callback_data=f"school_{school}")] for school in SCHOOLS]
        await update.message.reply_text(
            "Mektepti saylań:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return STUDENT_SCHOOL
    
    async def student_school(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle student school selection"""
        school = update.message.text.strip()
        if school not in SCHOOLS:
            keyboard = [[InlineKeyboardButton(school, callback_data=f"school_{school}")] for school in SCHOOLS]
            await update.message.reply_text(
                f"Dizimnen mektebińizdi saylań: {', '.join(SCHOOLS)}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return STUDENT_SCHOOL
        
        context.user_data["school"] = school
        success = self.csv_handler.add_student(
            context.user_data["user_id"],
            context.user_data["name"],
            context.user_data["student_id"],
            context.user_data["group"],
            context.user_data["school"]
        )
        
        from ui.keyboards import MAIN_MENU_KEYBOARD
        try:
            logger.info(f"Sending main menu to student: {MAIN_MENU_KEYBOARD}")
            if success:
                context.user_data["student"] = {
                    "student_id": context.user_data["student_id"],
                    "group": context.user_data["group"],
                    "school": context.user_data["school"]
                }
                await update.message.reply_text(
                    f"Siz student sıpatında dizimnen óttińiz. Kesteni kóriw ushın túymeni basıń:",
                    reply_markup=MAIN_MENU_KEYBOARD
                )
            else:
                await update.message.reply_text(
                    "Studentti dizimge alıwda qátelik.",
                    reply_markup=MAIN_MENU_KEYBOARD
                )
            logger.info("Main menu sent successfully to student")
        except Exception as e:
            logger.error(f"Error sending main menu to student: {e}")
            await update.message.reply_text("Qátelik júz berdi. Adminge xabarlasıń.")
        
        context.user_data.clear()
        return ConversationHandler.END
    
    # Attendance Flow - NO TIMEOUT LIMITATION
    async def handle_attendance_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle attendance action (Keldim/Kettim) - NO TIMEOUT"""
        text = update.message.text
        user_id = str(update.effective_user.id).strip()
        students = self.csv_handler.get_students()
        
        student = next((s for s in students if str(s.get("user_id", "")).strip() == user_id), None)
        if not student:
            from ui.keyboards import ATTENDANCE_MENU_KEYBOARD
            await update.message.reply_text(
                "Siz student sıpatında dizimnen ótpegensiz.",
                reply_markup=ATTENDANCE_MENU_KEYBOARD
            )
            return ConversationHandler.END
        
        context.user_data.update({
            "attendance_action": text,
            "student_id": student.get("student_id", ""),
            "group": student.get("group", ""),
            "school": student.get("school", ""),
            "name": student.get("name", "Unknown"),
            "action_timestamp": datetime.now(TIMEZONE)
        })
        
        from ui.keyboards import ATTENDANCE_ACTION_KEYBOARD
        await update.message.reply_text(
            "Geolokaciyańızdı jiberiń! (Tek 'Транслировать геопозицию' túymesi arqalı jiberiń)",
            reply_markup=ATTENDANCE_ACTION_KEYBOARD
        )
        return STUDENT_LOCATION
    
    async def handle_student_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle student location for attendance - ONLY LIVE LOCATION ACCEPTED"""
        location = update.message.location
        
        # Validate location - only accept live location
        if not location:
            from ui.keyboards import ATTENDANCE_ACTION_KEYBOARD
            await update.message.reply_text(
                "Geolokaciyańızdı jiberiń! (Tek 'Транслировать геопозицию' túymesi arqalı jiberiń",
                reply_markup=ATTENDANCE_ACTION_KEYBOARD
            )
            return STUDENT_LOCATION
        
        # Check if location is forwarded or not live location
        if (hasattr(update.message, 'forward_date') and update.message.forward_date) or \
           not hasattr(location, 'live_period') or location.live_period is None:
            from ui.keyboards import ATTENDANCE_ACTION_KEYBOARD
            await update.message.reply_text(
                'Iltimas, tek "Транслировать геопозицию" túymesi arqalı ózińizdiń real ornıńızdı jiberiń! Basqa birewden alınǵan yáki ózgertilgen geolokaciyalar qabıl etilmeydi.',
                reply_markup=ATTENDANCE_ACTION_KEYBOARD
            )
            return STUDENT_LOCATION
        
        action = context.user_data.get("attendance_action")
        student_id = context.user_data.get("student_id")
        group = context.user_data.get("group")
        school = context.user_data.get("school")
        student_name = context.user_data.get("name", "Unknown")
        
        # Validate location against school coordinates
        is_valid, message = self.location_service.validate_location(location, school)
        if not is_valid:
            keyboard = [
                [InlineKeyboardButton("Keldim", callback_data="came")],
                [InlineKeyboardButton("Kettim", callback_data="left")],
                [InlineKeyboardButton("Artqa qaytıw", callback_data="back_main")]
            ]
            await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
            return ConversationHandler.END
        
        # Record attendance
        if action == "Keldim":
            success, result_message = self.attendance_service.record_arrival(student_id, student_name, group, school)
        elif action == "Kettim":
            success, result_message = self.attendance_service.record_departure(student_id, student_name, group, school)
        else:
            success, result_message = False, "Belgisiz ámeliyat."
        
        keyboard = [
            [InlineKeyboardButton("Keldim", callback_data="came")],
            [InlineKeyboardButton("Kettim", callback_data="left")],
            [InlineKeyboardButton("Artqa qaytıw", callback_data="back_main")]
        ]
        await update.message.reply_text(result_message, reply_markup=InlineKeyboardMarkup(keyboard))
        context.user_data.clear()
        return Conversationunion

