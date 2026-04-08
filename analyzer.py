#!/usr/bin/env python3
"""
Health Trend Analyzer
Uses Claude Code CLI to analyze crawled articles and generate
actionable trend reports for copywriting.
"""

import json
import subprocess
import logging
import os
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent

def load_config():
    with open(BASE_DIR / "config.json", 'r') as f:
        return json.load(f)


def call_claude(prompt, model="sonnet", max_tokens=4000):
    """Call Claude Code CLI with a prompt and return the response."""
    try:
        cmd = [
            "claude",
            "-p", prompt,
            "--model", model,
            "--output-format", "text"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(BASE_DIR)
        )

        if result.returncode != 0:
            logger.error(f"Claude CLI error: {result.stderr}")
            return None

        return result.stdout.strip()

    except subprocess.TimeoutExpired:
        logger.error("Claude CLI timed out (120s)")
        return None
    except FileNotFoundError:
        logger.error("Claude CLI not found. Make sure 'claude' is in PATH.")
        return None
    except Exception as e:
        logger.error(f"Claude CLI call failed: {e}")
        return None


def build_niche_analysis_prompt(niche_name, articles):
    """Build the analysis prompt for a specific niche."""

    articles_text = ""
    for i, art in enumerate(articles[:20], 1):
        content_preview = art.get('content', '')[:500]
        articles_text += f"""
--- Article {i} ---
Title: {art['title']}
Source: {art['source']}
Keyword: {art['matched_keyword']}
Published: {art.get('published', 'N/A')}
URL: {art['url']}
Content preview: {content_preview}
"""

    prompt = f"""You are a senior copywriting research analyst specialized in direct response health marketing for the US market.

Analyze these {len(articles)} articles from today's crawl for the **{niche_name.upper().replace('_', ' ')}** niche.

{articles_text}

Generate a structured JSON report with this EXACT format:
{{
  "niche": "{niche_name}",
  "date": "{datetime.now().strftime('%Y-%m-%d')}",
  "run_time": "{datetime.now().strftime('%H:%M')}",
  "total_articles_analyzed": {len(articles)},
  "trending_topics": [
    {{
      "topic": "Brief topic description",
      "relevance_score": 8,
      "sources_count": 2,
      "key_articles": ["Article title 1", "Article title 2"],
      "consumer_angle": "Why this matters to consumers in this niche",
      "copy_hook_ideas": ["Hook idea 1", "Hook idea 2", "Hook idea 3"]
    }}
  ],
  "celebrity_mentions": [
    {{
      "celebrity": "Name",
      "context": "What they said/did related to this niche",
      "copy_potential": "How this could be used as a copy angle"
    }}
  ],
  "new_studies_or_discoveries": [
    {{
      "finding": "Brief description",
      "source": "Where it was published",
      "headline_angle": "How to turn this into a compelling headline"
    }}
  ],
  "product_trends": [
    {{
      "product_or_ingredient": "Name",
      "trend_direction": "rising/stable/declining",
      "context": "Why it's trending"
    }}
  ],
  "top_3_copy_angles": [
    {{
      "angle": "The copy angle in one sentence",
      "type": "fear/desire/curiosity/authority/social_proof",
      "example_headline": "A headline example using this angle",
      "target_emotion": "The primary emotion this targets"
    }}
  ],
  "summary": "2-3 sentence executive summary of today's trends for this niche"
}}

IMPORTANT:
- Focus on trends that are actionable for DIRECT RESPONSE copywriting
- Prioritize celebrity health stories (perfect for advertorial hooks)
- Identify new studies/discoveries (great for "Doctor Reveals" type angles)
- Note any FDA/regulatory news (affects compliance)
- Score relevance 1-10 based on copy potential, not just news importance
- Return ONLY valid JSON, no markdown formatting"""

    return prompt


