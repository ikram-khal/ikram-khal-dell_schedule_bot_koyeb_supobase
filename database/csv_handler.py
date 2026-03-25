"""
Google Sheets database handler for the Combined Bot (Attendance functionality)
Uses Google Spreadsheet "AttendanceBotData" with multiple sheets
"""
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from config.settings import DATA_DIR, TIMEZONE, DRIVE_FOLDER_ID
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import time

logger = logging.getLogger(__name__)

class CSVHandler:
    def __init__(self, drive_service, credentials):
        self.drive_service = drive_service
        self.credentials = credentials
        self.sheets_service = None
        self.spreadsheet_id = None
        self.sheet_names = ['teachers', 'students', 'schools', 'attendance']
        if credentials:
            self.sheets_service = build('sheets', 'v4', credentials=credentials)
            self.initialize_spreadsheet()
    
    def initialize_spreadsheet(self):
        """Initialize or find Google Spreadsheet 'AttendanceBotData'"""
        if not self.sheets_service:
            return

        try:
            # Search for existing spreadsheet
            results = self.drive_service.files().list(
                q=f"name='AttendanceBotData' and mimeType='application/vnd.google-apps.spreadsheet' and '{DRIVE_FOLDER_ID}' in parents",
                fields="files(id, name)"
            ).execute()

            if results.get('files'):
                self.spreadsheet_id = results['files'][0]['id']
                logger.info(f"Found existing spreadsheet: {self.spreadsheet_id}")
            else:
                # Create new spreadsheet
                spreadsheet = {
                    'properties': {'title': 'AttendanceBotData'}
                }
                spreadsheet = self.sheets_service.spreadsheets().create(
                    body=spreadsheet,
                    fields='spreadsheetId'
                ).execute()
                self.spreadsheet_id = spreadsheet.get('spreadsheetId')

                # Move to folder
                self.drive_service.files().update(
                    fileId=self.spreadsheet_id,
                    addParents=DRIVE_FOLDER_ID,
                    fields='id, parents'
                ).execute()

                logger.info(f"Created new spreadsheet: {self.spreadsheet_id}")

            # Ensure sheets exist
            self._ensure_sheets_exist()

        except Exception as e:
            logger.error(f"Error initializing spreadsheet: {e}")

    def _ensure_sheets_exist(self):
        """Ensure all required sheets exist in the spreadsheet"""
        if not self.spreadsheet_id or not self.sheets_service:
            return

        try:
            spreadsheet = self.sheets_service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
            existing_sheets = [sheet['properties']['title'] for sheet in spreadsheet['sheets']]

            headers = {
                'teachers': ['user_id', 'name', 'group', 'school'],
                'students': ['user_id', 'name', 'student_id', 'group', 'school'],
                'schools': ['school', 'latitude', 'longitude'],
                'attendance': ['student_id', 'name', 'group', 'school', 'date', 'came_time', 'left_time', 'status', 'token']
            }

            requests = []
            for sheet_name in self.sheet_names:
                if sheet_name not in existing_sheets:
                    # Add sheet
                    requests.append({
                        'addSheet': {
                            'properties': {
                                'title': sheet_name
                            }
                        }
                    })

            if requests:
                self.sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body={'requests': requests}
                ).execute()

            # Add headers to new sheets
            for sheet_name, columns in headers.items():
                if sheet_name not in existing_sheets:
                    self._write_sheet_headers(sheet_name, columns)

        except Exception as e:
            logger.error(f"Error ensuring sheets exist: {e}")

    def _write_sheet_headers(self, sheet_name, headers):
        """Write headers to a sheet"""
        try:
            range_name = f'{sheet_name}!A1:{chr(65 + len(headers) - 1)}1'
            body = {
                'values': [headers]
            }
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
        except Exception as e:
            logger.error(f"Error writing headers to {sheet_name}: {e}")

    def _safe_sheets_operation(self, operation_func, max_retries=3, delay=0.1):
        """Perform Sheets operation with retry mechanism for concurrent access"""
        for attempt in range(max_retries):
            try:
                return operation_func()
            except HttpError as e:
                if e.resp.status in [429, 500, 502, 503, 504]:  # Retryable errors
                    if attempt < max_retries - 1:
                        logger.warning(f"Google Sheets API error (attempt {attempt + 1}), retrying...")
                        time.sleep(delay * (2 ** attempt))
                    else:
                        logger.error(f"Failed Google Sheets operation after {max_retries} attempts: {e}")
                        raise e
                else:
                    raise e
    
    def read_csv(self, file_type: str) -> List[Dict[str, str]]:
        """Read data from Google Sheets and return as list of dictionaries"""
        if file_type not in self.sheet_names or not self.spreadsheet_id or not self.sheets_service:
            logger.warning(f"Cannot read sheet {file_type}")
            return []

        def _read():
            try:
                result = self.sheets_service.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range=f'{file_type}!A:Z'
                ).execute()

                values = result.get('values', [])
                if not values:
                    return []

                headers = values[0]
                data = []
                for row in values[1:]:
                    row_dict = {}
                    for i, header in enumerate(headers):
                        row_dict[header] = row[i] if i < len(row) else ''
                    data.append(row_dict)

                return data
            except Exception as e:
                logger.error(f"Error reading Google Sheet {file_type}: {e}")
                return []

        return self._safe_sheets_operation(_read)
    
    def write_csv(self, file_type: str, data: List[Dict[str, str]]):
        """Write data to Google Sheets"""
        if file_type not in self.sheet_names or not self.spreadsheet_id or not self.sheets_service:
            logger.error(f"Cannot write to sheet {file_type}")
            return False

        if not data:
            logger.warning(f"No data to write to {file_type}")
            return True

        def _write():
            try:
                # Convert data to values format
                if data:
                    headers = list(data[0].keys())
                    values = [headers]  # Add headers
                    for row in data:
                        values.append([row.get(h, '') for h in headers])

                    body = {'values': values}
                    self.sheets_service.spreadsheets().values().update(
                        spreadsheetId=self.spreadsheet_id,
                        range=f'{file_type}!A1',
                        valueInputOption='RAW',
                        body=body
                    ).execute()
                return True
            except Exception as e:
                logger.error(f"Error writing Google Sheet {file_type}: {e}")
                return False

        return self._safe_sheets_operation(_write)
    
    def append_to_csv(self, file_type: str, row_data: Dict[str, str]):
        """Append a single row to Google Sheets"""
        if file_type not in self.sheet_names or not self.spreadsheet_id or not self.sheets_service:
            logger.error(f"Cannot append to sheet {file_type}")
            return False

        def _append():
            try:
                # Get current data to determine next row
                result = self.sheets_service.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range=f'{file_type}!A:A'
                ).execute()

                values = result.get('values', [])
                next_row = len(values) + 1

                # If no headers, add them first
                if next_row == 1:
                    headers = list(row_data.keys())
                    body = {'values': [headers]}
                    self.sheets_service.spreadsheets().values().update(
                        spreadsheetId=self.spreadsheet_id,
                        range=f'{file_type}!A1',
                        valueInputOption='RAW',
                        body=body
                    ).execute()
                    next_row = 2

                # Append the row
                row_values = [row_data.get(h, '') for h in row_data.keys()]
                body = {'values': [row_values]}
                self.sheets_service.spreadsheets().values().append(
                    spreadsheetId=self.spreadsheet_id,
                    range=f'{file_type}!A{next_row}',
                    valueInputOption='RAW',
                    body=body
                ).execute()

                return True
            except Exception as e:
                logger.error(f"Error appending to Google Sheet {file_type}: {e}")
                return False

        return self._safe_sheets_operation(_append)
    
    def get_teachers(self) -> List[Dict[str, str]]:
        """Get all teachers from the teachers CSV"""
        try:
            return self.read_csv('teachers')
        except Exception as e:
            logger.error(f"Error getting teachers: {e}")
            return []
    
    def get_students(self) -> List[Dict[str, str]]:
        """Get all students from the students CSV"""
        try:
            return self.read_csv('students')
        except Exception as e:
            logger.error(f"Error getting students: {e}")
            return []
    
    def get_schools(self) -> List[Dict[str, str]]:
        """Get all schools from the schools CSV"""
        try:
            return self.read_csv('schools')
        except Exception as e:
            logger.error(f"Error getting schools: {e}")
            return []
    
    def get_attendance_records(self) -> List[Dict[str, str]]:
        """Get all attendance records"""
        try:
            return self.read_csv('attendance')
        except Exception as e:
            logger.error(f"Error getting attendance records: {e}")
            return []
    
    def add_teacher(self, user_id: str, name: str, group: str, school: str) -> bool:
        """Add a new teacher"""
        try:
            teacher_data = {
                'user_id': str(user_id).strip(),
                'name': name,
                'group': group,
                'school': school
            }
            return self.append_to_csv('teachers', teacher_data)
        except Exception as e:
            logger.error(f"Error adding teacher: {e}")
            return False
    
    def add_student(self, user_id: str, name: str, student_id: str, group: str, school: str) -> bool:
        """Add a new student"""
        try:
            student_data = {
                'user_id': str(user_id).strip(),
                'name': name,
                'student_id': student_id,
                'group': group,
                'school': school
            }
            return self.append_to_csv('students', student_data)
        except Exception as e:
            logger.error(f"Error adding student: {e}")
            return False

    def remove_teacher(self, user_id: str) -> bool:
        """Remove a teacher by user_id"""
        try:
            teachers = self.get_teachers()
            filtered_teachers = [t for t in teachers if str(t.get('user_id', '')).strip() != str(user_id).strip()]
            return self.write_csv('teachers', filtered_teachers)
        except Exception as e:
            logger.error(f"Error removing teacher {user_id}: {e}")
            return False

    def remove_student(self, user_id: str) -> bool:
        """Remove a student by user_id"""
        try:
            students = self.get_students()
            filtered_students = [s for s in students if str(s.get('user_id', '')).strip() != str(user_id).strip()]
            return self.write_csv('students', filtered_students)
        except Exception as e:
            logger.error(f"Error removing student {user_id}: {e}")
            return False
    
    def update_school_coordinates(self, school_name: str, latitude: float, longitude: float) -> bool:
        """Update or add school coordinates"""
        try:
            schools = self.get_schools()
            school_found = False
            
            # Update existing school
            for school in schools:
                if school.get('school', '') == school_name:
                    school['latitude'] = str(latitude)
                    school['longitude'] = str(longitude)
                    school_found = True
                    break
            
            if not school_found:
                # Add new school
                schools.append({
                    'school': school_name,
                    'latitude': str(latitude),
                    'longitude': str(longitude)
                })
            
            return self.write_csv('schools', schools)
        except Exception as e:
            logger.error(f"Error updating school coordinates: {e}")
            return False
    
    def record_attendance(self, student_id: str, name: str, group: str, school: str, 
                         date: str, came_time: Optional[str] = None, 
                         left_time: Optional[str] = None, token: Optional[str] = None) -> bool:
        """Record attendance for a student"""
        try:
            attendance_records = self.get_attendance_records()
            
            # Check if record exists for today
            today_record = None
            record_index = -1
            for i, record in enumerate(attendance_records):
                if (record.get('student_id', '') == student_id and 
                    record.get('date', '') == date):
                    today_record = record
                    record_index = i
                    break
            
            if today_record:
                # Update existing record
                if came_time:
                    attendance_records[record_index]['came_time'] = came_time
                if left_time:
                    attendance_records[record_index]['left_time'] = left_time
                attendance_records[record_index]['name'] = name
                
                return self.write_csv('attendance', attendance_records)
            else:
                # Create new record
                attendance_data = {
                    'student_id': student_id,
                    'name': name,
                    'group': group,
                    'school': school,
                    'date': date,
                    'came_time': came_time or '',
                    'left_time': left_time or '',
                    'status': 'present',
                    'token': token or ''
                }
                return self.append_to_csv('attendance', attendance_data)
        except Exception as e:
            logger.error(f"Error recording attendance: {e}")
            return False
    
    def get_attendance_records_by_group(self, group: str) -> List[Dict[str, str]]:
        """Get attendance records filtered by group"""
        try:
            all_records = self.get_attendance_records()
            return [record for record in all_records if record.get('group', '') == group]
        except Exception as e:
            logger.error(f"Error getting attendance records for group {group}: {e}")
            return []
    
    def get_student_attendance_history(self, student_id: str, days: int = 7) -> List[Dict[str, str]]:
        """Get attendance history for a specific student"""
        try:
            all_records = self.get_attendance_records()
            student_records = [record for record in all_records if record.get('student_id', '') == student_id]
            
            # Sort by date (most recent first)
            student_records.sort(key=lambda x: x.get('date', ''), reverse=True)
            
            # Return only the requested number of days
            return student_records[:days] if days > 0 else student_records
        except Exception as e:
            logger.error(f"Error getting attendance history for student {student_id}: {e}")
            return []
    
    def add_attendance_record(self, student_id: str, student_name: str, group: str, 
                            school: str, action: str, timestamp: datetime) -> bool:
        """Add attendance record with action (Keldim/Kettim)"""
        try:
            date_str = timestamp.strftime("%Y-%m-%d")
            time_str = timestamp.strftime("%H:%M")
            
            attendance_records = self.get_attendance_records()
            
            # Check if record exists for today
            today_record = None
            record_index = -1
            for i, record in enumerate(attendance_records):
                if (record.get('student_id', '') == student_id and 
                    record.get('date', '') == date_str):
                    today_record = record
                    record_index = i
                    break
            
            if today_record:
                # Update existing record
                if action == "Keldim":
                    attendance_records[record_index]['came_time'] = time_str
                elif action == "Kettim":
                    attendance_records[record_index]['left_time'] = time_str
                attendance_records[record_index]['name'] = student_name
                
                return self.write_csv('attendance', attendance_records)
            else:
                # Create new record
                attendance_data = {
                    'student_id': student_id,
                    'name': student_name,
                    'group': group,
                    'school': school,
                    'date': date_str,
                    'came_time': time_str if action == "Keldim" else '',
                    'left_time': time_str if action == "Kettim" else '',
                    'status': 'present',
                    'token': ''
                }
                return self.append_to_csv('attendance', attendance_data)
        except Exception as e:
            logger.error(f"Error adding attendance record: {e}")
            return False