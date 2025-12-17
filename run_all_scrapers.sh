#!/bin/bash
# Run all scrapers in Docker containers in parallel

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "🚀 Building Docker images for scrapers..."
docker-compose -f config/docker-compose.yml build scraper_playwright scraper_facebook scraper_dynamic

echo "📊 Starting all scrapers in parallel..."
docker-compose -f config/docker-compose.yml --profile scrapers up \
    scraper_playwright \
    scraper_facebook \
    scraper_dynamic

echo "✓ All scrapers completed!"
