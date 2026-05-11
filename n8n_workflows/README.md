# n8n Workflows

This directory contains exported n8n workflow JSON files.

## Candidate_Scraper_Workflow.json

**Purpose:** Module 1 — Candidate Data Scraper microservice.

**Flow:**
1. Receives payload from FastAPI via **Webhook** trigger (URL/text to scrape).
2. Scrapes raw text from the provided source using HTTP Request node.
3. Sends raw text to **Claude API** node for normalization into structured JSON.
4. Returns the normalized candidate JSON back to FastAPI via Webhook Response.

### Setup
1. Import the workflow JSON into your n8n instance.
2. Configure the Claude API credentials in n8n.
3. Set the Webhook URL in FastAPI's `.env` (`N8N_WEBHOOK_URL`).
