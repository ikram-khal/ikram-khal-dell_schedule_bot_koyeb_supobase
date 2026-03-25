"""
Database operations for the Combined Bot (Schedule + Users)
Uses Supabase PostgreSQL — no SQLite, no Google Drive
"""
import logging
import pandas as pd
from typing import Dict

from models.data_models import UserData, BotData
from services.supabase_service import get_supabase

logger = logging.getLogger(__name__)

# Column mapping: Supabase (lowercase) → DataFrame (original case)
_SCHEDULE_COLS = {
    'kun': 'Kun', 'jupliq': 'Jupliq', 'topar': 'Topar',
    'pan': 'Pan', 'oqitiwshi': 'Oqitiwshi', 'kabinet': 'Kabinet',
}
_EXAM_COLS = {
    'kun': 'Kun', 'waqti': 'Waqti', 'topar': 'Topar',
    'pan': 'Pan', 'oqitiwshi': 'Oqitiwshi', 'kabinet': 'Kabinet',
}


def _df_to_rows(df: pd.DataFrame, table_name: str) -> list:
    """Convert DataFrame rows to list of dicts for Supabase insert"""
    rows = []
    is_exam = (table_name == 'exam_schedule')
    for _, row in df.iterrows():
        if is_exam:
            record = {
                'kun': str(row.get('Kun', '') or ''),
                'waqti': str(row.get('Waqti', '') or ''),
                'topar': str(row.get('Topar', '') or ''),
                'pan': str(row.get('Pan', '') or ''),
                'oqitiwshi': str(row.get('Oqitiwshi', '') or ''),
                'kabinet': str(row.get('Kabinet', '') or ''),
            }
        else:
            jupliq = row.get('Jupliq')
            try:
                jupliq = int(jupliq)
            except (ValueError, TypeError):
                jupliq = None
            record = {
                'kun': str(row.get('Kun', '') or ''),
                'jupliq': jupliq,
                'topar': str(row.get('Topar', '') or ''),
                'pan': str(row.get('Pan', '') or ''),
                'oqitiwshi': str(row.get('Oqitiwshi', '') or ''),
                'kabinet': str(row.get('Kabinet', '') or ''),
            }
        rows.append(record)
    return rows


def init_db():
    """Verify Supabase connection is working"""
    try:
        get_supabase().table('users').select('user_id').limit(1).execute()
        logger.info("Database (Supabase) initialized successfully")
    except Exception as e:
        logger.error(f"Database init error: {e}")
        raise


def save_user_to_db(user_id: int, user_data: UserData):
    """Save or update a single user in Supabase"""
    try:
        get_supabase().table('users').upsert({
            'user_id': user_id,
            'role': user_data.role,
            'teacher_name': user_data.teacher_name,
            'group_name': user_data.group,
            'notifications': bool(user_data.notifications),
            'state': user_data.state,
        }).execute()
    except Exception as e:
        logger.error(f"save_user_to_db error for {user_id}: {e}")


def load_users_from_db() -> Dict[int, UserData]:
    """Load all users from Supabase"""
    users = {}
    try:
        res = get_supabase().table('users').select('*').execute()
        for row in (res.data or []):
            ud = UserData()
            ud.role = row.get('role')
            ud.teacher_name = row.get('teacher_name')
            ud.group = row.get('group_name')
            ud.notifications = bool(row.get('notifications', True))
            ud.state = row.get('state')
            users[int(row['user_id'])] = ud
    except Exception as e:
        logger.error(f"load_users_from_db error: {e}")
    return users


def save_to_db(df: pd.DataFrame, table_name: str):
    """Replace entire schedule table in Supabase with DataFrame contents"""
    try:
        client = get_supabase()

        # Clear existing data
        client.table(table_name).delete().neq('id', 0).execute()

        if df.empty:
            return

        rows = _df_to_rows(df, table_name)

        # Batch insert (500 rows per request to stay within limits)
        batch_size = 500
        for i in range(0, len(rows), batch_size):
            client.table(table_name).insert(rows[i:i + batch_size]).execute()

        logger.info(f"Saved {len(rows)} rows to {table_name}")
    except Exception as e:
        logger.error(f"save_to_db error for {table_name}: {e}")
        raise


def get_from_db(table_name: str, bot_data: BotData) -> pd.DataFrame:
    """Get schedule data — from cache first, then Supabase"""
    # Check cache
    if table_name == 'exam_schedule' and bot_data.exam_cache is not None:
        return bot_data.exam_cache
    if table_name in ('original_schedule', 'changes_schedule') and bot_data.schedule_cache is not None:
        return bot_data.schedule_cache

    # Load from Supabase
    try:
        res = get_supabase().table(table_name).select('*').execute()
        data = res.data or []
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        # Remove internal 'id' column
        df = df.drop(columns=['id'], errors='ignore')

        # Rename columns to expected case
        col_map = _EXAM_COLS if table_name == 'exam_schedule' else _SCHEDULE_COLS
        df = df.rename(columns=col_map)

        # Update cache
        if table_name == 'exam_schedule':
            bot_data.exam_cache = df
        else:
            bot_data.schedule_cache = df

        return df
    except Exception as e:
        logger.error(f"get_from_db error for {table_name}: {e}")
        return pd.DataFrame()


def delete_user_from_db(user_id: int):
    """Fully remove a user from the users table in Supabase"""
    try:
        get_supabase().table('users').delete().eq('user_id', user_id).execute()
    except Exception as e:
        logger.error(f"delete_user_from_db error for {user_id}: {e}")


def clear_db(schedule_type: str) -> bool:
    """Clear schedule tables in Supabase and reset bot cache"""
    try:
        client = get_supabase()
        if schedule_type == 'schedule':
            client.table('original_schedule').delete().neq('id', 0).execute()
            client.table('changes_schedule').delete().neq('id', 0).execute()
        else:
            client.table('exam_schedule').delete().neq('id', 0).execute()
        return True
    except Exception as e:
        logger.error(f"clear_db error: {e}")
        return False
