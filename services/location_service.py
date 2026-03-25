"""
Location and attendance service for the Combined Bot
30-second limitation REMOVED for real-time location tracking
"""
from datetime import datetime
from geopy.distance import geodesic
import uuid
import logging
from config.settings import ALLOWED_RADIUS, TIMEZONE, MIN_ATTENDANCE_HOURS

logger = logging.getLogger(__name__)

class LocationService:
    def __init__(self, csv_handler):
        self.csv_handler = csv_handler
        self._school_cache = {}  # Cache for school coordinates
        self._cache_timestamp = None
        self._cache_duration = 300  # 5 minutes cache
    
    def _get_cached_schools(self):
        """Get schools with caching for better performance"""
        current_time = datetime.now().timestamp()
        
        # Check if cache is valid
        if (self._cache_timestamp and
            current_time - self._cache_timestamp < self._cache_duration and
            self._school_cache):
            return self._school_cache
        
        # Refresh cache
        try:
            schools = self.csv_handler.get_schools()
            self._school_cache = {
                school.get("school", ""): {
                    "latitude": float(school.get("latitude", 0)),
                    "longitude": float(school.get("longitude", 0))
                }
                for school in schools
                if school.get("school") and school.get("latitude") and school.get("longitude")
            }
            self._cache_timestamp = current_time
            return self._school_cache
        except Exception as e:
            logger.error(f"Error caching schools: {e}")
            return self._school_cache or {}
    
    def validate_location(self, user_location, school_name):
        """Validate if user is within allowed radius of school - OPTIMIZED"""
        try:
            # Use cached school data for faster lookup
            schools_cache = self._get_cached_schools()
            
            if school_name not in schools_cache:
                return False, "Mektep koordinatları tabılmadı."
            
            school_coords = schools_cache[school_name]
            school_lat = school_coords["latitude"]
            school_lon = school_coords["longitude"]
            
            if school_lat == 0 and school_lon == 0:
                return False, "Mektep koordinatları nadurıs."
            
            # Fast distance calculation using geodesic
            distance = geodesic(
                (user_location.latitude, user_location.longitude),
                (school_lat, school_lon)
            ).kilometers
            
            if distance > ALLOWED_RADIUS:
                return False, f"Siz mektepten {distance:.2f} km qashıqlıqtasız."
            
            return True, f"Geolokaciya durıs! Qashıqlıq: {distance:.2f} km"
            
        except Exception as e:
            logger.error(f"Error validating location: {e}")
            return False, "Geolokaciya tekseriwde qátelik."

