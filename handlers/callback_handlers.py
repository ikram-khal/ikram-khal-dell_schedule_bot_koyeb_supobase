"""
Combined callback handlers for the Attendance and Schedule Bot
"""
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
import logging

from config.settings import (
    TEACHER_NAME, TEACHER_COURSE, TEACHER_GROUP, TEACHER_SCHOOL, TEACHER_LOCATION,
    STUDENT_NAME, STUDENT_COURSE, STUDENT_GROUP, STUDENT_SCHOOL, STUDENT_LOCATION,
    GROUPS, SCHOOLS, TIMEZONE, ALLOWED_USERS, GROUP_UNIONS,
    EXAM_GROUP_UNIONS, DAYS_OF_WEEK, DRIVE_FOLDER_ID, COURSE_GROUPS
)
from models.data_models import BotData
from database.db_operations import save_user_to_db, get_from_db, clear_db
from ui.keyboards import (
    MAIN_MENU_KEYBOARD, TEACHER_SCHEDULE_KEYBOARD, TEACHER_SCHEDULE_KEYBOARD_ADMIN,
    STUDENT_SCHEDULE_KEYBOARD, TEACHER_EXAM_KEYBOARD, TEACHER_EXAM_KEYBOARD_ADMIN,
    STUDENT_EXAM_KEYBOARD, DAY_KEYBOARD
)
from utils.helpers import (
    parse_groups, get_current_day, get_tomorrow_day, get_current_date, 
    get_tomorrow_date, get_current_week_dates, format_schedule, format_exam_schedule
)

logger = logging.getLogger(__name__)

