"""
Supabase client singleton for the Combined Bot
"""
from supabase import create_client, Client
from config.settings import SUPABASE_URL, SUPABASE_KEY

_client: Client = None


def get_supabase() -> Client:
    """Get or create the Supabase client (singleton)"""
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def init_supabase():
    """Initialize Supabase connection and verify it works"""
    try:
        client = get_supabase()
        # Verify connection by checking users table exists
        client.table('users').select('user_id').limit(1).execute()
        print("Supabase connected successfully")
        return True
    except Exception as e:
        print(f"Supabase connection error: {e}")
        return False
