import time
import logging
import signal
import sys
from datetime import datetime
from typing import Dict

from config import NEWS_CATEGORIES, DATABASE_NAME, CHECK_INTERVAL, MAX_NEWS_COUNT
from database import NewsDatabase
from parser import MaiNewsParser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('news_monitor.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class NewsMonitor:
    def __init__(self, check_interval: int):
        self.db = NewsDatabase(DATABASE_NAME)
        self.parser = MaiNewsParser()
        self.running = True
        self.check_interval = check_interval
        
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        logger.info("Получен сигнал завершения. Остановка мониторинга...")
        self.running = False
    
    def check_category(self, category_name: str, category_url: str) -> int:
        logger.info(f"Проверка категории: {category_name}")
        
        news_list = self.parser.get_latest_news(category_url, category_name)
        new_count = 0
        
        for news in news_list:
            if not self.db.news_exists(news['news_id']):
                if self.db.add_news(news):
                    new_count += 1
                    logger.info(f"Новая новость: {news['title'][:50]}...")
        
        if new_count > 0:
            logger.info(f"Добавлено {new_count} новых новостей в категории {category_name}")
        else:
            logger.info(f"Новых новостей в категории {category_name} не найдено")
        
        return new_count
    
    def check_all_categories(self) -> Dict[str, int]:
        results = {}
        total_new = 0
        
        for category_name, category_url in NEWS_CATEGORIES.items():
            try:
                new_count = self.check_category(category_name, category_url)
                results[category_name] = new_count
                total_new += new_count
            except Exception as e:
                logger.error(f"Ошибка при проверке категории {category_name}: {e}")
                results[category_name] = 0
        
        self.db.cleanup_old_news(MAX_NEWS_COUNT)
        
        logger.info(f"Всего добавлено {total_new} новых новостей")
        return results
    
    def run_once(self):
        logger.info("=" * 60)
        logger.info(f"Начало проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        results = self.check_all_categories()
        
        logger.info(f"Статистика по категориям: {results}")
        logger.info(f"Всего новостей в БД: {self.db.get_news_count()}")
        logger.info("=" * 60)
    
    def run_continuous(self):
        logger.info("Запуск непрерывного мониторинга новостей")
        logger.info(f"Интервал проверки: {self.check_interval} секунд")
        logger.info(f"Количество категорий: {len(NEWS_CATEGORIES)}")
        
        while self.running:
            try:
                self.run_once()
                
                if self.running:
                    logger.info(f"Следующая проверка через {self.check_interval} секунд...")
                    for _ in range(self.check_interval):
                        if not self.running:
                            break
                        time.sleep(1)
                        
            except KeyboardInterrupt:
                logger.info("Мониторинг остановлен пользователем")
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга: {e}")
                time.sleep(60)
        
        logger.info("Мониторинг завершен")


def print_stats(db: NewsDatabase):
    print("\n" + "=" * 60)
    print("СТАТИСТИКА БАЗЫ ДАННЫХ")
    print("=" * 60)
    print(f"Всего новостей: {db.get_news_count()}")
    
    for category in NEWS_CATEGORIES.keys():
        count = db.get_news_count(category)
        print(f"  - {category}: {count} новостей")
    
    print("=" * 60 + "\n")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Мониторинг новостей сайта МАИ')
    parser.add_argument('--once', action='store_true', help='Выполнить одну проверку')
    parser.add_argument('--stats', action='store_true', help='Показать статистику')
    parser.add_argument('--interval', type=int, default=CHECK_INTERVAL, 
                       help=f'Интервал проверки в секундах (по умолчанию: {CHECK_INTERVAL})')
    
    args = parser.parse_args()
    monitor = NewsMonitor(check_interval=args.interval)
    
    if args.stats:
        print_stats(monitor.db)
        return
    
    if args.once:
        monitor.run_once()
    else:
        monitor.run_continuous()


if __name__ == "__main__":
    main()