def build_daily_summary_prompt(niche_reports):
    """Build prompt for the cross-niche daily summary."""

    summaries = ""
    for niche, report in niche_reports.items():
        if report:
            summaries += f"\n--- {niche.upper().replace('_', ' ')} ---\n"
            summaries += f"Summary: {report.get('summary', 'N/A')}\n"
            summaries += f"Articles: {report.get('total_articles_analyzed', 0)}\n"
            top_angles = report.get('top_3_copy_angles', [])
            for angle in top_angles:
                summaries += f"  Angle: {angle.get('angle', 'N/A')}\n"

    prompt = f"""You are a senior copywriting strategist. Based on today's trend analysis across all health niches, create a brief daily executive briefing.

{summaries}

Return a JSON object:
{{
  "date": "{datetime.now().strftime('%Y-%m-%d')}",
  "run_time": "{datetime.now().strftime('%H:%M')}",
  "hottest_niche_today": "Which niche has the most copy potential right now",
  "cross_niche_trends": ["Trend that spans multiple niches"],
  "top_5_actionable_angles": [
    {{
      "niche": "niche_name",
      "angle": "The angle",
      "urgency": "high/medium/low",
      "why": "Brief explanation of why to act on this now"
    }}
  ],
  "daily_briefing": "A 3-4 sentence briefing a copywriter can read in 30 seconds to know what matters today"
}}

Return ONLY valid JSON."""

    return prompt


def analyze_niche(niche_name, articles, config):
    """Analyze a single niche's articles using Claude."""
    if not articles:
        logger.warning(f"No articles to analyze for niche '{niche_name}'")
        return None

    prompt = build_niche_analysis_prompt(niche_name, articles)
    model = config['analyzer'].get('model', 'sonnet')

    logger.info(f"Analyzing niche '{niche_name}' with {len(articles)} articles...")
    response = call_claude(prompt, model=model)

    if response:
        try:
            json_str = response
            if '```json' in json_str:
                json_str = json_str.split('```json')[1].split('```')[0]
            elif '```' in json_str:
                json_str = json_str.split('```')[1].split('```')[0]

            report = json.loads(json_str.strip())
            logger.info(f"Analysis complete for '{niche_name}'")
            return report
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON for '{niche_name}': {e}")
            debug_file = f"data/reports/debug_{niche_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
            with open(debug_file, 'w') as f:
                f.write(response)
            return None
    return None


def generate_daily_summary(niche_reports, config):
    """Generate a cross-niche daily summary."""
    prompt = build_daily_summary_prompt(niche_reports)
    model = config['analyzer'].get('model', 'sonnet')

    logger.info("Generating daily summary...")
    response = call_claude(prompt, model=model)

    if response:
        try:
            json_str = response
            if '```json' in json_str:
                json_str = json_str.split('```json')[1].split('```')[0]
            elif '```' in json_str:
                json_str = json_str.split('```')[1].split('```')[0]
            return json.loads(json_str.strip())
        except json.JSONDecodeError:
            logger.error("Failed to parse daily summary JSON")
            return None
    return None


def run_analysis(crawl_data, config=None):
    """Run full analysis pipeline on crawled data."""
    if config is None:
        config = load_config()

    os.makedirs('data/reports', exist_ok=True)

    niche_reports = {}

    for niche_name, articles in crawl_data.items():
        report = analyze_niche(niche_name, articles, config)
        niche_reports[niche_name] = report

    valid_reports = {k: v for k, v in niche_reports.items() if v is not None}
    daily_summary = None
    if valid_reports:
        daily_summary = generate_daily_summary(valid_reports, config)

    full_report = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'date': datetime.now().strftime('%Y-%m-%d'),
            'run_time': datetime.now().strftime('%H:%M'),
            'niches_analyzed': list(niche_reports.keys()),
            'niches_with_data': list(valid_reports.keys())
        },
        'daily_summary': daily_summary,
        'niche_reports': niche_reports
    }

    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    report_file = f"data/reports/report_{timestamp}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(full_report, f, ensure_ascii=False, indent=2)

    logger.info(f"Full report saved to {report_file}")

    return full_report, report_file


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python analyzer.py <crawl_data.json>")
        sys.exit(1)

    crawl_file = sys.argv[1]
    with open(crawl_file, 'r') as f:
        crawl_data = json.load(f)

    report, report_file = run_analysis(crawl_data)
    print(f"Report saved to: {report_file}")
