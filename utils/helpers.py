"""
Utility functions for the Combined Telegram Bot
"""
import pandas as pd
from datetime import datetime, timedelta
import pytz
from config.settings import DAYS_OF_WEEK, PAIR_TIMES


def parse_groups(group_str: str) -> list:
    """Parse group string into list of groups"""
    return group_str.split('-') if isinstance(group_str, str) and group_str.strip() else [str(group_str)]


def get_current_date() -> str:
    """Get current date in DD.MM.YYYY format"""
    return datetime.now(pytz.timezone('Asia/Tashkent')).strftime("%d.%m.%Y")


def get_tomorrow_date() -> str:
    """Get tomorrow's date in DD.MM.YYYY format"""
    return (datetime.now(pytz.timezone('Asia/Tashkent')) + timedelta(days=1)).strftime("%d.%m.%Y")


def get_current_day() -> str:
    """Get current day name"""
    today = datetime.now(pytz.timezone('Asia/Tashkent')).weekday()
    return DAYS_OF_WEEK[today] if today < 6 else "SHEMBI"


def get_tomorrow_day() -> str:
    """Get tomorrow's day name"""
    tomorrow = (datetime.now(pytz.timezone('Asia/Tashkent')) + timedelta(days=1)).weekday()
    return DAYS_OF_WEEK[tomorrow] if tomorrow < 6 else "SHEMBI"


def get_current_week_dates() -> list:
    """Get list of dates for current week"""
    uzb_tz = pytz.timezone('Asia/Tashkent')
    today = datetime.now(uzb_tz)
    start_of_week = today - timedelta(days=today.weekday())
    return [(start_of_week + timedelta(days=i)).strftime("%d.%m.%Y") for i in range(7)]


def format_schedule(df: pd.DataFrame, role: str) -> str:
    """Format schedule DataFrame into readable message"""
    df = df.copy()
    df["Kun"] = pd.Categorical(df["Kun"], categories=DAYS_OF_WEEK, ordered=True)
    df = df.sort_values(["Kun", "Jupliq"])
    message = ""
    current_day = None
    
    for _, row in df.iterrows():
        kun = str(row["Kun"]).capitalize()
        if row["Kun"] != current_day:
            if current_day:
                message += "\n============\n\n"
            message += f"📅 **{kun}**\n\n"
            current_day = row["Kun"]

        pair_time = PAIR_TIMES.get(row["Jupliq"], "Waqıt kórsetilmegen")
        pan = str(row['Pan']).capitalize()

        if role == "Oqıtıwshı":
            message += (
                f"🕒 {row['Jupliq']}-Jupliq, {pair_time}\n"
                f"👤 Topar: {row['Topar']}\n"
                f"📚 Pán: {pan}\n"
                f"🚪 Kabinet: {row['Kabinet']}\n"
                "----------\n"
            )
        else:
            teacher = str(row['Oqitiwshi']).title()
            message += (
                f"🕒 {row['Jupliq']}-Jupliq, {pair_time}\n"
                f"📚 Pán: {pan}\n"
                f"👤 Oqitiwshi: {teacher}\n"
                f"🚪 Kabinet: {row['Kabinet']}\n"
                "----------\n"
            )
    
    return message or "Sabaq joq"


def format_exam_schedule(df: pd.DataFrame, role: str) -> str:
    """Format exam schedule DataFrame into readable message"""
    df = df.copy()
    df["Kun"] = pd.to_datetime(df["Kun"], format="%d.%m.%Y")
    df = df.sort_values(["Kun", "Waqti"])
    df["Kun"] = df["Kun"].dt.strftime("%d.%m.%Y")
    message = ""
    current_date = None
    
    for _, row in df.iterrows():
        if row["Kun"] != current_date:
            if current_date:
                message += "\n============\n\n"
            message += f"📅 **{row['Kun']}**\n\n"
            current_date = row["Kun"]

        pan = str(row['Pan']).capitalize()

        if role == "Oqıtıwshı":
            message += (
                f"🕒 Waqti: {row['Waqti']}\n"
                f"👤 Topar: {row['Topar']}\n"
                f"📚 Pán: {pan}\n"
                f"🚪 Kabinet: {row['Kabinet']}\n"
                "----------\n"
            )
        else:
            teacher = str(row['Oqitiwshi']).title()
            message += (
                f"🕒 Waqti: {row['Waqti']}\n"
                f"📚 Pán: {pan}\n"
                f"👤 Oqitiwshi: {teacher}\n"
                f"🚪 Kabinet: {row['Kabinet']}\n"
                "----------\n"
            )
    
    return message or "Imtixan joq"


