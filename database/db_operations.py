"""
Database operations for the Combined Bot (Schedule functionality)
User data operations using Google Sheets
"""
import sqlite3
import pandas as pd
import json
import os
from typing import Dict
from config.settings import DB_FILE, DATA_DIR, DRIVE_FOLDER_ID
from models.data_models import UserData, BotData
from services.drive_service import upload_to_drive, download_latest_from_drive
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import time

# Global variables for user data spreadsheet
_users_sheets_service = None
_users_spreadsheet_id = None

def init_users_sheets_service(credentials):
    """Initialize Google Sheets service for user data"""
    global _users_sheets_service, _users_spreadsheet_id
    if credentials and not _users_sheets_service:
        _users_sheets_service = build('sheets', 'v4', credentials=credentials)

        # Find or create UsersBotData spreadsheet
        try:
            drive_service = build('drive', 'v3', credentials=credentials)
            results = drive_service.files().list(
                q=f"name='UsersBotData' and mimeType='application/vnd.google-apps.spreadsheet' and '{DRIVE_FOLDER_ID}' in parents",
                fields="files(id, name)"
            ).execute()

            if results.get('files'):
                _users_spreadsheet_id = results['files'][0]['id']
                # Ensure users sheet exists in existing spreadsheet
                spreadsheet = _users_sheets_service.spreadsheets().get(spreadsheetId=_users_spreadsheet_id).execute()
                existing_sheets = [sheet['properties']['title'] for sheet in spreadsheet['sheets']]
                if 'users' not in existing_sheets:
                    # Add users sheet
                    requests = [{
                        'addSheet': {
                            'properties': {
                                'title': 'users'
                            }
                        }
                    }]
                    _users_sheets_service.spreadsheets().batchUpdate(
                        spreadsheetId=_users_spreadsheet_id,
                        body={'requests': requests}
                    ).execute()
                    # Add headers
                    headers = ['user_id', 'role', 'teacher_name', 'group_name', 'notifications', 'state']
                    body = {'values': [headers]}
                    _users_sheets_service.spreadsheets().values().update(
                        spreadsheetId=_users_spreadsheet_id,
                        range='users!A1:F1',
                        valueInputOption='RAW',
                        body=body
                    ).execute()
            else:
                # Create new spreadsheet with users sheet
                spreadsheet = {
                    'properties': {'title': 'UsersBotData'},
                    'sheets': [{
                        'properties': {
                            'title': 'users'
                        }
                    }]
                }
                spreadsheet = _users_sheets_service.spreadsheets().create(
                    body=spreadsheet,
                    fields='spreadsheetId'
                ).execute()
                _users_spreadsheet_id = spreadsheet.get('spreadsheetId')

                # Move to folder
                drive_service.files().update(
                    fileId=_users_spreadsheet_id,
                    addParents=DRIVE_FOLDER_ID,
                    fields='id, parents'
                ).execute()

                # Add headers to users sheet
                headers = ['user_id', 'role', 'teacher_name', 'group_name', 'notifications', 'state']
                body = {'values': [headers]}
                _users_sheets_service.spreadsheets().values().update(
                    spreadsheetId=_users_spreadsheet_id,
                    range='users!A1:F1',
                    valueInputOption='RAW',
                    body=body
                ).execute()

        except Exception as e:
            print(f"Error initializing users spreadsheet: {e}")

def _safe_users_operation(operation_func, max_retries=3, delay=0.1):
    """Perform Users Sheets operation with retry mechanism"""
    for attempt in range(max_retries):
        try:
            return operation_func()
        except HttpError as e:
            if e.resp.status in [429, 500, 502, 503, 504]:
                if attempt < max_retries - 1:
                    print(f"Google Sheets API error (attempt {attempt + 1}), retrying...")
                    time.sleep(delay * (2 ** attempt))
                else:
                    print(f"Google Sheets operation failed after {max_retries} attempts: {e}")
                    raise e
            else:
                print(f"Google Sheets operation error: {e}")
                raise e
        except Exception as e:
            print(f"Unexpected error in users operation: {e}")
            raise e

