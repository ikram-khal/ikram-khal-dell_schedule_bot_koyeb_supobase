"""
Combined Bot class that merges Attendance and Schedule functionality
"""
import asyncio
import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ConversationHandler,
)

from config.settings import (
    BOT_TOKEN, ADMIN_USER_ID,
    TEACHER_NAME, TEACHER_COURSE, TEACHER_GROUP, TEACHER_SCHOOL, TEACHER_LOCATION,
    STUDENT_NAME, STUDENT_COURSE, STUDENT_GROUP, STUDENT_SCHOOL, STUDENT_LOCATION,
)

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.WARNING,
)
logger = logging.getLogger(__name__)


class CombinedBot:
    def __init__(self, db_handler, location_service, attendance_service,
                 conversation_handlers, message_handlers, callback_handlers, notification_handler):
        self.token = BOT_TOKEN
        self.admin_user_id = ADMIN_USER_ID

        if not self.token or not self.admin_user_id:
            raise ValueError("BOT_TOKEN or ADMIN_USER_ID not set")

        self.db_handler = db_handler
        self.location_service = location_service
        self.attendance_service = attendance_service
        self.conversation_handlers = conversation_handlers
        self.message_handlers = message_handlers
        self.callback_handlers = callback_handlers
        self.notification_handler = notification_handler

    def setup_handlers(self, app):
        """Setup all bot handlers"""

        teacher_conv = ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex("^Oqıtıwshı$"), self.conversation_handlers.teacher_flow_start),
                CallbackQueryHandler(self.callback_handlers.handle_callback_query, pattern="^teacher$"),
            ],
            states={
                TEACHER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.conversation_handlers.teacher_name)],
                TEACHER_COURSE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.conversation_handlers.teacher_course),
                    CallbackQueryHandler(self.callback_handlers.handle_callback_query, pattern="^course_"),
                ],
                TEACHER_GROUP: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.conversation_handlers.teacher_group),
                    CallbackQueryHandler(self.callback_handlers.handle_callback_query, pattern="^group_"),
                ],
                TEACHER_SCHOOL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.conversation_handlers.teacher_school),
                    CallbackQueryHandler(self.callback_handlers.handle_callback_query, pattern="^school_"),
                ],
                TEACHER_LOCATION: [
                    MessageHandler(filters.LOCATION & ~filters.FORWARDED, self.conversation_handlers.teacher_location)
                ],
            },
            fallbacks=[CommandHandler("cancel", self.message_handlers.cancel)],
            per_user=True,
            per_chat=True,
        )

        student_conv = ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex("^Student$"), self.conversation_handlers.student_flow_start),
                CallbackQueryHandler(self.callback_handlers.handle_callback_query, pattern="^student$"),
            ],
            states={
                STUDENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.conversation_handlers.student_name)],
                STUDENT_COURSE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.conversation_handlers.student_course),
                    CallbackQueryHandler(self.callback_handlers.handle_callback_query, pattern="^course_"),
                ],
                STUDENT_GROUP: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.conversation_handlers.student_group),
                    CallbackQueryHandler(self.callback_handlers.handle_callback_query, pattern="^group_"),
                ],
                STUDENT_SCHOOL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.conversation_handlers.student_school),
                    CallbackQueryHandler(self.callback_handlers.handle_callback_query, pattern="^school_"),
                ],
            },
            fallbacks=[CommandHandler("cancel", self.message_handlers.cancel)],
            per_user=True,
            per_chat=True,
        )

        update_coords_conv = ConversationHandler(
            entry_points=[
                MessageHandler(
                    filters.Regex("^Mektep koordinatların jańalaw$") &
                    filters.User(user_id=int(self.admin_user_id)),
                    self.message_handlers.update_school_coordinates,
                ),
                CallbackQueryHandler(self.callback_handlers.handle_callback_query, pattern="^update_coordinates$"),
            ],
            states={
                TEACHER_LOCATION: [
                    MessageHandler(filters.LOCATION & ~filters.FORWARDED, self.conversation_handlers.teacher_location)
                ],
            },
            fallbacks=[CommandHandler("cancel", self.message_handlers.cancel)],
            per_user=True,
            per_chat=True,
        )

        attendance_conv = ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex("^(Keldim|Kettim)$"), self.conversation_handlers.handle_attendance_action),
                CallbackQueryHandler(self.callback_handlers.handle_callback_query, pattern="^(came|left)$"),
            ],
            states={
                STUDENT_LOCATION: [
                    MessageHandler(filters.LOCATION & ~filters.FORWARDED, self.conversation_handlers.handle_student_location)
                ],
            },
            fallbacks=[CommandHandler("cancel", self.message_handlers.cancel)],
            per_user=True,
            per_chat=True,
        )

        app.add_handler(CommandHandler("start", self.message_handlers.start))
        app.add_handler(CommandHandler("reset", self.message_handlers.reset))
        app.add_handler(CommandHandler("notify_users_on", self.message_handlers.notify_users_on))
        app.add_handler(CommandHandler("notify_users_off", self.message_handlers.notify_users_off))

        app.add_handler(teacher_conv)
        app.add_handler(student_conv)
        app.add_handler(update_coords_conv)
        app.add_handler(attendance_conv)

        app.add_handler(MessageHandler(
            filters.Regex("^Qatnastı tekseriw$") & filters.User(user_id=int(self.admin_user_id)),
            self.message_handlers.check_attendance,
        ))

        app.add_handler(MessageHandler(filters.Document.ALL, self.message_handlers.handle_file))
        app.add_handler(MessageHandler(filters.LOCATION & ~filters.FORWARDED, self.message_handlers.handle_location))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handlers.handle_message))
        app.add_handler(MessageHandler(filters.LOCATION & filters.FORWARDED, self.message_handlers.handle_restricted_location))
        app.add_handler(CallbackQueryHandler(self.callback_handlers.handle_callback_query))
        app.add_handler(MessageHandler(filters.ALL, self.message_handlers.handle_invalid_input))
        app.add_error_handler(self.message_handlers.error_handler)
