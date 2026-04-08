#!/bin/bash
# Health Trend Crawler - Cron Runner
# This script is called by cron 2x/day (8h and 18h EST)

# Project directory (update this to your VPS path)
PROJECT_DIR="$HOME/health-trend-crawler"

# Log file
LOG_FILE="$PROJECT_DIR/data/logs/cron_$(date +%Y%m%d_%H%M).log"

# Change to project dir
cd "$PROJECT_DIR" || exit 1

# Ensure directories exist
mkdir -p data/raw data/reports data/logs

# Activate virtual environment if exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Run the pipeline
echo "$(date): Starting Health Trend Crawler..." >> "$LOG_FILE"
python3 main.py 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}

# Log completion
if [ $EXIT_CODE -eq 0 ]; then
    echo "$(date): Pipeline completed successfully" >> "$LOG_FILE"
else
    echo "$(date): Pipeline failed with exit code $EXIT_CODE" >> "$LOG_FILE"
fi

# Cleanup old logs (keep 30 days)
find "$PROJECT_DIR/data/logs" -name "cron_*.log" -mtime +30 -delete 2>/dev/null
find "$PROJECT_DIR/data/raw" -name "crawl_*.json" -mtime +30 -delete 2>/dev/null
find "$PROJECT_DIR/data/reports" -name "report_*.json" -mtime +30 -delete 2>/dev/null

echo "$(date): Cleanup done" >> "$LOG_FILE"
