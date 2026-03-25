#!/usr/bin/env python3
"""
Combined Telegram Bot - Main Entry Point (Koyeb Deployment Version)
"""

import asyncio
import sys
import os
import threading
import pandas as pd
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ApplicationBuilder

# Add the current directory to Python path to allow imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import configuration
from config.settings import BOT_TOKEN, ADMIN_USER_ID, DATA_DIR, DRIVE_FOLDER_ID

# Import models
from models.data_models import BotData

# Import services
from services.drive_service import init_drive, download_latest_from_drive
from services.location_service import LocationService, AttendanceService

# Import database operations
from database.db_operations import init_db, save_to_db, load_users_from_db
from database.csv_handler import CSVHandler

# Import handlers
from handlers.message_handlers import MessageHandlers
from handlers.callback_handlers import CallbackHandlers
from handlers.conversation_handlers import ConversationHandlers
from handlers.notification_handler import NotificationHandler

# Import bot classes
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
        pass  # Suppress logs

def start_health_server():
    port = int(os.environ.get('PORT', 8000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"Health check server running on port {port}")
    server.serve_forever()
# ---- End Health Check Server ----


def init_bot():
    """Initialize the combined bot with all necessary components"""
    print("Starting Combined Telegram Bot...")
    
    # Initialize Google Drive service
    print("Initializing Google Drive service...")
    drive_service, credentials = init_drive()
    if drive_service:
        print("Google Drive service initialized successfully")
    else:
        print("Google Drive service not available (credentials not set)")
    
    # Initialize database
    print("Initializing database...")
    init_db()
    print("Database initialized successfully")

    # Initialize users sheets service
    print("Initializing users sheets service...")
    from database.db_operations import init_users_sheets_service
    init_users_sheets_service(credentials)
    print("Users sheets service initialized successfully")
    
    # Initialize CSV handler
    print("Initializing CSV handler...")
    csv_handler = CSVHandler(drive_service, credentials)
    print("CSV handler initialized successfully")
    
    # Create bot application
    print("Creating bot application...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Initialize bot data
    bot_data = BotData()
    bot_data.drive_service = drive_service
    bot_data.csv_handler = csv_handler
    app.bot_data['bot_data'] = bot_data
    
    # Load users from database
    print("Loading users from database...")
    bot_data.users = load_users_from_db(drive_service)
    bot_data.subscribed_users = {uid for uid, ud in bot_data.users.items() if ud.notifications}
    print(f"Loaded {len(bot_data.users)} users from database")
    
    # Download and load existing schedules from Drive
    print("Loading existing schedules from Google Drive...")
    schedule_files = [
        ("keste_bot_orig", "original_schedule"),
        ("keste_bot_ozgeris", "changes_schedule"),
        ("imtixan_keste", "exam_schedule")
    ]
    
    for prefix, table in schedule_files:
        try:
            file_path = download_latest_from_drive(drive_service, DRIVE_FOLDER_ID, prefix)
            if file_path:
                print(f"Downloaded {prefix} from Drive")
                df = pd.read_excel(file_path, sheet_name="keste", engine="openpyxl")
                save_to_db(df, table, drive_service)
                
                # Update cache and file paths
                if table == "exam_schedule":
                    bot_data.exam_cache = df
                    bot_data.exam_file = file_path
                elif table == "changes_schedule":
                    bot_data.last_schedule_file = file_path
                    bot_data.schedule_cache = df
                else:  # original_schedule
                    bot_data.original_schedule_file = file_path
                    bot_data.last_schedule_file = file_path
                    bot_data.schedule_cache = df
                
                print(f"Loaded {table} with {len(df)} records")
            else:
                print(f"No {prefix} file found in Drive")
        except Exception as e:
            print(f"Error loading {prefix}: {e}")
    
    # Initialize services
    location_service = LocationService(csv_handler)
    attendance_service = AttendanceService(csv_handler)
    
    # Initialize handlers
    conversation_handlers = ConversationHandlers(csv_handler, location_service, attendance_service)
    notification_handler = NotificationHandler()
    message_handlers = MessageHandlers(csv_handler, attendance_service, conversation_handlers, bot_data, notification_handler)
    callback_handlers = CallbackHandlers(csv_handler, attendance_service, conversation_handlers)
    
    # Initialize combined bot
    combined_bot = CombinedBot(
        csv_handler, location_service, attendance_service,
        conversation_handlers, message_handlers, callback_handlers, notification_handler
    )
    
    # Setup handlers
    combined_bot.setup_handlers(app)
    
    print("All handlers registered successfully")
    
    return app


def main():
    """Main function to run the bot"""
    try:
        print("=" * 50)
        print("COMBINED TELEGRAM BOT v1.0")
        print("Attendance + Schedule Management")
        print("=" * 50)

        # Start health check server in background thread (for Koyeb)
        health_thread = threading.Thread(target=start_health_server, daemon=True)
        health_thread.start()

        # Initialize bot
        app = init_bot()

        print("Bot is ready and running!")
        print("Users can now interact with the bot")
        print("Press Ctrl+C to stop the bot")
        print("-" * 50)

        # run_polling creates and manages its own event loop
        app.run_polling(
            poll_interval=0.1,
            timeout=10,
            drop_pending_updates=True
        )

    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Error running bot: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

