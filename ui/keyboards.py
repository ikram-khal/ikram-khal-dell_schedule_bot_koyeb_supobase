"""
Keyboard definitions for the Combined Telegram Bot
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


# Role selection keyboard
ROLE_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("Oqıtıwshı", callback_data="role_teacher"),
     InlineKeyboardButton("Student", callback_data="role_student")]
])

# Main menu keyboard - Combined functionality
MAIN_MENU_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("📚 Sabaq kestesi", callback_data="main_schedule")],
    [InlineKeyboardButton("📝 Imtixan kestesi", callback_data="main_exam")],
    [InlineKeyboardButton("✅ Ámeliyat qatnası", callback_data="attendance_menu")]
])

# Attendance menu keyboard
ATTENDANCE_MENU_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("Oqıtıwshı", callback_data="teacher"),
     InlineKeyboardButton("Student", callback_data="student")],
    [InlineKeyboardButton("Artqa qaytıw", callback_data="back_main")]
])

# Teacher schedule keyboards
TEACHER_SCHEDULE_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("Búgin", callback_data="schedule_today"),
     InlineKeyboardButton("Erteń", callback_data="schedule_tomorrow")],
    [InlineKeyboardButton("Kúndi tánlaw", callback_data="schedule_choose_day"),
     InlineKeyboardButton("Tolıq hápteni kóriw", callback_data="schedule_full_week")],
    [InlineKeyboardButton("Artqa qaytıw", callback_data="back_main")]
])

TEACHER_SCHEDULE_KEYBOARD_ADMIN = InlineKeyboardMarkup([
    [InlineKeyboardButton("Búgin", callback_data="schedule_today"),
     InlineKeyboardButton("Erteń", callback_data="schedule_tomorrow")],
    [InlineKeyboardButton("Kúndi tánlaw", callback_data="schedule_choose_day"),
     InlineKeyboardButton("Tolıq hápteni kóriw", callback_data="schedule_full_week")],
    [InlineKeyboardButton("Kesteni óshiriw", callback_data="schedule_delete"),
     InlineKeyboardButton("Artqa qaytıw", callback_data="back_main")]
])

# Student schedule keyboard
STUDENT_SCHEDULE_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("Búgin", callback_data="schedule_today"),
     InlineKeyboardButton("Erteń", callback_data="schedule_tomorrow")],
    [InlineKeyboardButton("Kúndi tánlaw", callback_data="schedule_choose_day"),
     InlineKeyboardButton("Tolıq hápteni kóriw", callback_data="schedule_full_week")],
    [InlineKeyboardButton("Artqa qaytıw", callback_data="back_main")]
])

# Teacher exam keyboards
TEACHER_EXAM_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("Búgin", callback_data="exam_today"),
     InlineKeyboardButton("Erteń", callback_data="exam_tomorrow")],
    [InlineKeyboardButton("Usı hápte", callback_data="exam_current_week"),
     InlineKeyboardButton("Tolıq keste", callback_data="exam_full")],
    [InlineKeyboardButton("Artqa qaytıw", callback_data="back_main")]
])

TEACHER_EXAM_KEYBOARD_ADMIN = InlineKeyboardMarkup([
    [InlineKeyboardButton("Búgin", callback_data="exam_today"),
     InlineKeyboardButton("Erteń", callback_data="exam_tomorrow")],
    [InlineKeyboardButton("Usı hápte", callback_data="exam_current_week"),
     InlineKeyboardButton("Tolıq keste", callback_data="exam_full")],
    [InlineKeyboardButton("Kesteni óshiriw", callback_data="exam_delete"),
     InlineKeyboardButton("Artqa qaytıw", callback_data="back_main")]
])

# Student exam keyboard
STUDENT_EXAM_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("Búgin", callback_data="exam_today"),
     InlineKeyboardButton("Erteń", callback_data="exam_tomorrow")],
    [InlineKeyboardButton("Usı hápte", callback_data="exam_current_week"),
     InlineKeyboardButton("Tolıq keste", callback_data="exam_full")],
    [InlineKeyboardButton("Artqa qaytıw", callback_data="back_main")]
])

# Day selection keyboard
DAY_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("DUYSEMBI", callback_data="day_0"),
     InlineKeyboardButton("SIYSHEMBI", callback_data="day_1")],
    [InlineKeyboardButton("SARSHEMBI", callback_data="day_2"),
     InlineKeyboardButton("PIYSHEMBI", callback_data="day_3")],
    [InlineKeyboardButton("JUMA", callback_data="day_4"),
     InlineKeyboardButton("SHEMBI", callback_data="day_5")],
    [InlineKeyboardButton("Artqa qaytıw", callback_data="back_schedule")]
])

# Attendance action keyboard
ATTENDANCE_ACTION_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("Keldim", callback_data="came"),
     InlineKeyboardButton("Kettim", callback_data="left")],
    [InlineKeyboardButton("Artqa qaytıw", callback_data="back_main")]
])

# Teacher attendance menu keyboard
TEACHER_ATTENDANCE_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("Qatnastı tekseriw", callback_data="check_attendance")],
    [InlineKeyboardButton("Mektep koordinatların jańalaw", callback_data="update_coordinates")],
    [InlineKeyboardButton("Artqa qaytıw", callback_data="back_main")]
])
