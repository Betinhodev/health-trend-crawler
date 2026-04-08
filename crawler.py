#!/usr/bin/env python3
"""
Health Trend Crawler
Crawls news sites via Google News RSS and direct scraping to find
health-related trending articles for copywriting research.
"""

import json
import time
import hashlib
import logging
import re
import os
import sys
from datetime import datetime, timedelta
from urllib.parse import quote_plus, urljoin
from pathlib import Path

import feedparser
import requests
from bs4 import BeautifulSoup

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data/logs/crawler.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# CONFIG
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)


class GoogleNewsCrawler:
    """Crawls Google News RSS feeds filtered by site + keyword."""

    RSS_BASE = "https://news.google.com/rss/search"

    def __init__(self, config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config['crawler']['user_agent']
        })
        self.delay = config['crawler']['request_delay_seconds']
        self.timeout = config['crawler']['request_timeout_seconds']
        self.seen_urls = set()

    def build_query(self, domain, keyword, days_back=1):
        """Build Google News search query with site: operator."""
        date_after = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        query = f'site:{domain} "{keyword}" after:{date_after}'
        return query

    def fetch_rss(self, query):
        """Fetch and parse a Google News RSS feed for a query."""
        url = f"{self.RSS_BASE}?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            return feed.entries
        except Exception as e:
            logger.warning(f"RSS fetch failed for query '{query[:50]}...': {e}")
            return []

    def crawl_niche(self, niche_name, keywords, sites, max_articles=30):
        """Crawl all sites for a specific niche using its keywords."""
        articles = []
        max_per_query = self.config['crawler']['max_articles_per_query']

        logger.info(f"Crawling niche: {niche_name} ({len(keywords)} keywords x {len(sites)} sites)")

        for site in sites:
            domain = site['domain']
            site_name = site['name']

            for keyword in keywords:
                if len(articles) >= max_articles:
                    break

                query = self.build_query(domain, keyword)
                entries = self.fetch_rss(query)

                for entry in entries[:max_per_query]:
                    url = entry.get('link', '')

                    # Deduplicate
                    url_hash = hashlib.md5(url.encode()).hexdigest()
                    if url_hash in self.seen_urls:
                        continue
                    self.seen_urls.add(url_hash)

                    article = {
                        'title': entry.get('title', ''),
                        'url': url,
                        'source': site_name,
                        'domain': domain,
                        'published': entry.get('published', ''),
                        'niche': niche_name,
                        'matched_keyword': keyword,
                        'summary': entry.get('summary', ''),
                        'crawled_at': datetime.now().isoformat()
                    }
                    articles.append(article)

                    if len(articles) >= max_articles:
                        break

                time.sleep(self.delay)

        logger.info(f"Niche '{niche_name}': found {len(articles)} articles")
        return articles


class DirectCrawler:
    """Directly crawls sites that may not be well-indexed in Google News."""

    def __init__(self, config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config['crawler']['user_agent']
        })
        self.timeout = config['crawler']['request_timeout_seconds']
        self.delay = config['crawler']['request_delay_seconds']

    def scrape_homepage(self, site, keywords):
        """Scrape a site homepage and filter articles by keywords."""
        url = site['url']
        articles = []

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            links = soup.find_all('a', href=True)
            keyword_pattern = re.compile(
                '|'.join(re.escape(kw) for kw in keywords),
                re.IGNORECASE
            )

            for link in links:
                text = link.get_text(strip=True)
                href = link['href']

                if not text or len(text) < 20:
                    continue

                if keyword_pattern.search(text):
                    full_url = urljoin(url, href)

                    matched = None
                    for kw in keywords:
                        if kw.lower() in text.lower():
                            matched = kw
                            break

                    articles.append({
                        'title': text,
                        'url': full_url,
                        'source': site['name'],
                        'domain': site['domain'],
                        'published': datetime.now().strftime('%Y-%m-%d'),
                        'matched_keyword': matched or 'homepage_match',
                        'summary': '',
                        'crawled_at': datetime.now().isoformat()
                    })

        except Exception as e:
            logger.warning(f"Direct crawl failed for {site['name']}: {e}")

        return articles


class ArticleExtractor:
    """Extracts main text content from article URLs."""

    def __init__(self, config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config['crawler']['user_agent']
        })
        self.timeout = config['crawler']['request_timeout_seconds']
        self.max_chars = config['crawler']['article_max_chars']

    def extract(self, url):
        """Extract main article text from a URL."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            for tag in soup(['script', 'style', 'nav', 'header', 'footer',
                           'aside', 'iframe', 'noscript']):
                tag.decompose()

            article = (
                soup.find('article') or
                soup.find('div', class_=re.compile(r'article|post|content|entry', re.I)) or
                soup.find('main') or
                soup.body
            )

            if article:
                paragraphs = article.find_all('p')
                text = '\n'.join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30)
                return text[:self.max_chars]

            return ""

        except Exception as e:
            logger.warning(f"Content extraction failed for {url}: {e}")
            return ""


def run_crawl(config=None):
    """Execute a full crawl cycle across all niches and sites."""
    if config is None:
        config = load_config()

    os.makedirs('data/raw', exist_ok=True)
    os.makedirs('data/reports', exist_ok=True)
    os.makedirs('data/logs', exist_ok=True)

    gn_crawler = GoogleNewsCrawler(config)
    direct_crawler = DirectCrawler(config)
    extractor = ArticleExtractor(config)

    all_sites = config['sites']['gossip'] + config['sites']['health']

    all_articles = {}
    total_count = 0

    for niche_name, niche_data in config['niches'].items():
        keywords = niche_data['keywords']
        max_articles = config['crawler']['max_articles_per_niche']

        articles = gn_crawler.crawl_niche(niche_name, keywords, all_sites, max_articles)

        sites_with_results = {a['domain'] for a in articles}
        sites_missing = [s for s in all_sites if s['domain'] not in sites_with_results]

        if sites_missing and len(articles) < max_articles // 2:
            logger.info(f"Supplementing with direct crawl for {len(sites_missing)} sites...")
            for site in sites_missing[:5]:
                direct_articles = direct_crawler.scrape_homepage(site, keywords)
                for da in direct_articles:
                    da['niche'] = niche_name
                articles.extend(direct_articles[:3])
                time.sleep(direct_crawler.delay)

        top_articles = articles[:15]
        logger.info(f"Extracting content for {len(top_articles)} top articles in '{niche_name}'...")

        for article in top_articles:
            content = extractor.extract(article['url'])
            article['content'] = content
            time.sleep(1)

        for article in articles[15:]:
            article['content'] = ''

        all_articles[niche_name] = articles
        total_count += len(articles)
        logger.info(f"Niche '{niche_name}' complete: {len(articles)} articles")

    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    raw_file = f"data/raw/crawl_{timestamp}.json"
    with open(raw_file, 'w', encoding='utf-8') as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)

    logger.info(f"Crawl complete. Total: {total_count} articles. Saved to {raw_file}")

    return all_articles, raw_file


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Starting Health Trend Crawler")
    logger.info("=" * 60)

    articles, raw_file = run_crawl()

    print(f"\nCrawl finished. Results saved to: {raw_file}")
    for niche, arts in articles.items():
        print(f"  {niche}: {len(arts)} articles")
