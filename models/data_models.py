"""
Data models for the Combined Bot (Attendance + Schedule)
"""
from typing import Dict, Set
import pandas as pd


class UserData:
    """User data model for storing user information"""
    def __init__(self):
        self.role: str = None
        self.teacher_name: str = None
        self.group: str = None
        self.notifications: bool = True
        self.state: str = None


class BotData:
    """Bot data model for storing bot-wide information"""
    def __init__(self):
        self.users: Dict[int, UserData] = {}
        self.subscribed_users: Set[int] = set()
        self.schedule_cache: pd.DataFrame = None
        self.exam_cache: pd.DataFrame = None
