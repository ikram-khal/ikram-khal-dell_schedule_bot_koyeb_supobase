"""
Configuration settings for the Combined Bot (Attendance + Schedule)
"""
import os
import pytz

# Bot Configuration
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7385854628:AAGpv4SD7Qcb-T-kg9ticIx19WIc604bw5o")
ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID", "343553810")
ALLOWED_USERS = {343553810}

# Supabase Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://jxglccfbjxwbqffaxwkk.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp4Z2xjY2Zianh3YnFmZmF4d2trIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NDQ0MDg2MCwiZXhwIjoyMDkwMDE2ODYwfQ.Yu_vroA1cMvk2CzIdUvYHiYC4kT76sxKLU2xss5kryA")

# Application Constants (Attendance)
ALLOWED_RADIUS = 0.1  # 100 meters in kilometers
TIMEZONE = pytz.timezone("Asia/Tashkent")
MIN_ATTENDANCE_HOURS = 3
MIN_LIVE_PERIOD = 60

# Schedule Configuration
PAIR_TIMES = {
    1: "8:30-9:50", 2: "10:00-11:20", 3: "11:30-12:50",
    4: "13:00-14:20", 5: "14:30-15:50", 6: "16:00-17:20"
}

DAYS_OF_WEEK = ["DUYSEMBI", "SIYSHEMBI", "SARSHEMBI", "PIYSHEMBI", "JUMA", "SHEMBI"]

# Conversation States
TEACHER_NAME, TEACHER_COURSE, TEACHER_GROUP, TEACHER_SCHOOL, TEACHER_LOCATION, \
STUDENT_NAME, STUDENT_COURSE, STUDENT_GROUP, STUDENT_SCHOOL, STUDENT_LOCATION = range(10)

# Predefined Options (Attendance)
GROUPS = ["1G", "1D", "1E", "1J", "1Z", "2G", "2D", "2E", "2J", "2Z", "2I", "2K", "2L",
          "3G", "3D", "3E", "3J", "3Z", "3I", "4G", "4D", "4E"]
SCHOOLS = ["4-mektep", "7-mektep", "11-mektep", "12-mektep", "24-mektep",
           "31-mektep", "42-mektep", "Al-Xorezmiy QMI"]

# Course-based group organization for attendance
COURSE_GROUPS = {
    "1-kurs": ["1G", "1D", "1E", "1J", "1I"],
    "2-kurs": ["2G", "2D", "2E", "2J", "2Z", "2I", "2K", "2L"],
    "3-kurs": ["3G", "3D", "3E", "3J", "3Z", "3I"],
    "4-kurs": ["4G", "4D", "4E"],
}

# 3-step group selection for schedule bot student registration
# course_num → letter_group → [subgroups]  (empty list = no subgroup, store letter_group directly)
SCHEDULE_STUDENT_GROUPS = {
    "1": {
        "1G": ["101", "102"],
        "1D": ["103", "104"],
        "1E": ["105", "106"],
        "1J": ["107", "108"],
        "1Z": ["109", "110"],
        "1I": ["111"],
    },
    "2": {
        "2G": ["201", "202"],
        "2D": ["203", "204"],
        "2E": ["205", "206"],
        "2J": ["207", "208"],
        "2Z": ["209", "210"],
        "2I": ["211"],
        "2K": ["212"],
        "2L": ["213"],
    },
    "3": {
        "3G": ["301", "302"],
        "3D": ["303", "304"],
        "3E": ["305", "306"],
        "3J": ["307", "308"],
        "3Z": ["309"],
        "3I": ["310"],
    },
    "4": {
        "4G": [],  # no subgroups
        "4D": [],
        "4E": [],
    },
}

