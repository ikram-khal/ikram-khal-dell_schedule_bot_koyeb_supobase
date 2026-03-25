# Railway Deployment Guide

## CSV Migration Complete ✅

Your Telegram bot has been successfully migrated from Google Sheets to CSV files for attendance data storage.

## Deployment Instructions

### For Railway Deployment:

1. **Update your Railway service to use the new main file:**
   - Change the start command from `python main.py` to `python railway_main.py`

2. **Update requirements.txt:**
   - The requirements.txt now specifies `python-telegram-bot==21.4` which is compatible with Railway

3. **Environment Variables:**
   - Make sure all your environment variables are set in Railway:
     - `BOT_TOKEN`
     - `ADMIN_USER_ID`
     - `GOOGLE_DRIVE_CREDENTIALS` (if using schedule functionality)

### Key Changes Made:

1. **CSV Handler**: Replaced Google Sheets with local CSV file storage
2. **Version Compatibility**: Updated to python-telegram-bot v21.4 for Railway compatibility
3. **Async/Await**: Modern async patterns for better performance

### Data Structure Preserved:
- `attendance.csv`: `student_id, name, group, school, date, came_time, left_time, status, token`
- `teachers.csv`: `user_id, name, group, school`
- `students.csv`: `user_id, name, student_id, group, school`
- `schools.csv`: `school, latitude, longitude`

### Files Location:
CSV files are stored in the Railway container's temp directory: `/tmp/combined_bot/data/`

## Troubleshooting:

If you still get errors, check:
1. Environment variables are properly set
2. Railway is using `python railway_main.py` as the start command
3. All dependencies in requirements.txt are installed

## Local Development:

For local development, continue using `python main.py` (compatible with python-telegram-bot v20.x).
For Railway deployment, use `python railway_main.py` (compatible with python-telegram-bot v21.x).