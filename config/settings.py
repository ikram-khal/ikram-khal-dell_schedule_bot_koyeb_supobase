"""
Configuration settings for the Combined Bot (Attendance + Schedule)
"""
import os
import tempfile
import pytz

# Bot Configuration
BOT_TOKEN = "7385854628:AAGpv4SD7Qcb-T-kg9ticIx19WIc604bw5o"
ADMIN_USER_ID = "343553810"
ALLOWED_USERS = {343553810}  # Changed to set for faster lookup

# Google Sheets Configuration (DEPRECATED - Now using CSV files)
# GOOGLE_CREDENTIALS = None  # No longer needed for CSV implementation

# Google Drive Configuration (for Schedule)
DRIVE_CREDENTIALS = "ewogICJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIsCiAgInByb2plY3RfaWQiOiAic2NoZWR1bGVib3QtNDU2ODE2IiwKICAicHJpdmF0ZV9rZXlfaWQiOiAiZWQ5MzJmYzExZjllNjM2NDM5OGI1Nzk2YjA2YTU0MmM2ZDBiNmZhOSIsCiAgInByaXZhdGVfa2V5IjogIi0tLS0tQkVHSU4gUFJJVkFURSBLRVktLS0tLVxuTUlJRXZBSUJBREFOQmdrcWhraUc5dzBCQVFFRkFBU0NCS1l3Z2dTaUFnRUFBb0lCQVFDNWlFWVdxVFZRMDl0WVxuTXdQa2VQcktRQWozS0hZdmprb0V2YTdXaGF0Y3Q4Y2lpeXFCR2JIOWpJaERPbmJOOTRQeDVaWExzZk9weDJwMVxuUS85Wmh4d245YTEvOXNUOW10bzhRRkw5bVpMUkduUXV0by9qbFFuYjJYMDhYbmhQMjRoZnVLSkxLVllkS295WlxuRTFSZzhsdWFTbHZmZFdvWmM0UFVyMmhNSDZRZG5ET3dDam1weU5vVSs5ajdVU2p1SG12WG85MkYyempqVUVEY1xuKzljR1Bqd3c1UlNXejR2RjJ4Z24zK3pCWFcvbkFjdnVodlNpbFBFOWU0KzZuKzB0ellielFpSEV5d0lSVDlGaVxudnBvNFkzNzhtbHNJZFZqdmV6dTAwR21QU0E0TjFJcUxqMHY1eTVXdHNSZTBPZlphRmRCeTVBMU04dmFOeTVCNVxuRVd1QmlHMUJBZ01CQUFFQ2dnRUFBWHE2bmxoNU81eXVNWDVFcFcxK2lIUXBiaVBGTk5JSnVUbkpwZ2h1VlBZRlxuTVR0b0JSd0VsK2VSNHV3RUxGWnhMUHhlUWxVaXJZT21KUlc3K0pyZWMxdDBQUGZsaGJxQlMzemRmSXdIM1piUlxucVlRSFVvZ0FIN1UvV0ZGNDNFclNtVkFpVm43cytCeThWQnNtbWkyaDQ5d25HVGw1TlZ5VVhFZzRIaHFjSnlmeFxuekNNam54eXRSK09yeTM0N0pxZVFxdTNSOHVYYnJuQStDRE1NN2l5MkN1aURWSTQ0TXI0dGlwRHVzREliRU0zUFxucG1GSkR4UlpId3dzM0RlMVdLVjNIWmk5dldyZ1JGZytzZzRDRE5RR3lhYTEvQUQwMzczZXl1QzN0cEpFdWRza1xuZ3VZOEwxaHBhekVudGJLSFBqOXBiY0JmeWxPUGdhbFl5dm9vMkpWWkFRS0JnUUR2bWJyUFZhODFsVFlVM0VxOFxuNm1vRXliTHZLc0tsYnNXWFFCK0k4Z1kxUTZoNGRBNjY3cVQ1ZGNZY2FqVWhUcTVQeXZZUm54Y0ZxWVFzSUxSYVxuQkpBMWdpQ2FoeEhWMXNqclhxT1RBZ0pJVlNwU0xmVzVwSWYvRHFIbW05VVhxTnNSanV3dXlQRTZkSStnU29tU1xuMUpKZW9jVlQ4YzVlaUZtbW1BMitQN2ZyWVFLQmdRREdPeW5hb2E0LzFxQlNyUDZEYTlITTZRc1RwSXlZc3RWMlxuNWdQMlIvNmErVFlmNjBxWFRJUHBWOXE5aWo3L3VvNGhEUnF4bWtGYy9uMjl5bUpXaDFqSk9nSTNNUUx1VUpEQ1xuQnQwTWI3TEM5T3VKOCtEaG5Vcm9XZGFJMmVjcGNaSkw4RTkzc2t1c2MxbEhVR3p3RDlPeWtFUjI5aU45NkloWlxuQU5heDZoS3Q0UUtCZ0JIMFZDSmJTbURhaUkzeG9Bd2VDTW5KRDRhS2pzRjAxb3VwKzNMNHAreHY0SHorUFdoV1xubjdndDBpV284OGhHTEJ2QW1zWGhSUWxnbFkzMCtXN1JicmtEd2t1eUdXMEx4a3lVNys4Qk5JaVZFVEhOVGQrV1xuYTdaNk16bWpyY2t6Rnc5dXhWWVFLcnQxcHBtZFhFZkxkQmh4U09jc2RJbHk4RHppb2cwQ20xYWhBb0dBS1ZSc1xuaFlqd0s1ODBEZ2pEaCtNUyt3WWJxUnpGczVDVnNSU0QvdlZEd0V2MVhQSlJ1dm5aQnUycVRacGxTQ3c5TmVibFxuaWVIL2ZzUVFzMkZlMzJ1WXQxdkEyb0Q5ZTNLUXUrTnljd1ZXNEE3d2pQS3NFRjRiSUJhYkJDMXFaTm1wQnV3elxucFdFbkplMW16OWVVM3ZodHl1MEpXVVE0WWlmNVJaVkhMaEQvbEFFQ2dZQjVzQVN2L3VIVHZJRGFiVjJTaFdCTVxuZUdYVERtbFZ6eFpoNndaR2VHMURqeWdxandwbEVyTWlJelZ1eWwxZlFOUlJGRFhablBIUy9tS1VZc2FuWENuNlxuQytoQnZEc0t0SXVqRllNckJNYW5TRlNkblNlYWVmZkNkeHVxTytKOGZxbmRjdVRaUnpwcGJEWnc5bUh3L2V5WFxuMnNhbW5DSzUrMWl5d2JKWElHUWhXdz09XG4tLS0tLUVORCBQUklWQVRFIEtFWS0tLS0tXG4iLAogICJjbGllbnRfZW1haWwiOiAic2NoZWR1bGUtYm90QHNjaGVkdWxlYm90LTQ1NjgxNi5pYW0uZ3NlcnZpY2VhY2NvdW50LmNvbSIsCiAgImNsaWVudF9pZCI6ICIxMTI5MDM1MzEyMDAzOTU3NDYwNzYiLAogICJhdXRoX3VyaSI6ICJodHRwczovL2FjY291bnRzLmdvb2dsZS5jb20vby9vYXV0aDIvYXV0aCIsCiAgInRva2VuX3VyaSI6ICJodHRwczovL29hdXRoMi5nb29nbGVhcGlzLmNvbS90b2tlbiIsCiAgImF1dGhfcHJvdmlkZXJfeDUwOV9jZXJ0X3VybCI6ICJodHRwczovL3d3dy5nb29nbGVhcGlzLmNvbS9vYXV0aDIvdjEvY2VydHMiLAogICJjbGllbnRfeDUwOV9jZXJ0X3VybCI6ICJodHRwczovL3d3dy5nb29nbGVhcGlzLmNvbS9yb2JvdC92MS9tZXRhZGF0YS94NTA5L3NjaGVkdWxlLWJvdCU0MHNjaGVkdWxlYm90LTQ1NjgxNi5pYW0uZ3NlcnZpY2VhY2NvdW50LmNvbSIsCiAgInVuaXZlcnNlX2RvbWFpbiI6ICJnb29nbGVhcGlzLmNvbSIKfQo="  # Replace with actual token
DRIVE_FOLDER_ID = "1rxpNwOqHWIuI02KWbdBTKSpji6t5s9OY"
DRIVE_ID = "1rxpNwOqHWIuI02KWbdBTKSpji6t5s9OY"

