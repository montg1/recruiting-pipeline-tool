# n8n Workflows

Exported n8n workflows for the recruiting pipeline. Import each via
**n8n → Workflows → ⋯ → Import from File**.

---

## Module1_AI_Workflow.json — Module 1 AI brain (parse_jd + rank)

When `LLM_PROVIDER=n8n`, FastAPI does **no** Claude calls itself. It forwards the
raw inputs to this workflow's webhook; n8n owns the prompts and calls Claude.

**Flow:**
```
Webhook (POST /webhook/recruitpipe-ai)
  → Route by task (IF body.task == "rank")
      ├─ rank  → Build rank request  → Claude (rank)  → Extract rank JSON  ┐
      └─ parse → Build parse request → Claude (parse) → Extract parse JSON ┘
  → Respond to FastAPI
```

**Contract (what FastAPI sends / expects back):**
| task | request body | response |
|------|--------------|----------|
| `parse_jd` | `{ "task":"parse_jd", "jd_text":"..." }` | criteria object `{position, role_keywords[], must_have_skills[], …}` |
| `rank` | `{ "task":"rank", "criteria":{…}, "candidates":[{id,full_name,headline,…}] }` | `{ "rankings":[{id, match_score, verdict, reasons[], missing[]}] }` |

FastAPI tolerates n8n's usual array-wrapping (`[ {...} ]`) and raw-text passthrough.

### Setup
1. Import `Module1_AI_Workflow.json`.
2. Create an **HTTP Header Auth** credential: Name = `x-api-key`, Value = your Anthropic API key. Assign it to **both** `Claude (parse)` and `Claude (rank)` nodes (they show `REPLACE_ME` until you do).
3. (Optional) Change the model in the two *Build … request* Code nodes (default `claude-sonnet-4-6`).
4. **Activate** the workflow, copy the Production webhook URL, and set it in the backend `.env`:
   ```
   LLM_PROVIDER=n8n
   N8N_AI_WEBHOOK_URL=https://<your-n8n>/webhook/recruitpipe-ai
   ```
5. Restart FastAPI. Now `/api/scraper/search-from-jd` routes all AI through n8n.

> Discovery (GitHub API + LinkedIn X-ray via ZenRows) stays in FastAPI — it's
> web data-collection, not AI. Only the LLM steps live in n8n.

---

## Candidate_Scraper_Workflow.json — (legacy) single-profile normalize

Placeholder for the original brief's `/extract` flow: Webhook → scrape one
URL/text → Claude normalize → respond. Used by the manual-paste fallback
(e.g. a Facebook job-seeking post). Build out as needed.
