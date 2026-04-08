#!/usr/bin/env python3
"""
Health Trend Crawler - Main Orchestrator
Coordinates crawling, analysis, and dashboard generation.
"""

import json
import sys
import logging
import os
import argparse
from datetime import datetime
from pathlib import Path

# Add project dir to path
sys.path.insert(0, str(Path(__file__).parent))

from crawler import run_crawl
from analyzer import run_analysis
from dashboard import generate_dashboard

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data/logs/main.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent

def load_config():
    with open(BASE_DIR / "config.json", 'r') as f:
        return json.load(f)


def run_pipeline(crawl_only=False, analyze_file=None, skip_dashboard=False):
    """Run the complete pipeline: Crawl -> Analyze -> Generate Dashboard."""

    config = load_config()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

    logger.info("=" * 70)
    logger.info(f"HEALTH TREND CRAWLER - Pipeline Start - {timestamp}")
    logger.info("=" * 70)

    # Ensure directories
    os.makedirs('data/raw', exist_ok=True)
    os.makedirs('data/reports', exist_ok=True)
    os.makedirs('data/logs', exist_ok=True)

    # -- STEP 1: CRAWL --
    if analyze_file:
        logger.info(f"Skipping crawl, loading data from: {analyze_file}")
        with open(analyze_file, 'r') as f:
            crawl_data = json.load(f)
        raw_file = analyze_file
    else:
        logger.info("STEP 1/3: Starting crawl...")
        crawl_data, raw_file = run_crawl(config)

        total = sum(len(v) for v in crawl_data.values())
        logger.info(f"Crawl complete: {total} articles across {len(crawl_data)} niches")

        if total == 0:
            logger.warning("No articles found. Ending pipeline.")
            return

    if crawl_only:
        logger.info("Crawl-only mode. Stopping here.")
        print(f"\nRaw data saved to: {raw_file}")
        return

    # -- STEP 2: ANALYZE --
    logger.info("STEP 2/3: Starting analysis with Claude...")
    report, report_file = run_analysis(crawl_data, config)

    # Print summary to console
    daily = report.get('daily_summary', {})
    if daily:
        print("\n" + "=" * 60)
        print(f"DAILY BRIEFING - {timestamp}")
        print("=" * 60)
        print(f"\nHottest niche: {daily.get('hottest_niche_today', 'N/A')}")
        print(f"\n{daily.get('daily_briefing', 'No briefing generated.')}")

        print("\nTop Actionable Angles:")
        for i, angle in enumerate(daily.get('top_5_actionable_angles', []), 1):
            urgency = angle.get('urgency', '')
            marker = {'high': '!!!', 'medium': '!!', 'low': '!'}.get(urgency, '')
            print(f"  {i}. [{angle.get('niche', '')}] {angle.get('angle', '')} {marker}")
        print("=" * 60)

    # -- STEP 3: GENERATE DASHBOARD --
    if not skip_dashboard:
        logger.info("STEP 3/3: Generating HTML dashboard...")
        try:
            generate_dashboard(report, crawl_data, config)
            logger.info("Dashboard updated successfully")
        except Exception as e:
            logger.error(f"Dashboard generation error: {e}")
            logger.info("Pipeline completed without dashboard update. Data saved locally.")
    else:
        logger.info("Skipping dashboard generation (--skip-dashboard)")

    logger.info("=" * 70)
    logger.info(f"Pipeline complete. Report: {report_file}")
    logger.info("=" * 70)

    return report_file


def main():
    parser = argparse.ArgumentParser(
        description='Health Trend Crawler - Daily trend analysis for copywriters'
    )
    parser.add_argument(
        '--skip-dashboard', action='store_true',
        help='Skip HTML dashboard generation'
    )
    parser.add_argument(
        '--crawl-only', action='store_true',
        help='Only crawl, skip analysis and dashboard'
    )
    parser.add_argument(
        '--analyze', type=str, metavar='FILE',
        help='Skip crawl, analyze existing crawl data file'
    )
    parser.add_argument(
        '--test', action='store_true',
        help='Quick test with reduced scope (1 niche, 3 articles)'
    )
    parser.add_argument(
        '--dashboard-only', action='store_true',
        help='Only regenerate dashboard from latest report'
    )

    args = parser.parse_args()

    # Dashboard-only mode
    if args.dashboard_only:
        logger.info("Dashboard-only mode: regenerating from latest report...")
        generate_dashboard()
        return

    if args.test:
        logger.info("TEST MODE: Reducing scope...")
        config = load_config()
        # Keep only first niche
        first_niche = list(config['niches'].keys())[0]
        config['niches'] = {first_niche: config['niches'][first_niche]}
        config['crawler']['max_articles_per_niche'] = 3
        config['crawler']['max_articles_per_query'] = 2
        # Save temp config
        with open(BASE_DIR / "config_test.json", 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"Test mode: only '{first_niche}' niche, max 3 articles")

    run_pipeline(
        crawl_only=args.crawl_only,
        analyze_file=args.analyze,
        skip_dashboard=args.skip_dashboard
    )


if __name__ == '__main__':
    main()