# Group unions for schedule
GROUP_UNIONS = {
    "101": ["101"], "102": ["102"], "103": ["103"], "104": ["104"], "105": ["105"],
    "106": ["106"], "107": ["107"], "108": ["108"], "109": ["109"], "110": ["110"], "111": ["111"],
    "201": ["201"], "202": ["202"], "203": ["203"], "204": ["204"], "205": ["205"],
    "206": ["206"], "207": ["207"], "208": ["208"], "209": ["209"], "210": ["210"],
    "211": ["211"], "212": ["212"], "213": ["213"],
    "301": ["301"], "302": ["302"], "303": ["303"], "304": ["304"], "305": ["305"],
    "306": ["306"], "307": ["307"], "308": ["308"], "309": ["309"], "310": ["310"],
    "4G": ["4G"], "4D": ["4D"], "4E": ["4E"],
    "101-102": ["101", "102"],
    "103-104": ["103", "104"], "105-106": ["105", "106"], "107-108": ["107", "108"],
    "201-202": ["201", "202"], "203-204": ["203", "204"], "205-206": ["205", "206"],
    "207-208": ["207", "208"], "209-210": ["209", "210"],
    "301-302": ["301", "302"], "303-304": ["303", "304"], "305-306": ["305", "306"],
    "307-308": ["307", "308"],
    "103-104-105-106-107-108": ["103", "104", "105", "106", "107", "108"],
    "201-202-203-204-205-206-212": ["201", "202", "203", "204", "205", "206", "212"],
    "207-208-209-210": ["207", "208", "209", "210"],
    "301-302-303-304-305-306": ["301", "302", "303", "304", "305", "306"],
    "307-308-309": ["307", "308", "309"],
}

# Group unions for exams
EXAM_GROUP_UNIONS = {
    "101": ["1 G"], "102": ["1 G"], "103": ["1 D"], "104": ["1 D"], "105": ["1 E"],
    "106": ["1 E"], "107": ["1 J"], "108": ["1 J"], "109": ["1 Z"], "110": ["1 Z"], "111": ["1 I"],
    "201": ["2 G"], "202": ["2 G"], "203": ["2 D"], "204": ["2 D"], "205": ["2 E"],
    "206": ["2 E"], "207": ["2 J"], "208": ["2 J"], "209": ["2 Z"], "210": ["2 Z"],
    "211": ["2 I"], "212": ["2 K"], "213": ["2 L"],
    "301": ["3 G"], "302": ["3 G"], "303": ["3 D"], "304": ["3 D"], "305": ["3 E"],
    "306": ["3 E"], "307": ["3 J"], "308": ["3 J"], "309": ["3 Z"], "310": ["3 I"],
    "101-102": ["1 G"],
    "103-104": ["1 D"], "105-106": ["1 E"], "107-108": ["1 J"],
    "201-202": ["2 G"], "203-204": ["2 D"], "205-206": ["2 E"],
    "207-208": ["2 J"], "209-210": ["2 Z"],
    "301-302": ["3 G"], "303-304": ["3 D"], "305-306": ["3 E"],
    "307-308": ["3 J"],
    "103-104-105-106-107-108": ["1 D", "1 E", "1 J"],
    "201-202-203-204-205-206-212": ["2 G", "2 D", "2 E", "2 K"],
    "207-208-209-210": ["2 J", "2 Z"],
    "301-302-303-304-305-306": ["3 G", "3 D", "3 E"],
    "307-308-309": ["3 J", "3 Z"],
    "1 G": ["1 G"], "1 D": ["1 D"], "1 E": ["1 E"], "1 J": ["1 J"], "1 Z": ["1 Z"],
    "2 G": ["2 G"], "2 D": ["2 D"], "2 E": ["2 E"], "2 J": ["2 J"], "2 Z": ["2 Z"],
    "2 I": ["2 I"], "2 K": ["2 K"], "2 L": ["2 L"],
    "3 G": ["3 G"], "3 D": ["3 D"], "3 E": ["3 E"], "3 J": ["3 J"], "3 Z": ["3 Z"], "3 I": ["3 I"],
    "4 G": ["4 G"], "4 D": ["4 D"], "4 E": ["4 E"],
    "4G": ["4 G"], "4D": ["4 D"], "4E": ["4 E"],
}
