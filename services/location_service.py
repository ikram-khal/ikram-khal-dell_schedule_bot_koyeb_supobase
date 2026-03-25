"""
Location and attendance service for the Combined Bot
"""
from datetime import datetime
from geopy.distance import geodesic
import uuid
import logging
from config.settings import ALLOWED_RADIUS, TIMEZONE, MIN_ATTENDANCE_HOURS

logger = logging.getLogger(__name__)


class LocationService:
    def __init__(self, db_handler):
        self.db_handler = db_handler
        self._school_cache = {}
        self._cache_timestamp = None
        self._cache_duration = 300  # 5 minutes

    def _get_cached_schools(self):
        current_time = datetime.now().timestamp()
        if (self._cache_timestamp and
                current_time - self._cache_timestamp < self._cache_duration and
                self._school_cache):
            return self._school_cache

        try:
            schools = self.db_handler.get_schools()
            self._school_cache = {
                s.get("school", ""): {
                    "latitude": float(s.get("latitude", 0)),
                    "longitude": float(s.get("longitude", 0)),
                }
                for s in schools
                if s.get("school") and s.get("latitude") and s.get("longitude")
            }
            self._cache_timestamp = current_time
        except Exception as e:
            logger.error(f"Error caching schools: {e}")

        return self._school_cache

    def validate_location(self, user_location, school_name):
        """Validate if user is within allowed radius of school"""
        try:
            schools = self._get_cached_schools()
            if school_name not in schools:
                return False, "Mektep koordinatları tabılmadı."

            coords = schools[school_name]
            if coords["latitude"] == 0 and coords["longitude"] == 0:
                return False, "Mektep koordinatları nadurıs."

            distance = geodesic(
                (user_location.latitude, user_location.longitude),
                (coords["latitude"], coords["longitude"]),
            ).kilometers

            if distance > ALLOWED_RADIUS:
                return False, f"Siz mektepten {distance:.2f} km qashıqlıqtasız."

            return True, f"Geolokaciya durıs! Qashıqlıq: {distance:.2f} km"
        except Exception as e:
            logger.error(f"validate_location error: {e}")
            return False, "Geolokaciya tekseriwde qátelik."


class AttendanceService:
    def __init__(self, db_handler):
        self.db_handler = db_handler
        self._attendance_cache = []
        self._students_cache = []
        self._cache_timestamp = None
        self._cache_duration = 60  # 1 minute

    def _get_cached_attendance(self):
        current_time = datetime.now().timestamp()
        if (self._cache_timestamp and
                current_time - self._cache_timestamp < self._cache_duration and
                self._attendance_cache):
            return self._attendance_cache
        try:
            self._attendance_cache = self.db_handler.get_attendance_records()
            self._cache_timestamp = current_time
        except Exception as e:
            logger.error(f"Error caching attendance: {e}")
        return self._attendance_cache

    def _get_cached_students(self):
        current_time = datetime.now().timestamp()
        if (self._cache_timestamp and
                current_time - self._cache_timestamp < self._cache_duration and
                self._students_cache):
            return self._students_cache
        try:
            self._students_cache = self.db_handler.get_students()
        except Exception as e:
            logger.error(f"Error caching students: {e}")
        return self._students_cache

    def record_arrival(self, student_id, name, group, school):
        try:
            today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
            current_time = datetime.now(TIMEZONE).strftime("%H:%M")

            attendance = self._get_cached_attendance()
            today_record = next(
                (r for r in attendance if r.get("student_id") == student_id and r.get("date") == today),
                None,
            )

            if today_record and today_record.get("came_time"):
                return False, f"Kelgen waqtıńız {today_record['came_time']} dep jazıp alındı."

            token = str(uuid.uuid4())
            success = self.db_handler.record_attendance(
                student_id, name, group, school, today,
                came_time=current_time, token=token,
            )

            if success:
                self._cache_timestamp = None
                return True, f"Kelgeńiz jazıp alındı! Waqıt: {current_time}"
            return False, "Qatnas jazıwda qátelik."
        except Exception as e:
            logger.error(f"record_arrival error: {e}")
            return False, "Kelgen waqtın jazıwda qátelik."

    def record_departure(self, student_id, name, group, school):
        try:
            today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
            current_time = datetime.now(TIMEZONE).strftime("%H:%M")

            attendance = self._get_cached_attendance()
            today_record = next(
                (r for r in attendance if r.get("student_id") == student_id and r.get("date") == today),
                None,
            )

            if not today_record or not today_record.get("came_time"):
                return False, "Búgingi kelgeńizdi belgilemegensiz."
            if today_record.get("left_time"):
                return False, f"Ketken waqtıńız {today_record['left_time']} dep jazıp alındı."

            came_time_str = today_record.get("came_time", "")
            warning_message = ""
            time_spent_message = ""

            if came_time_str:
                try:
                    came_minutes = int(came_time_str.split(':')[0]) * 60 + int(came_time_str.split(':')[1])
                    curr_minutes = int(current_time.split(':')[0]) * 60 + int(current_time.split(':')[1])
                    if curr_minutes < came_minutes:
                        curr_minutes += 24 * 60
                    diff = curr_minutes - came_minutes
                    if diff / 60 < MIN_ATTENDANCE_HOURS:
                        warning_message = f"Eskertiw! Siz mektepte {diff / 60:.1f} saat boldıńız."
                    time_spent_message = f"\nMektepte boldıńız: {diff // 60} saat {diff % 60} minut"
                except Exception:
                    pass

            success = self.db_handler.record_attendance(
                student_id, name, group, school, today, left_time=current_time
            )

            if success:
                self._cache_timestamp = None
                msg = f"Ketkenińiz jazıp alındı! Waqıt: {current_time}{time_spent_message}"
                if warning_message:
                    msg = warning_message + "\n" + msg
                return True, msg
            return False, "Ketken waqtın jazıwda qátelik."
        except Exception as e:
            logger.error(f"record_departure error: {e}")
            return False, "Ketken waqtın jazıwda qátelik."

    def get_attendance_report(self, teacher_group):
        try:
            today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
            attendance = self._get_cached_attendance()
            students = self._get_cached_students()

            today_records = [
                r for r in attendance
                if r.get("date") == today and r.get("group") == teacher_group
            ]

            if not today_records:
                return f"{teacher_group} toparında {today} sánesinde qatnas maǵlıwmatları joq."

            report = f"{today} sánesi ushın {teacher_group} toparınıń qatnas maǵlıwmatları:\n"
            for record in today_records:
                sid = record.get("student_id", "")
                student = next((s for s in students if s.get("student_id") == sid), None)
                if student:
                    name = student.get("name", "Belgisiz")
                    came = record.get("came_time") or "-"
                    left = record.get("left_time") or "-"
                    time_in = ""
                    if came != "-" and left != "-":
                        try:
                            cm = int(came.split(':')[0]) * 60 + int(came.split(':')[1])
                            lm = int(left.split(':')[0]) * 60 + int(left.split(':')[1])
                            if lm < cm:
                                lm += 24 * 60
                            total = lm - cm
                            time_in = f" ({total // 60} saat {total % 60} minut)"
                        except Exception:
                            pass
                    report += f"- {name}:\n  Keldi: {came}\n  Ketti: {left}{time_in}\n"
            return report
        except Exception as e:
            logger.error(f"get_attendance_report error: {e}")
            return "Qatnas maǵlıwmatların alıwda qátelik."