class AttendanceService:
    def __init__(self, csv_handler):
        self.csv_handler = csv_handler
        self._attendance_cache = {}
        self._students_cache = {}
        self._cache_timestamp = None
        self._cache_duration = 60  # 1 minute cache for attendance data
    
    def _get_cached_attendance(self):
        """Get attendance records with caching for better performance"""
        current_time = datetime.now().timestamp()
        
        # Check if cache is valid
        if (self._cache_timestamp and
            current_time - self._cache_timestamp < self._cache_duration and
            self._attendance_cache):
            return self._attendance_cache
        
        # Refresh cache
        try:
            records = self.csv_handler.get_attendance_records()
            self._attendance_cache = records
            self._cache_timestamp = current_time
            return records
        except Exception as e:
            logger.error(f"Error caching attendance: {e}")
            return self._attendance_cache or []
    
    def _get_cached_students(self):
        """Get students with caching for better performance"""
        current_time = datetime.now().timestamp()
        
        # Check if cache is valid (use same timestamp as attendance)
        if (self._cache_timestamp and
            current_time - self._cache_timestamp < self._cache_duration and
            self._students_cache):
            return self._students_cache
        
        # Refresh cache
        try:
            students = self.csv_handler.get_students()
            self._students_cache = students
            return students
        except Exception as e:
            logger.error(f"Error caching students: {e}")
            return self._students_cache or []
    
    def record_arrival(self, student_id, name, group, school):
        """Record student arrival - OPTIMIZED with caching"""
        try:
            today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
            current_time = datetime.now(TIMEZONE).strftime("%H:%M")
            
            # Check if already recorded arrival today using cached data
            attendance_records = self._get_cached_attendance()
            today_record = next((r for r in attendance_records if
                               r.get("student_id", "") == student_id and
                               r.get("date", "") == today), None)
            
            if today_record and today_record.get("came_time", ""):
                return False, f"Kelgen waqtıńız {today_record.get('came_time', '')} dep jazıp alındı."
            
            # Record arrival
            token = str(uuid.uuid4())
            success = self.csv_handler.record_attendance(
                student_id, name, group, school, today,
                came_time=current_time, token=token
            )
            
            if success:
                # Invalidate cache to ensure fresh data next time
                self._cache_timestamp = None
                return True, f"Kelgeńiz jazıp alındı! Waqıt: {current_time}"
            else:
                return False, "Qatnas jazıwda qátelik."
                
        except Exception as e:
            logger.error(f"Error recording arrival: {e}")
            return False, "Kelgen waqtın jazıwda qátelik."
    
    def record_departure(self, student_id, name, group, school):
        """Record student departure - OPTIMIZED with caching"""
        try:
            today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
            current_time = datetime.now(TIMEZONE).strftime("%H:%M")
            
            # Check if arrival was recorded using cached data
            attendance_records = self._get_cached_attendance()
            today_record = next((r for r in attendance_records if
                               r.get("student_id", "") == student_id and
                               r.get("date", "") == today), None)
            
            if not today_record or not today_record.get("came_time", ""):
                return False, "Búgingi kelgeńizdi belgilemegensiz."
            
            if today_record.get("left_time", ""):
                return False, f"Ketken waqtıńız {today_record.get('left_time', '')} dep jazıp alındı."
            
            # Calculate time spent and check minimum hours
            came_time_str = today_record.get("came_time", "")
            warning_message = ""
            time_spent_message = ""
            
            if came_time_str:
                try:
                    came_minutes = int(came_time_str.split(':')[0]) * 60 + int(came_time_str.split(':')[1])
                    current_minutes = int(current_time.split(':')[0]) * 60 + int(current_time.split(':')[1])
                    if current_minutes < came_minutes:
                        current_minutes += 24 * 60
                    
                    time_diff_hours = (current_minutes - came_minutes) / 60.0
                    time_diff_minutes = current_minutes - came_minutes
                    
                    if time_diff_hours < MIN_ATTENDANCE_HOURS:
                        warning_message = f"Eskertiw! Siz mektepte {time_diff_hours:.1f} saat boldıńız."
                    
                    time_spent_message = f"\nMektepte boldıńız: {time_diff_minutes // 60} saat {time_diff_minutes % 60} minut"
                except:
                    pass
            
            # Record departure
            success = self.csv_handler.record_attendance(
                student_id, name, group, school, today,
                left_time=current_time
            )
            
            if success:
                # Invalidate cache to ensure fresh data next time
                self._cache_timestamp = None
                message = f"Ketkenińiz jazıp alındı! Waqıt: {current_time}{time_spent_message}"
                if warning_message:
                    message = warning_message + "\n" + message
                return True, message
            else:
                return False, "Ketken waqtın jazıwda qátelik."
                
        except Exception as e:
            logger.error(f"Error recording departure: {e}")
            return False, "Ketken waqtın jazıwda qátelik."
    
    def get_attendance_report(self, teacher_group):
        """Generate attendance report for a group - OPTIMIZED with caching"""
        try:
            today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
            attendance_records = self._get_cached_attendance()
            students = self._get_cached_students()
            
            today_records = [r for r in attendance_records
                           if r.get("date", "") == today and r.get("group", "") == teacher_group]
            
            if not today_records:
                return f"{teacher_group} toparında {today} sánesinde qatnas maǵlıwmatları joq."
            
            report = f"{today} sánesi ushın {teacher_group} toparınıń qatnas maǵlıwmatları:\n"
            
            for record in today_records:
                student_id = record.get("student_id", "")
                student = next((s for s in students if s.get("student_id", "") == student_id), None)
                
                if student:
                    name = student.get("name", "Belgisiz")
                    came_time = record.get("came_time", "-")
                    left_time = record.get("left_time", "-")
                    
                    time_in_school = ""
                    if came_time != "-" and left_time != "-":
                        try:
                            came_minutes = int(came_time.split(':')[0]) * 60 + int(came_time.split(':')[1])
                            left_minutes = int(left_time.split(':')[0]) * 60 + int(left_time.split(':')[1])
                            if left_minutes < came_minutes:
                                left_minutes += 24 * 60
                            total_minutes = left_minutes - came_minutes
                            time_in_school = f" ({total_minutes // 60} saat {total_minutes % 60} minut)"
                        except:
                            time_in_school = " (Waqıt esapda qátelik)"
                    
                    report += f"- {name}:\n  Keldi: {came_time}\n  Ketti: {left_time}{time_in_school}\n"
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating attendance report: {e}")
            return "Qatnas maǵlıwmatların alıwda qátelik."