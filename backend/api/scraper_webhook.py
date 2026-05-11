"""
Scraper webhook endpoint — receives URL/text from frontend,
forwards payload to n8n webhook for scraping and AI normalization,
then returns the structured candidate data for preview.
"""

from fastapi import APIRouter

router = APIRouter()


# TODO: Implement scraper webhook endpoints
# - POST /scrape   → Accept URL/text, forward to n8n webhook,
#                     receive normalized JSON, return for frontend preview
# - POST /confirm  → HR confirms previewed data, save to database