# Data Configuration
DATA_DIR = os.path.join(tempfile.gettempdir(), "combined_bot", "data")
DB_FILE = os.path.join(DATA_DIR, "combined.db")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Application Constants (Attendance)
# SPREADSHEET_NAME = "AttendanceBotData"  # No longer needed for CSV implementation
ALLOWED_RADIUS = 0.1  # 100 meters in kilometers
# REMOVED: LOCATION_TIMEOUT = 30  # 30-second limitation removed for real-time location
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
GROUPS = ["1G", "1D", "1E", "1J", "1Z", "2G", "2G", "2D", "2E", "2J", "2Z", "2I", "2K", "2L", "3G", "3D", "3E", "3J", "3Z", "3I", "4G", "4D", "4E"]
SCHOOLS = ["4-mektep", "7-mektep", "11-mektep", "12-mektep", "24-mektep", "31-mektep", "42-mektep", "Al-Xorezmiy QMI"]

# Course-based group organization for attendance
COURSE_GROUPS = {
    "1-kurs": ["1G", "1D", "1E", "1J", "1I",],
    "2-kurs": ["2G", "2D", "2E", "2J", "2Z", "2I", "2K", "2L"],
    "3-kurs": ["3G", "3D", "3E", "3J", "3Z", "3I"],
    "4-kurs": ["4G", "4D", "4E"]
}

