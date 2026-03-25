"""
Supabase database handler for the Combined Bot (Attendance functionality)
Replaces csv_handler.py — same public interface, uses Supabase PostgreSQL
"""
import logging
from datetime import datetime
from typing import List, Dict, Optional

from config.settings import TIMEZONE
from services.supabase_service import get_supabase

logger = logging.getLogger(__name__)


class SupabaseHandler:
    """Handles all attendance-related DB operations via Supabase"""

    # ---------- teachers ----------

    def get_teachers(self) -> List[Dict]:
        try:
            res = get_supabase().table('teachers').select('*').execute()
            return res.data or []
        except Exception as e:
            logger.error(f"get_teachers error: {e}")
            return []

    def add_teacher(self, user_id: str, name: str, group: str, school: str) -> bool:
        try:
            get_supabase().table('teachers').upsert({
                'user_id': int(user_id),
                'name': name,
                'group': group,
                'school': school,
            }).execute()
            return True
        except Exception as e:
            logger.error(f"add_teacher error: {e}")
            return False

    def remove_teacher(self, user_id: str) -> bool:
        try:
            get_supabase().table('teachers').delete().eq('user_id', int(user_id)).execute()
            return True
        except Exception as e:
            logger.error(f"remove_teacher error: {e}")
            return False

    # ---------- students ----------

    def get_students(self) -> List[Dict]:
        try:
            res = get_supabase().table('students').select('*').execute()
            return res.data or []
        except Exception as e:
            logger.error(f"get_students error: {e}")
            return []

    def add_student(self, user_id: str, name: str, student_id: str, group: str, school: str) -> bool:
        try:
            get_supabase().table('students').upsert({
                'user_id': int(user_id),
                'name': name,
                'student_id': student_id,
                'group': group,
                'school': school,
            }).execute()
            return True
        except Exception as e:
            logger.error(f"add_student error: {e}")
            return False

    def remove_student(self, user_id: str) -> bool:
        try:
            get_supabase().table('students').delete().eq('user_id', int(user_id)).execute()
            return True
        except Exception as e:
            logger.error(f"remove_student error: {e}")
            return False

    # ---------- schools ----------

    def get_schools(self) -> List[Dict]:
        try:
            res = get_supabase().table('schools').select('*').execute()
            return res.data or []
        except Exception as e:
            logger.error(f"get_schools error: {e}")
            return []

    def update_school_coordinates(self, school_name: str, latitude: float, longitude: float) -> bool:
        try:
            get_supabase().table('schools').upsert({
                'school': school_name,
                'latitude': float(latitude),
                'longitude': float(longitude),
            }).execute()
            return True
        except Exception as e:
            logger.error(f"update_school_coordinates error: {e}")
            return False

    # ---------- attendance ----------

    def get_attendance_records(self) -> List[Dict]:
        try:
            res = get_supabase().table('attendance').select('*').execute()
            return res.data or []
        except Exception as e:
            logger.error(f"get_attendance_records error: {e}")
            return []

    def get_attendance_records_by_group(self, group: str) -> List[Dict]:
        try:
            res = get_supabase().table('attendance').select('*').eq('group', group).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"get_attendance_records_by_group error: {e}")
            return []

    def get_student_attendance_history(self, student_id: str, days: int = 7) -> List[Dict]:
        try:
            res = (
                get_supabase()
                .table('attendance')
                .select('*')
                .eq('student_id', student_id)
                .order('date', desc=True)
                .limit(days if days > 0 else 1000)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.error(f"get_student_attendance_history error: {e}")
            return []

    def record_attendance(
        self,
        student_id: str,
        name: str,
        group: str,
        school: str,
        date: str,
        came_time: Optional[str] = None,
        left_time: Optional[str] = None,
        token: Optional[str] = None,
    ) -> bool:
        """Insert or update today's attendance record for a student"""
        try:
            client = get_supabase()

            # Check if record exists for today
            res = (
                client.table('attendance')
                .select('id,came_time,left_time')
                .eq('student_id', student_id)
                .eq('date', date)
                .execute()
            )
            existing = res.data

            if existing:
                record_id = existing[0]['id']
                update_data = {'name': name}
                if came_time:
                    update_data['came_time'] = came_time
                if left_time:
                    update_data['left_time'] = left_time
                client.table('attendance').update(update_data).eq('id', record_id).execute()
            else:
                client.table('attendance').insert({
                    'student_id': student_id,
                    'name': name,
                    'group': group,
                    'school': school,
                    'date': date,
                    'came_time': came_time or '',
                    'left_time': left_time or '',
                    'status': 'present',
                    'token': token or '',
                }).execute()

            return True
        except Exception as e:
            logger.error(f"record_attendance error: {e}")
            return False

    def add_attendance_record(
        self,
        student_id: str,
        student_name: str,
        group: str,
        school: str,
        action: str,
        timestamp: datetime,
    ) -> bool:
        """Record arrival (Keldim) or departure (Kettim)"""
        date_str = timestamp.strftime("%Y-%m-%d")
        time_str = timestamp.strftime("%H:%M")
        return self.record_attendance(
            student_id=student_id,
            name=student_name,
            group=group,
            school=school,
            date=date_str,
            came_time=time_str if action == "Keldim" else None,
            left_time=time_str if action == "Kettim" else None,
        )
