import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class NewsDatabase:
    def __init__(self, db_name: str):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS news (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        news_id TEXT UNIQUE NOT NULL,
                        title TEXT NOT NULL,
                        publish_date TEXT,
                        url TEXT NOT NULL,
                        detected_at TEXT NOT NULL,
                        category TEXT NOT NULL
                    )
                """)
                conn.commit()
                logger.info("База данных инициализирована")
        except sqlite3.Error as e:
            logger.error(e)
            raise
    
    def news_exists(self, news_id: str) -> bool:
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM news WHERE news_id = ?",
                    (news_id,)
                )
                return cursor.fetchone()[0] > 0
        except sqlite3.Error as e:
            logger.error(e)
            return False
    
    def add_news(self, news_data: Dict) -> bool:
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO news (news_id, title, publish_date, url, detected_at, category)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    news_data['news_id'],
                    news_data['title'],
                    news_data.get('publish_date', ''),
                    news_data['url'],
                    datetime.now().isoformat(),
                    news_data['category']
                ))
                conn.commit()
                logger.info(f"Добавлена новость: {news_data['title'][:50]}...")
                return True
        except sqlite3.IntegrityError:
            logger.debug(f"Новость уже существует: {news_data['news_id']}")
            return False
        except sqlite3.Error as e:
            logger.error(e)
            return False
    
    def get_all_news(self, category: Optional[str] = None) -> List[Dict]:
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                if category:
                    cursor.execute(
                        "SELECT * FROM news WHERE category = ? ORDER BY detected_at DESC",
                        (category,)
                    )
                else:
                    cursor.execute("SELECT * FROM news ORDER BY detected_at DESC")
                
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(e)
            return []
    
    def get_news_count(self, category: Optional[str] = None) -> int:
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                if category:
                    cursor.execute(
                        "SELECT COUNT(*) FROM news WHERE category = ?",
                        (category,)
                    )
                else:
                    cursor.execute("SELECT COUNT(*) FROM news")
                return cursor.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(e)
            return 0
    
    def cleanup_old_news(self, max_count: int):
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM news 
                    WHERE id NOT IN (
                        SELECT id FROM news 
                        ORDER BY detected_at DESC 
                        LIMIT ?
                    )
                """, (max_count,))
                conn.commit()
                deleted = cursor.rowcount
                if deleted > 0:
                    logger.info(f"Удалено {deleted} старых новостей")
        except sqlite3.Error as e:
            logger.error(e)
