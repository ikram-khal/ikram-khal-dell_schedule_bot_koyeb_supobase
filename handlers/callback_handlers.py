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
    EXAM_GROUP_UNIONS, DAYS_OF_WEEK, COURSE_GROUPS, SCHEDULE_STUDENT_GROUPS,
)
from models.data_models import BotData
from database.db_operations import save_user_to_db, get_from_db, clear_db
from ui.keyboards import (
    MAIN_MENU_KEYBOARD, TEACHER_SCHEDULE_KEYBOARD, TEACHER_SCHEDULE_KEYBOARD_ADMIN,
    STUDENT_SCHEDULE_KEYBOARD, TEACHER_EXAM_KEYBOARD, TEACHER_EXAM_KEYBOARD_ADMIN,
    STUDENT_EXAM_KEYBOARD, DAY_KEYBOARD,
)
from utils.helpers import (
    parse_groups, get_current_day, get_tomorrow_day, get_current_date,
    get_tomorrow_date, get_current_week_dates, format_schedule, format_exam_schedule,
)

logger = logging.getLogger(__name__)


class CallbackHandlers:
    def __init__(self, db_handler, attendance_service, conversation_handlers):
        self.db_handler = db_handler
        self.attendance_service = attendance_service
        self.conversation_handlers = conversation_handlers

    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        user_id = query.from_user.id
        bot_data: BotData = context.bot_data.get('bot_data')

        # Schedule bot callbacks
        if (data in ["main_schedule", "main_exam", "back_main", "back_schedule"]
                or data.startswith("role_") or data.startswith("schedule_")
                or data.startswith("exam_") or data.startswith("day_")
                or data.startswith("sch_c_") or data.startswith("sch_g_") or data.startswith("sch_s_")):
            return await button_handler(update, context)

        # Attendance menu
        elif data == "attendance_menu":
            uid_str = str(query.from_user.id)
            teachers = self.db_handler.get_teachers()
            teacher = next((t for t in teachers if str(t.get("user_id", "")).strip() == uid_str), None)
            if teacher:
                context.user_data["role"] = "teacher"
                from ui.keyboards import TEACHER_ATTENDANCE_KEYBOARD
                await query.edit_message_text(
                    f"Sálem, {teacher.get('name', 'Oqıtıwshı')}! Tómendegilerden birin saylań:",
                    reply_markup=TEACHER_ATTENDANCE_KEYBOARD,
                )
                return

            students = self.db_handler.get_students()
            student = next((s for s in students if str(s.get("user_id", "")).strip() == uid_str), None)
            if student:
                context.user_data.update({
                    "role": "student",
                    "student_id": student.get("student_id", ""),
                    "group": student.get("group", ""),
                    "school": student.get("school", ""),
                    "name": student.get("name", "Unknown"),
                })
                from ui.keyboards import ATTENDANCE_ACTION_KEYBOARD
                await query.edit_message_text(
                    f"Sálem, {student.get('name', 'Student')}! Qatnastı belgilew ushın túymeni saylań:",
                    reply_markup=ATTENDANCE_ACTION_KEYBOARD,
                )
                return

            from ui.keyboards import ATTENDANCE_MENU_KEYBOARD
            await query.edit_message_text(
                "Qatnastı belgilew ushın rolıńızdı saylań:",
                reply_markup=ATTENDANCE_MENU_KEYBOARD,
            )

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

    async def check_attendance_callback(self, query, context):
        user_id = str(query.from_user.id)
        teachers = self.db_handler.get_teachers()
        teacher = next((t for t in teachers if str(t.get("user_id", "")).strip() == user_id), None)

        if not teacher:
            from ui.keyboards import ATTENDANCE_MENU_KEYBOARD
            await query.edit_message_text(
                "Siz oqıtıwshı sıpatında dizimnen ótpegensiz.",
                reply_markup=ATTENDANCE_MENU_KEYBOARD,
            )
            return ConversationHandler.END

        teacher_group = teacher.get("group", "")
        if not teacher_group:
            from ui.keyboards import TEACHER_ATTENDANCE_KEYBOARD
            await query.edit_message_text(
                "Qátelik: sizde topar kórsetilmegen.",
                reply_markup=TEACHER_ATTENDANCE_KEYBOARD,
            )
            return ConversationHandler.END

        report = self.attendance_service.get_attendance_report(teacher_group)
        from ui.keyboards import TEACHER_ATTENDANCE_KEYBOARD
        await query.edit_message_text(report, reply_markup=TEACHER_ATTENDANCE_KEYBOARD)
        return ConversationHandler.END

    async def update_school_coordinates_callback(self, query, context):
        user_id = str(query.from_user.id)
        teachers = self.db_handler.get_teachers()
        teacher = next((t for t in teachers if str(t.get("user_id", "")).strip() == user_id), None)

        if not teacher:
            keyboard = [[InlineKeyboardButton("Oqıtıwshı", callback_data="teacher")]]
            await query.edit_message_text(
                "Siz oqıtıwshı sıpatında dizimnen ótpegensiz.",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return ConversationHandler.END

        context.user_data["role"] = "teacher"
        context.user_data["school"] = teacher.get("school", "")
        await query.edit_message_text("Mekteptiń jańa geolokaciyasın real waqıtta jiberiń.")
        return TEACHER_LOCATION

    async def handle_attendance_action_callback(self, query, context, action_text: str):
        user_id = str(query.from_user.id).strip()
        students = self.db_handler.get_students()

        if not students:
            keyboard = [[InlineKeyboardButton("Student", callback_data="student")]]
            await query.edit_message_text(
                "Qátelik: Studentler dizimi tabılmadı.",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return ConversationHandler.END

        student = next((s for s in students if str(s.get("user_id", "")).strip() == user_id), None)
        if not student:
            keyboard = [[InlineKeyboardButton("Student", callback_data="student")]]
            await query.edit_message_text(
                "Siz student sıpatında dizimnen ótpegensiz.",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return ConversationHandler.END

        context.user_data.update({
            "attendance_action": action_text,
            "student_id": student.get("student_id", ""),
            "group": student.get("group", ""),
            "school": student.get("school", ""),
            "name": student.get("name", "Unknown"),
            "action_timestamp": datetime.now(TIMEZONE),
        })

        keyboard = [
            [InlineKeyboardButton("Keldim", callback_data="came")],
            [InlineKeyboardButton("Kettim", callback_data="left")],
            [InlineKeyboardButton("Artqa qaytıw", callback_data="back_main")],
        ]
        await query.edit_message_text(
            "Geolokaciyańızdı real waqıtta jiberiń!!!",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return STUDENT_LOCATION

    async def teacher_course_callback(self, query, context, course: str):
        if course not in COURSE_GROUPS:
            keyboard = [[InlineKeyboardButton(c, callback_data=f"course_{c}")] for c in COURSE_GROUPS]
            await query.edit_message_text(
                f"Dizimnen kursıńızdı tańlań:", reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return TEACHER_COURSE
        context.user_data["course"] = course
        keyboard = [[InlineKeyboardButton(g, callback_data=f"group_{g}")] for g in COURSE_GROUPS[course]]
        await query.edit_message_text(
            f"{course} toparlaran óz toparıńızdı saylań:", reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return TEACHER_GROUP

    async def teacher_group_callback(self, query, context, group: str):
        course_groups = COURSE_GROUPS.get(context.user_data.get("course", ""), GROUPS)
        if group not in course_groups:
            keyboard = [[InlineKeyboardButton(g, callback_data=f"group_{g}")] for g in course_groups]
            await query.edit_message_text("Dizimnen topardı saylań:", reply_markup=InlineKeyboardMarkup(keyboard))
            return TEACHER_GROUP
        context.user_data["group"] = group
        keyboard = [[InlineKeyboardButton(s, callback_data=f"school_{s}")] for s in SCHOOLS]
        await query.edit_message_text("Mektepti saylań:", reply_markup=InlineKeyboardMarkup(keyboard))
        return TEACHER_SCHOOL

    async def teacher_school_callback(self, query, context, school: str):
        if school not in SCHOOLS:
            keyboard = [[InlineKeyboardButton(s, callback_data=f"school_{s}")] for s in SCHOOLS]
            await query.edit_message_text("Dizimnen mektepti saylań:", reply_markup=InlineKeyboardMarkup(keyboard))
            return TEACHER_SCHOOL
        context.user_data["school"] = school
        success = self.db_handler.add_teacher(
            context.user_data["user_id"],
            context.user_data["name"],
            context.user_data["group"],
            school,
        )
        if success:
            await query.edit_message_text("Mektep geolokaciyasın real waqıtta jiberiń.")
            return TEACHER_LOCATION
        await query.edit_message_text("Oqıtıwshı dizimge qosıwda qátelik.")
        return ConversationHandler.END

    async def student_course_callback(self, query, context, course: str):
        if course not in COURSE_GROUPS:
            keyboard = [[InlineKeyboardButton(c, callback_data=f"course_{c}")] for c in COURSE_GROUPS]
            await query.edit_message_text("Dizimnen kursıńızdı saylań:", reply_markup=InlineKeyboardMarkup(keyboard))
            return STUDENT_COURSE
        context.user_data["course"] = course
        keyboard = [[InlineKeyboardButton(g, callback_data=f"group_{g}")] for g in COURSE_GROUPS[course]]
        await query.edit_message_text(
            f"{course} toparlarınan óz toparıńızdı saylań:", reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return STUDENT_GROUP

    async def student_group_callback(self, query, context, group: str):
        course_groups = COURSE_GROUPS.get(context.user_data.get("course", ""), GROUPS)
        if group not in course_groups:
            keyboard = [[InlineKeyboardButton(g, callback_data=f"group_{g}")] for g in course_groups]
            await query.edit_message_text("Dizimnen toparıńızdı saylań:", reply_markup=InlineKeyboardMarkup(keyboard))
            return STUDENT_GROUP
        context.user_data["group"] = group
        keyboard = [[InlineKeyboardButton(s, callback_data=f"school_{s}")] for s in SCHOOLS]
        await query.edit_message_text("Mektepti saylań:", reply_markup=InlineKeyboardMarkup(keyboard))
        return STUDENT_SCHOOL

    async def student_school_callback(self, query, context, school: str):
        if school not in SCHOOLS:
            keyboard = [[InlineKeyboardButton(s, callback_data=f"school_{s}")] for s in SCHOOLS]
            await query.edit_message_text("Dizimnen mektebińizdi saylań:", reply_markup=InlineKeyboardMarkup(keyboard))
            return STUDENT_SCHOOL
        context.user_data["school"] = school
        success = self.db_handler.add_student(
            context.user_data["user_id"],
            context.user_data["name"],
            context.user_data["student_id"],
            context.user_data["group"],
            school,
        )
        if success:
            context.user_data["student"] = {
                "student_id": context.user_data["student_id"],
                "group": context.user_data["group"],
                "school": school,
            }
            keyboard = [
                [InlineKeyboardButton("Keldim", callback_data="came")],
                [InlineKeyboardButton("Kettim", callback_data="left")],
                [InlineKeyboardButton("Artqa qaytıw", callback_data="back_main")],
            ]
            await query.edit_message_text(
                "Dizimnen ótiw sátli! 'Keldim' yamasa 'Kettim' túymesin basıń.",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            await query.edit_message_text("Student dizimge qosıwda qátelik.")
        return ConversationHandler.END


# ---- Schedule bot callback functions ----

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    bot_data: BotData = context.bot_data.get('bot_data')
    callback_data = query.data

    if callback_data == "back_main":
        await query.edit_message_text("Bas betke qaytıldı:", reply_markup=MAIN_MENU_KEYBOARD)
        return

    if not bot_data or user_id not in bot_data.users:
        await query.edit_message_text("Iltimas, /start buyrıǵın baslań!")
        return

    user_data = bot_data.users[user_id]

    if callback_data == "main_schedule":
        if not user_data.role:
            from ui.keyboards import ROLE_KEYBOARD
            await query.edit_message_text("Sabaq kesteńizdi kóriw ushın rolıńızdı saylań:", reply_markup=ROLE_KEYBOARD)
            return
        if user_data.role == "Oqıtıwshı" and not user_data.teacher_name:
            await query.edit_message_text("Iltimas atı jónińizdi jazıń (máselen: Xalmuratov I):")
            return
        if user_data.role == "Student" and not user_data.group:
            await query.edit_message_text("Toparıńızdı jazıń (máselen: 101, 201, 301):")
            return
        user_data.state = "schedule"
        save_user_to_db(user_id, user_data)
        keyboard = _get_schedule_keyboard(user_id, user_data.role)
        await query.edit_message_text("Sabaq kesteńizdi kóriw ushın túymeni saylań:", reply_markup=keyboard)

    elif callback_data == "main_exam":
        if not user_data.role:
            from ui.keyboards import ROLE_KEYBOARD
            await query.edit_message_text("Imtixan kesteńizdi kóriw ushın rolıńızdı saylań:", reply_markup=ROLE_KEYBOARD)
            return
        if user_data.role == "Oqıtıwshı" and not user_data.teacher_name:
            await query.edit_message_text("Iltimas atı jónińizdi jazıń:")
            return
        if user_data.role == "Student" and not user_data.group:
            await query.edit_message_text("Toparıńızdı jazıń:")
            return
        user_data.state = "exam"
        save_user_to_db(user_id, user_data)
        keyboard = _get_exam_keyboard(user_id, user_data.role)
        await query.edit_message_text("Imtixan kesteńizdi kóriw ushın túymeni saylań:", reply_markup=keyboard)

    elif callback_data == "back_schedule":
        keyboard = _get_schedule_keyboard(user_id, user_data.role)
        await query.edit_message_text("Sabaq kesteńizdi kóriw ushın túymeni saylań:", reply_markup=keyboard)

    elif callback_data.startswith("role_"):
        role = "Oqıtıwshı" if callback_data == "role_teacher" else "Student"
        user_data.role = role
        save_user_to_db(user_id, user_data)
        if role == "Oqıtıwshı":
            await query.edit_message_text("Iltimas atı jónińizdi jazıń (máselen: Xalmuratov I):")
        else:
            # 3-step group selection: show course buttons
            keyboard = [
                [InlineKeyboardButton("1-kurs", callback_data="sch_c_1")],
                [InlineKeyboardButton("2-kurs", callback_data="sch_c_2")],
                [InlineKeyboardButton("3-kurs", callback_data="sch_c_3")],
                [InlineKeyboardButton("4-kurs", callback_data="sch_c_4")],
            ]
            await query.edit_message_text("Kursıńızdı tańlań:", reply_markup=InlineKeyboardMarkup(keyboard))

    # Step 1: course selected → show letter groups
    elif callback_data.startswith("sch_c_"):
        course_num = callback_data[6:]  # "1", "2", "3", "4"
        groups = list(SCHEDULE_STUDENT_GROUPS.get(course_num, {}).keys())
        keyboard = [[InlineKeyboardButton(g, callback_data=f"sch_g_{g}")] for g in groups]
        await query.edit_message_text(f"{course_num}-kurs: toparıńızdı tańlań:",
                                       reply_markup=InlineKeyboardMarkup(keyboard))

    # Step 2: letter group selected → show subgroups (or store directly for 4-kurs)
    elif callback_data.startswith("sch_g_"):
        letter_group = callback_data[6:]  # "1G", "2D", etc.
        # Find subgroups for this letter group
        subgroups = None
        for course_data in SCHEDULE_STUDENT_GROUPS.values():
            if letter_group in course_data:
                subgroups = course_data[letter_group]
                break

        if subgroups is None:
            await query.edit_message_text("Qátelik. /start arqalı qaytadan urınıp kóriń.")
            return

        if not subgroups:
            # 4-kurs: no subgroups, store letter group directly
            user_data.group = letter_group
            save_user_to_db(user_id, user_data)
            keyboard = _get_schedule_keyboard(user_id, user_data.role)
            await query.edit_message_text(
                f"Siz {letter_group} toparı sıpatında dizimnen óttińiz. Kesteni kóriw ushın túymeni saylań:",
                reply_markup=keyboard,
            )
        else:
            keyboard = [[InlineKeyboardButton(s, callback_data=f"sch_s_{s}")] for s in subgroups]
            await query.edit_message_text(f"{letter_group}: podgrupańızdı tańlań:",
                                           reply_markup=InlineKeyboardMarkup(keyboard))

    # Step 3: subgroup selected → store and show schedule menu
    elif callback_data.startswith("sch_s_"):
        subgroup = callback_data[6:]  # "101", "102", etc.
        if subgroup not in GROUP_UNIONS:
            await query.edit_message_text("Qátelik: topar tabılmadı. /start arqalı qaytadan urınıp kóriń.")
            return
        user_data.group = subgroup
        save_user_to_db(user_id, user_data)
        keyboard = _get_schedule_keyboard(user_id, user_data.role)
        await query.edit_message_text(
            f"Siz {subgroup} toparı sıpatında dizimnen óttińiz. Kesteni kóriw ushın túymeni saylań:",
            reply_markup=keyboard,
        )

    elif user_data.state == "schedule":
        await _handle_schedule_callback(query, context, user_data, bot_data, callback_data)

    elif user_data.state == "exam":
        await _handle_exam_callback(query, context, user_data, bot_data, callback_data)


def _get_schedule_keyboard(user_id: int, role: str):
    if user_id in ALLOWED_USERS:
        return TEACHER_SCHEDULE_KEYBOARD_ADMIN
    if role == "Oqıtıwshı":
        return TEACHER_SCHEDULE_KEYBOARD
    return STUDENT_SCHEDULE_KEYBOARD


def _get_exam_keyboard(user_id: int, role: str):
    if user_id in ALLOWED_USERS:
        return TEACHER_EXAM_KEYBOARD_ADMIN
    if role == "Oqıtıwshı":
        return TEACHER_EXAM_KEYBOARD
    return STUDENT_EXAM_KEYBOARD


async def _handle_schedule_callback(query, context, user_data, bot_data, callback_data):
    required = ['Kun', 'Jupliq', 'Topar', 'Pan', 'Oqitiwshi', 'Kabinet']

    df = get_from_db("changes_schedule", bot_data)
    if df.empty:
        df = get_from_db("original_schedule", bot_data)

    if df.empty:
        keyboard = _get_schedule_keyboard(query.from_user.id, user_data.role)
        await query.edit_message_text("Sabaq kestesi ele júklenbegen!", reply_markup=keyboard)
        return

    missing = [c for c in required if c not in df.columns]
    if missing:
        keyboard = _get_schedule_keyboard(query.from_user.id, user_data.role)
        await query.edit_message_text(f"Kestede kerekli baǵanalar joq: {', '.join(missing)}", reply_markup=keyboard)
        return

    df["Oqitiwshi"] = df["Oqitiwshi"].astype(str).str.strip().str.lower()
    df["Topar"] = df["Topar"].astype(str).str.strip()
    keyboard = _get_schedule_keyboard(query.from_user.id, user_data.role)

    if user_data.role == "Oqıtıwshı":
        if not user_data.teacher_name:
            await query.edit_message_text("Qátelik: Oqıtıwshı atı kiritilmegen.", reply_markup=MAIN_MENU_KEYBOARD)
            return
        schedule = df[df["Oqitiwshi"] == user_data.teacher_name.lower()]
    else:
        if not user_data.group or user_data.group not in GROUP_UNIONS:
            await query.edit_message_text("Qátelik: Topar kiritilmegen.", reply_markup=MAIN_MENU_KEYBOARD)
            return
        relevant = GROUP_UNIONS[user_data.group]
        schedule = df[df["Topar"].apply(lambda x: any(g in parse_groups(x) for g in relevant))]

    if callback_data == "schedule_today":
        day = get_current_day()
        msg = format_schedule(schedule[schedule["Kun"] == day], user_data.role)
        await query.edit_message_text(f"Sizde búgin ({day}) {msg.lower()}.", parse_mode="Markdown", reply_markup=keyboard)

    elif callback_data == "schedule_tomorrow":
        day = get_tomorrow_day()
        msg = format_schedule(schedule[schedule["Kun"] == day], user_data.role)
        await query.edit_message_text(f"Sizde erteń ({day}) {msg.lower()}.", parse_mode="Markdown", reply_markup=keyboard)

    elif callback_data == "schedule_choose_day":
        await query.edit_message_text("Kúndi tańlań:", reply_markup=DAY_KEYBOARD)

    elif callback_data == "schedule_full_week":
        msg = format_schedule(schedule, user_data.role)
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=keyboard)

    elif callback_data == "schedule_delete" and query.from_user.id in ALLOWED_USERS:
        await _delete_schedule(bot_data, "schedule", query)

    elif callback_data.startswith("day_"):
        day_index = int(callback_data.split("_")[1])
        day = DAYS_OF_WEEK[day_index]
        msg = format_schedule(schedule[schedule["Kun"] == day], user_data.role)
        await query.edit_message_text(f"Sizde {day} kúni {msg.lower()}.", parse_mode="Markdown", reply_markup=keyboard)


async def _handle_exam_callback(query, context, user_data, bot_data, callback_data):
    required = ['Kun', 'Waqti', 'Topar', 'Pan', 'Oqitiwshi', 'Kabinet']

    df = get_from_db("exam_schedule", bot_data)
    if df.empty:
        keyboard = _get_exam_keyboard(query.from_user.id, user_data.role)
        await query.edit_message_text("Imtixan kestesi ele júklenbegen!", reply_markup=keyboard)
        return

    missing = [c for c in required if c not in df.columns]
    if missing:
        keyboard = _get_exam_keyboard(query.from_user.id, user_data.role)
        await query.edit_message_text(f"Kestede kerekli baǵanalar joq: {', '.join(missing)}", reply_markup=keyboard)
        return

    df["Oqitiwshi"] = df["Oqitiwshi"].astype(str).str.strip().str.lower()
    df["Topar"] = df["Topar"].astype(str).str.strip()
    keyboard = _get_exam_keyboard(query.from_user.id, user_data.role)

    if user_data.role == "Oqıtıwshı":
        if not user_data.teacher_name:
            await query.edit_message_text("Qátelik: Oqıtıwshı atı kiritilmegen.", reply_markup=MAIN_MENU_KEYBOARD)
            return
        schedule = df[df["Oqitiwshi"] == user_data.teacher_name.lower()]
    else:
        if not user_data.group or user_data.group not in EXAM_GROUP_UNIONS:
            await query.edit_message_text("Qátelik: Topar kiritilmegen.", reply_markup=MAIN_MENU_KEYBOARD)
            return
        relevant = EXAM_GROUP_UNIONS.get(user_data.group, [user_data.group])
        schedule = df[df["Topar"].apply(lambda x: any(g in parse_groups(x) for g in relevant))]

    if callback_data == "exam_today":
        date = get_current_date()
        msg = format_exam_schedule(schedule[schedule["Kun"] == date], user_data.role)
        await query.edit_message_text(f"Sizde búgin ({date}) {msg.lower()}.", parse_mode="Markdown", reply_markup=keyboard)

    elif callback_data == "exam_tomorrow":
        date = get_tomorrow_date()
        msg = format_exam_schedule(schedule[schedule["Kun"] == date], user_data.role)
        await query.edit_message_text(f"Sizde erteń ({date}) {msg.lower()}.", parse_mode="Markdown", reply_markup=keyboard)

    elif callback_data == "exam_current_week":
        dates = get_current_week_dates()
        msg = format_exam_schedule(schedule[schedule["Kun"].isin(dates)], user_data.role)
        await query.edit_message_text(f"Sizde bul háptede {msg.lower()}.", parse_mode="Markdown", reply_markup=keyboard)

    elif callback_data == "exam_full":
        msg = format_exam_schedule(schedule, user_data.role)
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=keyboard)

    elif callback_data == "exam_delete" and query.from_user.id in ALLOWED_USERS:
        await _delete_schedule(bot_data, "exam", query)


async def _delete_schedule(bot_data: BotData, schedule_type: str, query):
    if clear_db(schedule_type):
        if schedule_type == "schedule":
            bot_data.schedule_cache = None
            msg = "Sabaq kestesi sátli óshirildi!"
        else:
            bot_data.exam_cache = None
            msg = "Imtixan kestesi sátli óshirildi!"
        await query.edit_message_text(msg)
        await query.message.reply_text("Bas betke qaytıldı:", reply_markup=MAIN_MENU_KEYBOARD)
    else:
        await query.edit_message_text(f"Qátelik: keste óshirilmedi!")