class CallbackHandlers:
    def __init__(self, csv_handler, attendance_service, conversation_handlers):
        self.csv_handler = csv_handler
        self.attendance_service = attendance_service
        self.conversation_handlers = conversation_handlers
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline buttons"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        bot_data: BotData = context.bot_data.get('bot_data')
        
        # Handle schedule bot callbacks first (main menu and schedule functionality)
        if data in ["main_schedule", "main_exam", "back_main", "back_schedule"] or data.startswith("role_") or data.startswith("schedule_") or data.startswith("exam_") or data.startswith("day_"):
            return await button_handler(update, context)
        
        # Handle attendance menu
        elif data == "attendance_menu":
            user_id = str(query.from_user.id)
            
            # Check if user is already registered as a teacher
            teachers = self.csv_handler.get_teachers()
            teacher = next((t for t in teachers if str(t.get("user_id", "")).strip() == user_id), None)
            
            if teacher:
                # User is registered as teacher, show teacher interface
                context.user_data["role"] = "teacher"
                from ui.keyboards import TEACHER_ATTENDANCE_KEYBOARD
                await query.edit_message_text(
                    f"Sálem, {teacher.get('name', 'Oqıtıwshı')}! Tómendegilerden birin saylań:",
                    reply_markup=TEACHER_ATTENDANCE_KEYBOARD
                )
                return
            
            # Check if user is already registered as a student
            students = self.csv_handler.get_students()
            student = next((s for s in students if str(s.get("user_id", "")).strip() == user_id), None)
            
            if student:
                # User is registered as student, show student interface
                context.user_data["role"] = "student"
                context.user_data.update({
                    "student_id": student.get("student_id", ""),
                    "group": student.get("group", ""),
                    "school": student.get("school", ""),
                    "name": student.get("name", "Unknown")
                })
                from ui.keyboards import ATTENDANCE_ACTION_KEYBOARD
                await query.edit_message_text(
                    f"Sálem, {student.get('name', 'Student')}! Qatnastı belgilew ushın túymeni saylań:",
                    reply_markup=ATTENDANCE_ACTION_KEYBOARD
                )
                return
            
            # User is not registered, show role selection
            from ui.keyboards import ATTENDANCE_MENU_KEYBOARD
            await query.edit_message_text("Qatnastı belgilew ushın rolıńızdı saylań:", reply_markup=ATTENDANCE_MENU_KEYBOARD)
            return
        
        # Attendance bot callbacks
        elif data == "teacher":
            context.user_data["role"] = "teacher"
            return await self.conversation_handlers.teacher_flow_start_callback(query, context)
        elif data == "student":
            context.user_data["role"] = "student"
            return await self.conversation_handlers.student_flow_start_callback(query, context)
        elif data == "check_attendance":
            return await self.check_attendance_callback(query, context)
        elif data == "update_coordinates":
            return await self.update_school_coordinates_callback(query, context)
        elif data == "came":
            context.user_data['attendance_action'] = 'Keldim'
            return await self.handle_attendance_action_callback(query, context, "Keldim")
        elif data == "left":
            context.user_data['attendance_action'] = 'Kettim'
            return await self.handle_attendance_action_callback(query, context, "Kettim")
        elif data.startswith("course_"):
            course = data.replace("course_", "").replace("_", "-")
            if context.user_data.get("role") == "teacher":
                return await self.teacher_course_callback(query, context, course)
            else:
                return await self.student_course_callback(query, context, course)
        elif data.startswith("group_"):
            group = data.replace("group_", "").replace("_", " ")
            if context.user_data.get("role") == "teacher":
                return await self.teacher_group_callback(query, context, group)
            else:
                return await self.student_group_callback(query, context, group)
        elif data.startswith("school_"):
            school = data.replace("school_", "").replace("_", " ")
            if context.user_data.get("role") == "teacher":
                return await self.teacher_school_callback(query, context, school)
            else:
                return await self.student_school_callback(query, context, school)
        
        return ConversationHandler.END
    
    # Attendance bot callback methods
    async def check_attendance_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Check attendance for callback queries"""
        user_id = str(query.from_user.id)
        teachers = self.csv_handler.get_teachers()
        
        teacher = next((t for t in teachers if str(t.get("user_id", "")).strip() == user_id), None)
        if not teacher:
            from ui.keyboards import ATTENDANCE_MENU_KEYBOARD
            await query.edit_message_text(
                "Siz oqıtıwshı sıpatında dizimnen ótpegensiz.",
                reply_markup=ATTENDANCE_MENU_KEYBOARD
            )
            return ConversationHandler.END
        
        teacher_group = teacher.get("group", "")
        if not teacher_group:
            from ui.keyboards import TEACHER_ATTENDANCE_KEYBOARD
            await query.edit_message_text(
                "Qátelik: sizde topar kórsetilmegen.",
                reply_markup=TEACHER_ATTENDANCE_KEYBOARD
            )
            return ConversationHandler.END
        
        report = self.attendance_service.get_attendance_report(teacher_group)
        from ui.keyboards import TEACHER_ATTENDANCE_KEYBOARD
        await query.edit_message_text(report, reply_markup=TEACHER_ATTENDANCE_KEYBOARD)
        return ConversationHandler.END
    
    async def update_school_coordinates_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Update school coordinates for callback queries"""
        user_id = str(query.from_user.id)
        teachers = self.csv_handler.get_teachers()
        
        teacher = next((t for t in teachers if str(t.get("user_id", "")).strip() == user_id), None)
        if not teacher:
            keyboard = [[InlineKeyboardButton("Oqıtıwshı", callback_data="teacher")]]
            await query.edit_message_text(
                "Siz oqıtıwshı sıpatında dizimnen ótpegensiz.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ConversationHandler.END
        
        context.user_data["role"] = "teacher"
        context.user_data["school"] = teacher.get("school", "")
        await query.edit_message_text("Mekteptiń jańa geolokaciyasın real waqıtta jiberiń.")
        return TEACHER_LOCATION
    
    async def handle_attendance_action_callback(self, query, context: ContextTypes.DEFAULT_TYPE, action_text: str):
        """Handle attendance action for callback queries"""
        user_id = str(query.from_user.id).strip()
        students = self.csv_handler.get_students()
        
        if not students:
            keyboard = [[InlineKeyboardButton("Student", callback_data="student")]]
            await query.edit_message_text(
                "Qátelik: Studentler dizimi tabılmadı.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ConversationHandler.END

        student = next((s for s in students if str(s.get("user_id", "")).strip() == user_id), None)
        if not student:
            keyboard = [[InlineKeyboardButton("Student", callback_data="student")]]
            await query.edit_message_text(
                "Siz student sıpatında dizimnen ótpegensiz.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ConversationHandler.END
        
        context.user_data.update({
            "attendance_action": action_text,
            "student_id": student.get("student_id", ""),
            "group": student.get("group", ""),
            "school": student.get("school", ""),
            "name": student.get("name", "Unknown"),
            "action_timestamp": datetime.now(TIMEZONE)
        })
        
        keyboard = [
            [InlineKeyboardButton("Keldim", callback_data="came")],
            [InlineKeyboardButton("Kettim", callback_data="left")],
            [InlineKeyboardButton("Artqa qaytıw", callback_data="back_main")]
        ]
        await query.edit_message_text(
            "Geolokaciyańızdı real waqıtta jiberiń!!!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return STUDENT_LOCATION
    
    async def teacher_course_callback(self, query, context: ContextTypes.DEFAULT_TYPE, course: str):
        """Handle teacher course selection for callback queries"""
        if course not in COURSE_GROUPS:
            keyboard = [[InlineKeyboardButton(c, callback_data=f"course_{c}")] for c in COURSE_GROUPS.keys()]
            await query.edit_message_text(
                f"Dizimnen kursıńızdı tańlań: {', '.join(COURSE_GROUPS.keys())}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return TEACHER_COURSE
        
        context.user_data["course"] = course
        course_groups = COURSE_GROUPS[course]
        keyboard = [[InlineKeyboardButton(group, callback_data=f"group_{group}")] for group in course_groups]
        await query.edit_message_text(
            f"{course} toparlaran óz toparıńızdı saylań:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return TEACHER_GROUP
    
    async def teacher_group_callback(self, query, context: ContextTypes.DEFAULT_TYPE, group: str):
        """Handle teacher group selection for callback queries"""
        selected_course = context.user_data.get("course", "")
        course_groups = COURSE_GROUPS.get(selected_course, GROUPS)
        
        if group not in course_groups:
            keyboard = [[InlineKeyboardButton(g, callback_data=f"group_{g}")] for g in course_groups]
            await query.edit_message_text(
                f"Dizimnen topardı saylań: {', '.join(course_groups)}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return TEACHER_GROUP
        
        context.user_data["group"] = group
        keyboard = [[InlineKeyboardButton(school, callback_data=f"school_{school}")] for school in SCHOOLS]
        await query.edit_message_text(
            "Mektepti saylań:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return TEACHER_SCHOOL
    
    async def teacher_school_callback(self, query, context: ContextTypes.DEFAULT_TYPE, school: str):
        """Handle teacher school selection for callback queries"""
        if school not in SCHOOLS:
            keyboard = [[InlineKeyboardButton(s, callback_data=f"school_{s}")] for s in SCHOOLS]
            await query.edit_message_text(
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
            await query.edit_message_text("Mektep geolokaciyasın real waqıtta jiberiń.")
            return TEACHER_LOCATION
        else:
            await query.edit_message_text("Oqıtıwshı dizimge qosıwda qátelik.")
            return ConversationHandler.END
    
    async def student_course_callback(self, query, context: ContextTypes.DEFAULT_TYPE, course: str):
        """Handle student course selection for callback queries"""
        if course not in COURSE_GROUPS:
            keyboard = [[InlineKeyboardButton(c, callback_data=f"course_{c}")] for c in COURSE_GROUPS.keys()]
            await query.edit_message_text(
                f"Dizimnen kursıńızdı saylań: {', '.join(COURSE_GROUPS.keys())}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return STUDENT_COURSE
        
        context.user_data["course"] = course
        course_groups = COURSE_GROUPS[course]
        keyboard = [[InlineKeyboardButton(group, callback_data=f"group_{group}")] for group in course_groups]
        await query.edit_message_text(
            f"{course} toparlarınan óz toparıńızdı saylań:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return STUDENT_GROUP
    
    async def student_group_callback(self, query, context: ContextTypes.DEFAULT_TYPE, group: str):
        """Handle student group selection for callback queries"""
        selected_course = context.user_data.get("course", "")
        course_groups = COURSE_GROUPS.get(selected_course, GROUPS)
        
        if group not in course_groups:
            keyboard = [[InlineKeyboardButton(g, callback_data=f"group_{g}")] for g in course_groups]
            await query.edit_message_text(
                f"Dizimnen toparıńızdı saylań: {', '.join(course_groups)}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return STUDENT_GROUP
        
        context.user_data["group"] = group
        keyboard = [[InlineKeyboardButton(school, callback_data=f"school_{school}")] for school in SCHOOLS]
        await query.edit_message_text(
            "Mektepti saylań:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return STUDENT_SCHOOL
    
    async def student_school_callback(self, query, context: ContextTypes.DEFAULT_TYPE, school: str):
        """Handle student school selection for callback queries"""
        if school not in SCHOOLS:
            keyboard = [[InlineKeyboardButton(s, callback_data=f"school_{s}")] for s in SCHOOLS]
            await query.edit_message_text(
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
        
        if success:
            context.user_data["student"] = {
                "student_id": context.user_data["student_id"],
                "group": context.user_data["group"],
                "school": context.user_data["school"]
            }
            keyboard = [
                [InlineKeyboardButton("Keldim", callback_data="came")],
                [InlineKeyboardButton("Kettim", callback_data="left")],
                [InlineKeyboardButton("Artqa qaytıw", callback_data="back_main")]
            ]
            await query.edit_message_text(
                f"Dizimnen ótiw sátli juwmaqlandı! Geolokaciyanı jiberiw ushın, 'Keldim' yamasa 'Kettim' túymesin basıń.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.edit_message_text("Student dizimge qosıwda qátelik.")
        
        return ConversationHandler.END


# Schedule bot callback functions
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline keyboards"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    bot_data: BotData = context.bot_data.get('bot_data')
    callback_data = query.data
    
    # Handle back_main callback for all users (including attendance-only users)
    if callback_data == "back_main":
        await query.edit_message_text("Bas betke qaytıldı:", reply_markup=MAIN_MENU_KEYBOARD)
        return
    
    if not bot_data or user_id not in bot_data.users:
        await query.edit_message_text("Iltimas, /start buyrıǵın baslań!")
        return
    
    user_data = bot_data.users[user_id]
    
    # Main menu callbacks
    if callback_data == "main_schedule":
        # Check if user needs to register first
        if not user_data.role:
            from ui.keyboards import ROLE_KEYBOARD
            await query.edit_message_text("Sabaq kesteńizdi kóriw ushın, iltimas rolıńızdı saylań:", reply_markup=ROLE_KEYBOARD)
            return
        
        # Check if user has completed registration
        if user_data.role == "Oqıtıwshı" and not user_data.teacher_name:
            await query.edit_message_text("Iltimas atı jónińizdi jazıń (máselen: Xalmuratov I):")
            return
        elif user_data.role == "Student" and not user_data.group:
            await query.edit_message_text("Toparıńızdı jazıń (máselen: 101, 201, 301, 4G):")
            return
        
        user_data.state = "schedule"
        save_user_to_db(user_id, user_data, bot_data.drive_service)
        keyboard = get_schedule_keyboard(user_id, user_data.role)
        await query.edit_message_text("Sabaq kesteńizdi kóriw ushın túymeni saylań:", reply_markup=keyboard)
    
    elif callback_data == "main_exam":
        # Check if user needs to register first
        if not user_data.role:
            from ui.keyboards import ROLE_KEYBOARD
            await query.edit_message_text("Imtixan kesteńizdi kóriw ushın, iltimas rolıńızdı saylań:", reply_markup=ROLE_KEYBOARD)
            return
        
        # Check if user has completed registration
        if user_data.role == "Oqıtıwshı" and not user_data.teacher_name:
            await query.edit_message_text("Iltimas atı jónińizdi jazıń (máselen: Xalmuratov I):")
            return
        elif user_data.role == "Student" and not user_data.group:
            await query.edit_message_text("Toparıńızdı jazıń (máselen: 101, 201, 301, 4G):")
            return
        
        user_data.state = "exam"
        save_user_to_db(user_id, user_data, bot_data.drive_service)
        keyboard = get_exam_keyboard(user_id, user_data.role)
        await query.edit_message_text("Imtixan kesteńizdi kóriw ushın túymeni saylań:", reply_markup=keyboard)
    
    elif callback_data == "back_schedule":
        keyboard = get_schedule_keyboard(user_id, user_data.role)
        await query.edit_message_text("Sabaq kesteńizdi kóriw ushın túymeni saylań:", reply_markup=keyboard)
    
    # Role selection callbacks
    elif callback_data.startswith("role_"):
        role = "Oqıtıwshı" if callback_data == "role_teacher" else "Student"
        user_data.role = role
        save_user_to_db(user_id, user_data, bot_data.drive_service)
        await query.edit_message_text(
            "Iltimas atı jónińizdi jazıń (máselen: Xalmuratov I):" if role == "Oqıtıwshı"
            else "Toparıńızdı jazıń (máselen: 101, 201, 301, 4G):"
        )
    
    # Schedule and exam callbacks
    elif user_data.state == "schedule":
        await handle_schedule_callback(query, context, user_data, bot_data, callback_data)
    
    elif user_data.state == "exam":
        await handle_exam_callback(query, context, user_data, bot_data, callback_data)


def get_schedule_keyboard(user_id: int, role: str):
    """Get appropriate schedule keyboard based on user role and permissions"""
    if user_id in ALLOWED_USERS:
        return TEACHER_SCHEDULE_KEYBOARD_ADMIN
    elif role == "Oqıtıwshı":
        return TEACHER_SCHEDULE_KEYBOARD
    else:
        return STUDENT_SCHEDULE_KEYBOARD


def get_exam_keyboard(user_id: int, role: str):
    """Get appropriate exam keyboard based on user role and permissions"""
    if user_id in ALLOWED_USERS:
        return TEACHER_EXAM_KEYBOARD_ADMIN
    elif role == "Oqıtıwshı":
        return TEACHER_EXAM_KEYBOARD
    else:
        return STUDENT_EXAM_KEYBOARD


async def handle_schedule_callback(query, context, user_data, bot_data, callback_data):
    """Handle schedule-related callback queries"""
    required_columns = ['Kun', 'Jupliq', 'Topar', 'Pan', 'Oqitiwshi', 'Kabinet']
    
    # Get schedule data
    df = get_from_db("changes_schedule", bot_data.drive_service, bot_data)
    if df.empty:
        df = get_from_db("original_schedule", bot_data.drive_service, bot_data)
    
    if df.empty:
        keyboard = get_schedule_keyboard(query.from_user.id, user_data.role)
        await query.edit_message_text("Sabaq kestesi ele júklenbegen! Iltimas, sabır etiń!", reply_markup=keyboard)
        return
    
    # Check required columns
    missing_cols = [c for c in required_columns if c not in df.columns]
    if missing_cols:
        keyboard = get_schedule_keyboard(query.from_user.id, user_data.role)
        await query.edit_message_text(f"Qátelik! Kestede kerekli baǵanalar joq: {', '.join(missing_cols)}", reply_markup=keyboard)
        return
    
    # Normalize data
    df["Oqitiwshi"] = df["Oqitiwshi"].astype(str).str.strip().str.lower()
    df["Topar"] = df["Topar"].astype(str).str.strip()
    
    keyboard = get_schedule_keyboard(query.from_user.id, user_data.role)
    
    # Filter schedule based on user role
    if user_data.role == "Oqıtıwshı":
        if not user_data.teacher_name:
            await query.edit_message_text("Qátelik: Oqıtıwshı atı kiritilmegen. Iltimas, /start arqalı qayta rolıńızdı ornatıń.", reply_markup=MAIN_MENU_KEYBOARD)
            return
        schedule = df[df["Oqitiwshi"] == user_data.teacher_name.lower()]
    else:
        if not user_data.group or user_data.group not in GROUP_UNIONS:
            await query.edit_message_text("Qátelik: Topar kiritilmegen ya da durıs emes. Iltimas, /start arqalı qayta rolıńızdı ornatıń.", reply_markup=MAIN_MENU_KEYBOARD)
            return
        relevant_groups = GROUP_UNIONS[user_data.group]
        schedule = df[df["Topar"].apply(lambda x: any(g in parse_groups(x) for g in relevant_groups))]
    
    # Handle specific schedule callbacks
    if callback_data == "schedule_today":
        current_day = get_current_day()
        day_schedule = schedule[schedule["Kun"] == current_day]
        message = format_schedule(day_schedule, user_data.role)
        await query.edit_message_text(f"Sizde búgin ({current_day}) {message.lower()}.", parse_mode="Markdown", reply_markup=keyboard)
    
    elif callback_data == "schedule_tomorrow":
        tomorrow_day = get_tomorrow_day()
        day_schedule = schedule[schedule["Kun"] == tomorrow_day]
        message = format_schedule(day_schedule, user_data.role)
        await query.edit_message_text(f"Sizde erteń ({tomorrow_day}) {message.lower()}.", parse_mode="Markdown", reply_markup=keyboard)
    
    elif callback_data == "schedule_choose_day":
        await query.edit_message_text("Kúndi tańlań:", reply_markup=DAY_KEYBOARD)
    
    elif callback_data == "schedule_full_week":
        message = format_schedule(schedule, user_data.role)
        await query.edit_message_text(message, parse_mode="Markdown", reply_markup=keyboard)
    
    elif callback_data == "schedule_delete" and query.from_user.id in ALLOWED_USERS:
        await delete_schedule(bot_data, bot_data.drive_service, DRIVE_FOLDER_ID, "schedule", query, context)
    
    elif callback_data.startswith("day_"):
        day_index = int(callback_data.split("_")[1])
        day = DAYS_OF_WEEK[day_index]
        day_schedule = schedule[schedule["Kun"] == day]
        message = format_schedule(day_schedule, user_data.role)
        await query.edit_message_text(f"Sizde {day} kúni {message.lower()}.", parse_mode="Markdown", reply_markup=keyboard)


async def handle_exam_callback(query, context, user_data, bot_data, callback_data):
    """Handle exam-related callback queries"""
    required_columns = ['Kun', 'Waqti', 'Topar', 'Pan', 'Oqitiwshi', 'Kabinet']
    
    # Get exam data
    df = get_from_db("exam_schedule", bot_data.drive_service, bot_data)
    if df.empty:
        keyboard = get_exam_keyboard(query.from_user.id, user_data.role)
        await query.edit_message_text("Imtixan kestesi ele júklenbegen!", reply_markup=keyboard)
        return
    
    # Check required columns
    missing_cols = [c for c in required_columns if c not in df.columns]
    if missing_cols:
        keyboard = get_exam_keyboard(query.from_user.id, user_data.role)
        await query.edit_message_text(f"Qátelik! Kestede kerekli baǵanalar joq: {', '.join(missing_cols)}", reply_markup=keyboard)
        return
    
    # Normalize data
    df["Oqitiwshi"] = df["Oqitiwshi"].astype(str).str.strip().str.lower()
    df["Topar"] = df["Topar"].astype(str).str.strip()
    
    keyboard = get_exam_keyboard(query.from_user.id, user_data.role)
    
    # Filter schedule based on user role
    if user_data.role == "Oqıtıwshı":
        if not user_data.teacher_name:
            await query.edit_message_text("Qátelik: Oqıtıwshı atı kiritilmegen. Iltimas, /start arqalı qayta rolıńızdı ornatıń.", reply_markup=MAIN_MENU_KEYBOARD)
            return
        schedule = df[df["Oqitiwshi"] == user_data.teacher_name.lower()]
    else:
        if not user_data.group or user_data.group not in EXAM_GROUP_UNIONS:
            await query.edit_message_text("Qátelik: Topar kiritilmegen yáki durıs emes. Iltimas, /start arqalı qayta rolıńızdı ornatıń.", reply_markup=MAIN_MENU_KEYBOARD)
            return
        relevant_groups = EXAM_GROUP_UNIONS.get(user_data.group, [user_data.group])
        schedule = df[df["Topar"].apply(lambda x: any(g in parse_groups(x) for g in relevant_groups))]
    
    # Handle specific exam callbacks
    if callback_data == "exam_today":
        current_date = get_current_date()
        day_schedule = schedule[schedule["Kun"] == current_date]
        message = format_exam_schedule(day_schedule, user_data.role)
        await query.edit_message_text(f"Sizde búgin ({current_date}) {message.lower()}.", parse_mode="Markdown", reply_markup=keyboard)
    
    elif callback_data == "exam_tomorrow":
        tomorrow_date = get_tomorrow_date()
        day_schedule = schedule[schedule["Kun"] == tomorrow_date]
        message = format_exam_schedule(day_schedule, user_data.role)
        await query.edit_message_text(f"Sizde erteń ({tomorrow_date}) {message.lower()}.", parse_mode="Markdown", reply_markup=keyboard)
    
    elif callback_data == "exam_current_week":
        week_dates = get_current_week_dates()
        week_schedule = schedule[schedule["Kun"].isin(week_dates)]
        message = format_exam_schedule(week_schedule, user_data.role)
        await query.edit_message_text(f"Sizde bul háptede {message.lower()}.", parse_mode="Markdown", reply_markup=keyboard)
    
    elif callback_data == "exam_full":
        message = format_exam_schedule(schedule, user_data.role)
        await query.edit_message_text(message, parse_mode="Markdown", reply_markup=keyboard)
    
    elif callback_data == "exam_delete" and query.from_user.id in ALLOWED_USERS:
        await delete_schedule(bot_data, bot_data.drive_service, DRIVE_FOLDER_ID, "exam", query, context)


async def delete_schedule(bot_data: BotData, drive_service, folder_id: str, schedule_type: str, query, context):
    """Delete schedule from database and drive"""
    if clear_db(drive_service, folder_id, schedule_type):
        if schedule_type == "schedule":
            bot_data.original_schedule_file = None
            bot_data.last_schedule_file = None
            bot_data.schedule_cache = None
            message = "Sabaq kestesi sátli óshirildi, Google Drive da tolıq tazalandı!"
        else:
            bot_data.exam_file = None
            bot_data.exam_cache = None
            message = "Imtixan kestesi sátli óshirildi, Google Drive da tolıq tazalandı!"
        
        await query.edit_message_text(message)
        await query.message.reply_text("Bas betke qaytıldı. Túymelerden birin saylań:", reply_markup=MAIN_MENU_KEYBOARD)
        return True
    else:
        await query.edit_message_text(f"Qátelik: {schedule_type.capitalize()} keste óshirilmedi!")
        return False

