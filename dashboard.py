#!/usr/bin/env python3
"""
Dashboard Generator
Reads report JSONs and generates static HTML files served by Caddy.
"""

import json
import glob
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
PUBLIC_DIR = BASE_DIR / "public"
REPORTS_DIR = BASE_DIR / "data" / "reports"
RAW_DIR = BASE_DIR / "data" / "raw"


def load_config():
    with open(BASE_DIR / "config.json", 'r') as f:
        return json.load(f)


def setup_jinja():
    """Initialize Jinja2 environment."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False
    )
    return env


def get_latest_report():
    """Find and load the most recent report JSON."""
    report_files = sorted(glob.glob(str(REPORTS_DIR / "report_*.json")), reverse=True)
    if not report_files:
        return None, None

    latest = report_files[0]
    with open(latest, 'r', encoding='utf-8') as f:
        return json.load(f), latest


def get_latest_crawl_for_report(report):
    """Find the crawl data that corresponds to a report."""
    if not report:
        return {}

    meta = report.get('metadata', {})
    date = meta.get('date', '')
    run_time = meta.get('run_time', '').replace(':', '')

    pattern = f"crawl_{date.replace('-', '')}*.json"
    crawl_files = sorted(glob.glob(str(RAW_DIR / pattern)), reverse=True)

    if crawl_files:
        with open(crawl_files[0], 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def get_all_reports():
    """Load metadata from all historical reports."""
    report_files = sorted(glob.glob(str(REPORTS_DIR / "report_*.json")), reverse=True)
    reports = []

    for rf in report_files[:30]:
        try:
            with open(rf, 'r', encoding='utf-8') as f:
                data = json.load(f)
            meta = data.get('metadata', {})
            daily = data.get('daily_summary', {})
            reports.append({
                'date': meta.get('date', 'Unknown'),
                'run_time': meta.get('run_time', ''),
                'niches_with_data': meta.get('niches_with_data', []),
                'hottest_niche': daily.get('hottest_niche_today', '') if daily else '',
                'file': rf
            })
        except Exception as e:
            logger.warning(f"Failed to load report {rf}: {e}")

    return reports


def generate_main_dashboard(env, report, config):
    """Generate the main index.html dashboard."""
    template = env.get_template("index.html")

    meta = report.get('metadata', {}) if report else {}
    daily_summary = report.get('daily_summary') if report else None
    niche_reports = report.get('niche_reports', {}) if report else {}

    html = template.render(
        active_page='home',
        last_update=meta.get('generated_at', 'Never')[:16].replace('T', ' '),
        date=meta.get('date', datetime.now().strftime('%Y-%m-%d')),
        run_time=meta.get('run_time', '--:--'),
        daily_summary=daily_summary,
        niche_reports=niche_reports
    )

    output = PUBLIC_DIR / "index.html"
    with open(output, 'w', encoding='utf-8') as f:
        f.write(html)
    logger.info(f"Generated: {output}")


def generate_niche_pages(env, report, crawl_data, config):
    """Generate individual niche pages."""
    template = env.get_template("niche.html")

    meta = report.get('metadata', {}) if report else {}
    niche_reports = report.get('niche_reports', {}) if report else {}
    niches = config.get('niches', {})

    for niche_key in niches.keys():
        niche_report = niche_reports.get(niche_key)
        articles = crawl_data.get(niche_key, [])

        html = template.render(
            active_page=niche_key,
            last_update=meta.get('generated_at', 'Never')[:16].replace('T', ' '),
            date=meta.get('date', datetime.now().strftime('%Y-%m-%d')),
            run_time=meta.get('run_time', '--:--'),
            niche_name=niche_key,
            report=niche_report,
            articles=articles
        )

        output = PUBLIC_DIR / f"niche_{niche_key}.html"
        with open(output, 'w', encoding='utf-8') as f:
            f.write(html)
        logger.info(f"Generated: {output}")


def generate_history_page(env, config):
    """Generate the history index page."""
    template = env.get_template("history.html")
    reports = get_all_reports()

    html = template.render(
        active_page='history',
        last_update=datetime.now().strftime('%Y-%m-%d %H:%M'),
        reports=reports
    )

    os.makedirs(PUBLIC_DIR / "history", exist_ok=True)
    output = PUBLIC_DIR / "history" / "index.html"
    with open(output, 'w', encoding='utf-8') as f:
        f.write(html)
    logger.info(f"Generated: {output}")

    for rpt_meta in reports:
        try:
            with open(rpt_meta['file'], 'r', encoding='utf-8') as f:
                full_report = json.load(f)

            crawl_data = get_latest_crawl_for_report(full_report)

            index_template = env.get_template("index.html")
            meta = full_report.get('metadata', {})

            html = index_template.render(
                active_page='history',
                last_update=meta.get('generated_at', '')[:16].replace('T', ' '),
                date=meta.get('date', ''),
                run_time=meta.get('run_time', ''),
                daily_summary=full_report.get('daily_summary'),
                niche_reports=full_report.get('niche_reports', {})
            )

            day_output = PUBLIC_DIR / "history" / f"{rpt_meta['date']}.html"
            with open(day_output, 'w', encoding='utf-8') as f:
                f.write(html)

        except Exception as e:
            logger.warning(f"Failed to generate history page for {rpt_meta['date']}: {e}")


def generate_dashboard(report=None, crawl_data=None, config=None):
    """Generate the complete static dashboard."""
    if config is None:
        config = load_config()

    os.makedirs(PUBLIC_DIR, exist_ok=True)
    os.makedirs(PUBLIC_DIR / "history", exist_ok=True)

    if report is None:
        report, _ = get_latest_report()

    if crawl_data is None:
        crawl_data = get_latest_crawl_for_report(report) if report else {}

    env = setup_jinja()

    generate_main_dashboard(env, report, config)
    generate_niche_pages(env, report, crawl_data, config)
    generate_history_page(env, config)

    logger.info("Dashboard generation complete")
    return True


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        report_file = sys.argv[1]
        with open(report_file, 'r') as f:
            report = json.load(f)

        crawl_data = None
        if len(sys.argv) > 2:
            with open(sys.argv[2], 'r') as f:
                crawl_data = json.load(f)
        else:
            crawl_data = get_latest_crawl_for_report(report)

        generate_dashboard(report, crawl_data)
    else:
        generate_dashboard()