def init_db():
    """Initialize the database with required tables"""
    with sqlite3.connect(DB_FILE, timeout=10) as conn:
        cursor = conn.cursor()
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS original_schedule
            (id INTEGER PRIMARY KEY AUTOINCREMENT, Kun TEXT, Jupliq INTEGER, Topar TEXT, Pan TEXT, Oqitiwshi TEXT, Kabinet TEXT);
            CREATE TABLE IF NOT EXISTS changes_schedule
            (id INTEGER PRIMARY KEY AUTOINCREMENT, Kun TEXT, Jupliq INTEGER, Topar TEXT, Pan TEXT, Oqitiwshi TEXT, Kabinet TEXT);
            CREATE TABLE IF NOT EXISTS exam_schedule
            (id INTEGER PRIMARY KEY AUTOINCREMENT, Kun TEXT, Waqti TEXT, Topar TEXT, Pan TEXT, Oqitiwshi TEXT, Kabinet TEXT);
            CREATE TABLE IF NOT EXISTS users
            (user_id INTEGER PRIMARY KEY, role TEXT, teacher_name TEXT, group_name TEXT, notifications INTEGER DEFAULT 1, state TEXT);
        ''')
        conn.commit()


def check_table_exists(table_name: str) -> bool:
    """Check if a table exists in the database"""
    with sqlite3.connect(DB_FILE, timeout=10) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        return bool(cursor.fetchone())


def save_user_to_db(user_id: int, user_data: UserData, drive_service):
    """Save user data to Google Sheets"""
    if not _users_sheets_service or not _users_spreadsheet_id:
        return

    def _save():
        try:
            # Read existing users
            result = _users_sheets_service.spreadsheets().values().get(
                spreadsheetId=_users_spreadsheet_id,
                range='users!A:F'
            ).execute()

            values = result.get('values', [])
            headers = ['user_id', 'role', 'teacher_name', 'group_name', 'notifications', 'state']
            existing_data = []
            for row in values[1:]:  # Skip headers
                if len(row) >= 6:
                    existing_data.append({
                        'user_id': row[0],
                        'role': row[1],
                        'teacher_name': row[2],
                        'group_name': row[3],
                        'notifications': row[4],
                        'state': row[5]
                    })

            # Update or add user
            user_row = {
                'user_id': str(user_id),
                'role': user_data.role,
                'teacher_name': user_data.teacher_name,
                'group_name': user_data.group,
                'notifications': str(int(user_data.notifications)),
                'state': user_data.state
            }

            # Remove existing user if present
            existing_data = [row for row in existing_data if row['user_id'] != str(user_id)]
            # Add new/updated user
            existing_data.append(user_row)

            # Prepare data for writing
            write_values = [headers]
            for row in existing_data:
                write_values.append([
                    row['user_id'], row['role'], row['teacher_name'],
                    row['group_name'], row['notifications'], row['state']
                ])

            # Clear the sheet first to avoid leftover data
            _users_sheets_service.spreadsheets().values().clear(
                spreadsheetId=_users_spreadsheet_id,
                range='users!A:Z'
            ).execute()

            # Write new data
            body = {'values': write_values}
            _users_sheets_service.spreadsheets().values().update(
                spreadsheetId=_users_spreadsheet_id,
                range='users!A1',
                valueInputOption='RAW',
                body=body
            ).execute()
            return True
        except Exception as e:
            print(f"Error saving user to Google Sheets: {e}")
            return False

    _safe_users_operation(_save)


def load_users_from_db(drive_service) -> Dict[int, UserData]:
    """Load users from Google Sheets"""
    users = {}

    if not _users_sheets_service or not _users_spreadsheet_id:
        return users

    def _load():
        try:
            result = _users_sheets_service.spreadsheets().values().get(
                spreadsheetId=_users_spreadsheet_id,
                range='users!A:F'
            ).execute()

            values = result.get('values', [])
            if len(values) < 2:  # No data beyond headers
                return users

            headers = values[0]
            for row in values[1:]:
                if len(row) >= 6:
                    user_data = UserData()
                    user_data.role = row[1]
                    user_data.teacher_name = row[2]
                    user_data.group = row[3]
                    user_data.notifications = bool(int(row[4]) if row[4] else 0)
                    user_data.state = row[5]
                    users[int(row[0])] = user_data

        except Exception as e:
            print(f"Error loading users from Google Sheets: {e}")

        return users

    return _safe_users_operation(_load)


def save_to_db(df: pd.DataFrame, table_name: str, drive_service):
    """Save DataFrame to database and sync with Google Drive"""
    with sqlite3.connect(DB_FILE, timeout=10) as conn:
        df.to_sql(table_name, conn, if_exists='replace', index=False)
    
    # Export to CSV for backup
    csv_path = os.path.join(DATA_DIR, f"{table_name}.csv")
    df.to_csv(csv_path, index=False)
    upload_to_drive(drive_service, csv_path, DRIVE_FOLDER_ID)


def get_from_db(table_name: str, drive_service, bot_data: BotData) -> pd.DataFrame:
    """Get data from database, using cache when available"""
    # Check cache first
    if table_name == "exam_schedule" and bot_data.exam_cache is not None:
        return bot_data.exam_cache
    if table_name in ["original_schedule", "changes_schedule"] and bot_data.schedule_cache is not None:
        return bot_data.schedule_cache
    
    # If table doesn't exist locally, try to download from Drive
    if not check_table_exists(table_name):
        csv_path = download_latest_from_drive(drive_service, DRIVE_FOLDER_ID, f"{table_name}.csv")
        if csv_path and os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            with sqlite3.connect(DB_FILE, timeout=10) as conn:
                df.to_sql(table_name, conn, if_exists='replace', index=False)
            
            # Update cache
            if table_name == "exam_schedule":
                bot_data.exam_cache = df
            else:
                bot_data.schedule_cache = df
            return df
        return pd.DataFrame()
    
    # Load from local database
    with sqlite3.connect(DB_FILE, timeout=10) as conn:
        df = pd.read_sql(f'SELECT * FROM {table_name}', conn)
        
        # Update cache
        if table_name == "exam_schedule":
            bot_data.exam_cache = df
        else:
            bot_data.schedule_cache = df
        return df


def clear_db(drive_service, folder_id: str, schedule_type: str) -> bool:
    """Clear database tables and files for specified schedule type"""
    try:
        with sqlite3.connect(DB_FILE, timeout=10) as conn:
            cursor = conn.cursor()
            if schedule_type == "schedule":
                cursor.executescript('''
                    DROP TABLE IF EXISTS original_schedule;
                    DROP TABLE IF EXISTS changes_schedule;
                    CREATE TABLE original_schedule
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, Kun TEXT, Jupliq INTEGER, Topar TEXT, Pan TEXT, Oqitiwshi TEXT, Kabinet TEXT);
                    CREATE TABLE changes_schedule
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, Kun TEXT, Jupliq INTEGER, Topar TEXT, Pan TEXT, Oqitiwshi TEXT, Kabinet TEXT);
                ''')
                prefix = ('keste_bot_', 'original_schedule', 'changes_schedule')
            else:
                cursor.execute('DROP TABLE IF EXISTS exam_schedule')
                cursor.execute('''
                    CREATE TABLE exam_schedule
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, Kun TEXT, Waqti TEXT, Topar TEXT, Pan TEXT, Oqitiwshi TEXT, Kabinet TEXT)
                ''')
                prefix = ('imtixan_keste', 'exam_schedule')
            conn.commit()
        
        # Clear local files
        for file in os.listdir(DATA_DIR):
            if any(file.startswith(p) for p in prefix):
                try:
                    os.remove(os.path.join(DATA_DIR, file))
                except Exception:
                    pass
        
        # Clear Drive files
        if drive_service:
            try:
                results = drive_service.files().list(
                    q=f"'{folder_id}' in parents", 
                    fields="files(id, name)", 
                    pageSize=100
                ).execute()
                for file in results.get('files', []):
                    if any(file['name'].startswith(p) for p in prefix):
                        drive_service.files().delete(fileId=file['id']).execute()
            except Exception as e:
                print(f"Error clearing DB from Drive: {e}")
                return False
        
        return True
    except Exception as e:
        print(f"Error clearing database: {e}")
        return False