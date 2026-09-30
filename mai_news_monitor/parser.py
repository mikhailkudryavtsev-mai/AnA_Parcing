import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import logging
import re
import hashlib

from config import BASE_URL, REQUEST_TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)


class MaiNewsParser:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        })
    
    def fetch_page(self, url: str) -> Optional[str]:
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return response.text
        except requests.RequestException as e:
            logger.error(f"Ошибка при получении страницы {url}: {e}")
            return None
    
    def parse_news_list(self, html: str, category: str) -> List[Dict]:
        news_list = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            cards = soup.select("div.col-sm-6.col-lg-6.mb-3.mb-lg-5")
            
            if not cards:
                link_tags = soup.select("a.card")
            else:
                link_tags = [card.select_one("a.card") for card in cards]
            
            for link_tag in link_tags:
                if not link_tag:
                    continue
                    
                try:
                    news_data = self._extract_news_data(link_tag, category)
                    if news_data:
                        news_list.append(news_data)
                except Exception as e:
                    logger.warning(f"Ошибка при парсинге новости: {e}")
                    continue
            
            logger.info(f"Найдено {len(news_list)} новостей в категории {category}")
            return news_list
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге списка новостей: {e}")
            return []
    
    def _extract_news_data(self, link_tag, category: str) -> Optional[Dict]:
        try:
            href = link_tag.get('href', '')
            if not href:
                return None
            card = link_tag.find_parent(['div'])
            title = ""
            
            if card:
                h5 = card.select_one("div.card-body h5, h5.card-title, h5")
                if h5:
                    title = h5.get_text(strip=True)

            if not title:
                title = link_tag.get_text(strip=True)
                
            if len(title) < 10:
                return None

            if href.startswith('/'):
                full_url = BASE_URL + href
            elif href.startswith('http'):
                full_url = href
            else:
                base = BASE_URL.rstrip('/') + "/press/news/"
                full_url = base + href.lstrip('/')

            news_id = self._extract_news_id(full_url)
            if not news_id:
                news_id = hashlib.md5(full_url.encode('utf-8')).hexdigest()

            publish_date = ''
            if card:
                badge = card.select_one("span.badge")
                if badge:
                    publish_date = badge.get_text(strip=True)
                else:
                    date_elem = card.find(['time', 'span', 'div'], 
                                         class_=re.compile(r'date|time|published', re.I))
                    if date_elem:
                        publish_date = date_elem.get('datetime', date_elem.get_text(strip=True))
            
            return {
                'news_id': news_id,
                'title': title,
                'publish_date': publish_date,
                'url': full_url,
                'category': category
            }
            
        except Exception as e:
            logger.debug(f"Не удалось извлечь данные новости: {e}")
            return None
    
    def _extract_news_id(self, url: str) -> Optional[str]:
        match = re.search(r'ID=(\d+)', url, re.I)
        if match:
            return match.group(1)
        
        match = re.search(r'/(\d+)/?$', url)
        if match:
            return match.group(1)
        
        match = re.search(r'/([^/]+)/?$', url)
        if match:
            slug = match.group(1)
            if slug not in ['news', 'press', '']:
                return slug
                
        return None
    
    def get_latest_news(self, category_url: str, category_name: str) -> List[Dict]:
        full_url = BASE_URL + category_url
        logger.info(f"Парсинг категории {category_name}: {full_url}")
        
        html = self.fetch_page(full_url)
        if not html:
            return []
        
        return self.parse_news_list(html, category_name)