# Group unions for schedule
GROUP_UNIONS = {
    # Individual groups (all groups can be separate)
    "101": ["101"], "102": ["102"], "103": ["103"], "104": ["104"], "105": ["105"],
    "106": ["106"], "107": ["107"], "108": ["108"], "109": ["109"], 
    "201": ["201"], "202": ["202"], "203": ["203"], "204": ["204"], "205": ["205"],
    "206": ["206"], "207": ["207"], "208": ["208"], "209": ["209"], "210": ["210"],
    "211": ["211"], "212": ["212"],
    "301": ["301"], "302": ["302"], "303": ["303"], "304": ["304"], "305": ["305"],
    "306": ["306"], "307": ["307"], "308": ["308"], "309": ["309"], "310": ["310"],
    
    # Paired groups (as specified)
    "101-102": ["101", "102"],
    "103-104": ["103", "104"], "105-106": ["105", "106"], "107-108": ["107", "108"],
    "201-202": ["201", "202"], "203-204": ["203", "204"], "205-206": ["205", "206"],
    "207-208": ["207", "208"], "209-210": ["209", "210"],
    "301-302": ["301", "302"], "303-304": ["303", "304"], "305-306": ["305", "306"],
    "307-308": ["307", "308"],
    
    # Full unions (when "all together")
    "103-104-105-106-107-108": ["103", "104", "105", "106", "107", "108"],
    "201-202-203-204-205-206-212": ["201", "202", "203", "204", "205", "206", "212"],
    "207-208-209-210": ["207", "208", "209", "210"],
    "301-302-303-304-305-306": ["301", "302", "303", "304", "305", "306"],
    "307-308-309": ["307", "308", "309"]
}

# Group unions for exams
EXAM_GROUP_UNIONS = {
    # Individual groups
    "101": ["1 G"], "102": ["1 G"], "103": ["1 D"], "104": ["1 D"], "105": ["1 E"],
    "106": ["1 E"], "107": ["1 J"], "108": ["1 J"], "109": ["1 Z"],
    "201": ["2 G"], "202": ["2 G"], "203": ["2 D"], "204": ["2 D"], "205": ["2 E"],
    "206": ["2 E"], "207": ["2 J"], "208": ["2 J"], "209": ["2 Z"], "210": ["2 Z"],
    "211": ["2 I"], "212": ["2 K"], "213": ["2 L"],
    "301": ["3 G"], "302": ["3 G"], "303": ["3 D"], "304": ["3 D"], "305": ["3 E"],
    "306": ["3 E"], "307": ["3 J"], "308": ["3 J"], "309": ["3 Z"], "310": ["3 I"],
    
    # Paired groups
    "101-102": ["1 G"],
    "103-104": ["1 D"], "105-106": ["1 E"], "107-108": ["1 J"],
    "201-202": ["2 G"], "203-204": ["2 D"], "205-206": ["2 E"],
    "207-208": ["2 J"], "209-210": ["2 Z"],
    "301-302": ["3 G"], "303-304": ["3 D"], "305-306": ["3 E"],
    "307-308": ["3 J"],
    
    # Full unions
    "103-104-105-106-107-108": ["1 D", "1 E", "1 J"],
    "201-202-203-204-205-206-212": ["2 G", "2 D", "2 E", "2 K"],
    "207-208-209-210": ["2 J", "2 Z"],
    "301-302-303-304-305-306": ["3 G", "3 D", "3 E"],
    "307-308-309": ["3 J", "3 Z"],
    
    # Exam groups (standalone)
    "1 G": ["1 G"], "1 D": ["1 D"], "1 E": ["1 E"], "1 J": ["1 J"], "1 Z": ["1 Z"],
    "2 G": ["2 G"], "2 D": ["2 D"], "2 E": ["2 E"], "2 J": ["2 J"], "2 Z": ["2 Z"],
    "2 I": ["2 I"], "2 K": ["2 K"], "2 L": ["2 L"],
    "3 G": ["3 G"], "3 D": ["3 D"], "3 E": ["3 E"], "3 J": ["3 J"], "3 Z": ["3 Z"], "3 I": ["3 I"],
    "4 G": ["4 G"], "4 D": ["4 D"], "4 E": ["4 E"]

}

