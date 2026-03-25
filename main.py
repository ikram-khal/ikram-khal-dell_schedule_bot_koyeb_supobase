#!/usr/bin/env python3
"""
Combined Telegram Bot - Main Entry Point (Koyeb Deployment)
"""

import sys
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram.ext import ApplicationBuilder

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import BOT_TOKEN, ADMIN_USER_ID
from models.data_models import BotData
from services.supabase_service import init_supabase
from services.location_service import LocationService, AttendanceService
from database.supabase_handler import SupabaseHandler
from database.db_operations import init_db, load_users_from_db, get_from_db
from handlers.message_handlers import MessageHandlers
from handlers.callback_handlers import CallbackHandlers
from handlers.conversation_handlers import ConversationHandlers
from handlers.notification_handler import NotificationHandler
from bot.combined_bot import CombinedBot


# ---- Health Check HTTP Server for Koyeb ----
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Bot is running!')

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

    def log_message(self, format, *args):
        pass


def start_health_server():
    port = int(os.environ.get('PORT', 8000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"Health check server running on port {port}")
    server.serve_forever()
# ---- End Health Check Server ----


def init_bot():
    """Initialize the combined bot"""
    print("Starting Combined Telegram Bot...")

    # Initialize Supabase
    print("Connecting to Supabase...")
    init_supabase()
    init_db()
    print("Supabase ready")

    # Initialize handlers/services
    db_handler = SupabaseHandler()
    location_service = LocationService(db_handler)
    attendance_service = AttendanceService(db_handler)

    # Create bot application
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Initialize bot data
    bot_data = BotData()
    app.bot_data['bot_data'] = bot_data

    # Load users
    print("Loading users...")
    bot_data.users = load_users_from_db()
    bot_data.subscribed_users = {uid for uid, ud in bot_data.users.items() if ud.notifications}
    print(f"Loaded {len(bot_data.users)} users")

    # Load schedules into cache
    print("Loading schedules from Supabase...")
    for table in ('original_schedule', 'changes_schedule', 'exam_schedule'):
        try:
            df = get_from_db(table, bot_data)
            if not df.empty:
                print(f"Loaded {table}: {len(df)} rows")
            else:
                print(f"{table}: empty (no data yet)")
        except Exception as e:
            print(f"Error loading {table}: {e}")

    # Initialize all handlers
    conversation_handlers = ConversationHandlers(db_handler, location_service, attendance_service)
    notification_handler = NotificationHandler()
    message_handlers = MessageHandlers(db_handler, attendance_service, conversation_handlers, bot_data, notification_handler)
    callback_handlers = CallbackHandlers(db_handler, attendance_service, conversation_handlers)

    combined_bot = CombinedBot(
        db_handler, location_service, attendance_service,
        conversation_handlers, message_handlers, callback_handlers, notification_handler
    )
    combined_bot.setup_handlers(app)

    print("All handlers registered successfully")
    return app


def main():
    try:
        print("=" * 50)
        print("COMBINED TELEGRAM BOT v2.0 (Supabase)")
        print("Attendance + Schedule Management")
        print("=" * 50)

        health_thread = threading.Thread(target=start_health_server, daemon=True)
        health_thread.start()

        app = init_bot()

        print("Bot is ready and running!")
        print("-" * 50)

        app.run_polling(
            poll_interval=0.1,
            timeout=10,
            drop_pending_updates=True,
        )

    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Error running bot: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