def check_excel_file(file_path: str, schedule_type: str) -> str:
    """Check if Excel file has correct format and columns"""
    column_configs = {
        "schedule": {
            "required": ["Kun", "Jupliq", "Topar", "Pan", "Oqitiwshi", "Kabinet"],
            "aliases": {
                "Jupliq": ["Jupliq", "Пара", "Lesson"],
                "Kun": ["Kun", "Kún", "Day"],
                "Topar": ["Topar", "Group"],
                "Pan": ["Pan", "Pán", "Subject"],
                "Oqitiwshi": ["Oqitiwshi", "Oqtıwshı", "Teacher"],
                "Kabinet": ["Kabinet", "Room"]
            }
        },
        "exam": {
            "required": ["Kun", "Waqti", "Topar", "Pan", "Oqitiwshi", "Kabinet"],
            "aliases": {
                "Waqti": ["Waqti", "Time"],
                "Kun": ["Kun", "Date"],
                "Topar": ["Topar", "Group"],
                "Pan": ["Pan", "Subject"],
                "Oqitiwshi": ["Oqitiwshi", "Oqtıwshı", "Teacher"],
                "Kabinet": ["Kabinet", "Room"]
            }
        }
    }
    
    config = column_configs[schedule_type]
    df = pd.read_excel(file_path, sheet_name="keste", engine="openpyxl")
    missing_cols = []
    rename_dict = {}
    
    for required_col in config["required"]:
        found = False
        for alias in config["aliases"][required_col]:
            if alias in df.columns:
                rename_dict[alias] = required_col
                found = True
                break
        if not found:
            missing_cols.append(required_col)
    
    if missing_cols:
        return f"Baǵanalar kemis: {', '.join(missing_cols)}"
    
    df.rename(columns=rename_dict, inplace=True)
    if schedule_type == "exam":
        try:
            df["Kun"] = pd.to_datetime(df["Kun"], format="%d.%m.%Y").dt.strftime("%d.%m.%Y")
            df["Waqti"] = df["Waqti"].apply(
                lambda x: pd.to_datetime(x, format="%H:%M:%S").strftime("%H:%M")
                if len(str(x).split(":")) == 3 else x
            )
        except Exception:
            return "Fayl formatında qátelik: Kun (DD.MM.YYYY) yamasa Waqti (HH:MM) durıs emes."
    
    df.to_excel(file_path, sheet_name="keste", index=False, engine="openpyxl")
    return "OK"


def format_attendance_report(attendance_data: list, group: str) -> str:
    """Format attendance data into readable report"""
    if not attendance_data:
        return f"Topar {group} ushın qatnastı maǵlıwmatı tabılmadı."
    
    message = f"📊 **{group} toparı ushın qatnastı esabatı**\n\n"
    
    # Group by date
    dates = {}
    for record in attendance_data:
        date = record.get('date', 'Unknown')
        if date not in dates:
            dates[date] = []
        dates[date].append(record)
    
    for date, records in sorted(dates.items()):
        message += f"📅 **{date}**\n"
        for record in records:
            name = record.get('name', 'Unknown')
            action = record.get('action', 'Unknown')
            time = record.get('time', 'Unknown')
            message += f"👤 {name}: {action} - {time}\n"
        message += "\n"
    
    return message


def validate_location_distance(user_lat: float, user_lon: float, school_lat: float, school_lon: float, max_distance: float = 100) -> tuple:
    """
    Validate if user location is within acceptable distance from school
    Returns (is_valid, distance_in_meters)
    """
    from geopy.distance import geodesic
    
    user_location = (user_lat, user_lon)
    school_location = (school_lat, school_lon)
    
    distance = geodesic(user_location, school_location).meters
    is_valid = distance <= max_distance
    
    return is_valid, distance


def format_distance_message(distance: float, is_valid: bool) -> str:
    """Format distance validation message"""
    if distance < 1000:
        distance_str = f"{distance:.1f} metr"
    else:
        distance_str = f"{distance/1000:.2f} kilometr"
    
    if is_valid:
        return f"✅ Siz mektepten {distance_str} aralıqta tursız. Qatnastı belgilenip qoyıldı!"
    else:
        return f"❌ Siz mektepten {distance_str} aralıqta tursız. Bu júdá alıs! Mektep territoriyasına jaqınlasıń."