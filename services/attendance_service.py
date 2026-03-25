"""
Attendance service for managing student attendance records
"""
from datetime import datetime, timedelta
from typing import Tuple, List, Dict, Any
import logging

from config.settings import TIMEZONE
from database.csv_handler import CSVHandler
from utils.helpers import format_attendance_report

logger = logging.getLogger(__name__)

class AttendanceService:
    def __init__(self, csv_handler: CSVHandler):
        self.csv_handler = csv_handler
    
    def record_arrival(self, student_id: str, student_name: str, group: str, school: str) -> Tuple[bool, str]:
        """
        Record student arrival
        Returns (success, message)
        """
        try:
            current_time = datetime.now(TIMEZONE)
            
            # Record attendance in CSV
            success = self.csv_handler.add_attendance_record(
                student_id=student_id,
                student_name=student_name,
                group=group,
                school=school,
                action="Keldim",
                timestamp=current_time
            )
            
            if success:
                time_str = current_time.strftime("%H:%M")
                message = f"✅ {student_name}, siz {time_str} da mektepke kelgeniñiz belgilenip qoyıldı!"
                logger.info(f"Recorded arrival for student {student_id} ({student_name}) at {time_str}")
                return True, message
            else:
                message = "❌ Qatnastı belgilew barısında qátelik júz berdi. Qayta urınıp kóriñ."
                logger.error(f"Failed to record arrival for student {student_id}")
                return False, message
                
        except Exception as e:
            logger.error(f"Error recording arrival for student {student_id}: {str(e)}")
            return False, "❌ Texnikalıq qátelik júz berdi. Qayta urınıp kóriñ."
    
    def record_departure(self, student_id: str, student_name: str, group: str, school: str) -> Tuple[bool, str]:
        """
        Record student departure
        Returns (success, message)
        """
        try:
            current_time = datetime.now(TIMEZONE)
            
            # Record attendance in CSV
            success = self.csv_handler.add_attendance_record(
                student_id=student_id,
                student_name=student_name,
                group=group,
                school=school,
                action="Kettim",
                timestamp=current_time
            )
            
            if success:
                time_str = current_time.strftime("%H:%M")
                message = f"✅ {student_name}, siz {time_str} da mektepten shıqqanıñız belgilenip qoyıldı!"
                logger.info(f"Recorded departure for student {student_id} ({student_name}) at {time_str}")
                return True, message
            else:
                message = "❌ Qatnastı belgilew barısında qátelik júz berdi. Qayta urınıp kóriñ."
                logger.error(f"Failed to record departure for student {student_id}")
                return False, message
                
        except Exception as e:
            logger.error(f"Error recording departure for student {student_id}: {str(e)}")
            return False, "❌ Texnikalıq qátelik júz berdi. Qayta urınıp kóriñ."
    
    def get_attendance_report(self, group: str) -> str:
        """
        Get attendance report for a specific group
        """
        try:
            # Get attendance records from CSV
            attendance_records = self.csv_handler.get_attendance_records_by_group(group)
            
            if not attendance_records:
                return f"📊 **{group} toparı ushın qatnastı esabatı**\n\nBúgin ele qatnastı maǵlıwmatı joq."
            
            # Format the report
            report = self._format_attendance_report(attendance_records, group)
            logger.info(f"Generated attendance report for group {group}")
            return report
            
        except Exception as e:
            logger.error(f"Error generating attendance report for group {group}: {str(e)}")
            return f"❌ {group} toparı ushın qatnastı esabatın alıwda qátelik júz berdi."
    
    def _format_attendance_report(self, records: List[Dict[str, Any]], group: str) -> str:
        """
        Format attendance records into a readable report
        """
        if not records:
            return f"📊 **{group} toparı ushın qatnastı esabatı**\n\nBúgin ele qatnastı maǵlıwmatı joq."

        # Group records by date
        today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
        today_records = []
        all_time_records = []

        for record in records:
            record_date = record.get('date', '')
            if record_date == today:
                today_records.append(record)
            all_time_records.append(record)

        # Build report
        report = f"📊 **{group} toparı ushın qatnastı esabatı**\n\n"

        # Today's attendance - group by student
        if today_records:
            report += "🗓 **Búgingi qatnastı:**\n"
            # Group records by student_id
            student_records = {}
            for record in today_records:
                student_id = record.get('student_id', '')
                if student_id not in student_records:
                    student_records[student_id] = {
                        'name': record.get('name', 'Unknown'),
                        'school': record.get('school', 'Unknown'),
                        'came_time': record.get('came_time', ''),
                        'left_time': record.get('left_time', '')
                    }
                else:
                    # Update times if not set
                    if not student_records[student_id]['came_time']:
                        student_records[student_id]['came_time'] = record.get('came_time', '')
                    if not student_records[student_id]['left_time']:
                        student_records[student_id]['left_time'] = record.get('left_time', '')

            for student_data in student_records.values():
                name = student_data['name']
                came_time = student_data['came_time']
                left_time = student_data['left_time']

                # Format times
                came_str = came_time if came_time else '-'
                left_str = left_time if left_time else '-'

                # Calculate duration if both times exist
                duration_str = ''
                if came_time and left_time:
                    try:
                        came_dt = datetime.strptime(came_time, "%H:%M")
                        left_dt = datetime.strptime(left_time, "%H:%M")
                        if left_dt >= came_dt:
                            duration = left_dt - came_dt
                            hours = duration.seconds // 3600
                            minutes = (duration.seconds % 3600) // 60
                            duration_str = f" ({hours} saat {minutes} minut)"
                        else:
                            # Handle case where left time is next day
                            duration = (left_dt + timedelta(days=1)) - came_dt
                            hours = duration.seconds // 3600
                            minutes = (duration.seconds % 3600) // 60
                            duration_str = f" ({hours} saat {minutes} minut)"
                    except ValueError:
                        duration_str = ''

                report += f"{name}: Keldi: {came_str} / Ketti: {left_str}{duration_str}\n"
            report += "\n"
        else:
            report += "🗓 **Búgingi qatnastı:** Ele maǵlıwmat joq\n\n"

        # Summary statistics
        total_students = len(set(record.get('student_id', '') for record in all_time_records))
        total_records = len(all_time_records)

        report += f"📈 **Statistika:**\n"
        report += f"👥 Jámi studentler: {total_students}\n"
        report += f"📝 Jámi qatnastı jazıwları: {total_records}\n"

        return report
    
    def get_student_attendance_history(self, student_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get attendance history for a specific student
        """
        try:
            records = self.csv_handler.get_student_attendance_history(student_id, days)
            logger.info(f"Retrieved {len(records)} attendance records for student {student_id}")
            return records
        except Exception as e:
            logger.error(f"Error getting attendance history for student {student_id}: {str(e)}")
            return []
    
    def get_group_statistics(self, group: str) -> Dict[str, Any]:
        """
        Get attendance statistics for a group
        """
        try:
            records = self.csv_handler.get_attendance_records_by_group(group)
            
            if not records:
                return {
                    'total_students': 0,
                    'total_records': 0,
                    'today_arrivals': 0,
                    'today_departures': 0
                }
            
            today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
            today_records = [r for r in records if r.get('date', '') == today]
            
            stats = {
                'total_students': len(set(record.get('student_id', '') for record in records)),
                'total_records': len(records),
                'today_arrivals': len([r for r in today_records if r.get('action') == 'Keldim']),
                'today_departures': len([r for r in today_records if r.get('action') == 'Kettim'])
            }
            
            logger.info(f"Generated statistics for group {group}: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error generating statistics for group {group}: {str(e)}")
            return {
                'total_students': 0,
                'total_records': 0,
                'today_arrivals': 0,
                'today_departures': 0
            }