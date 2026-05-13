from fastapi import APIRouter, HTTPException, Depends
import os
import httpx
from pydantic import BaseModel, Field

router = APIRouter(prefix="/scraper", tags=["Scraper"])

class ScraperRequest(BaseModel):
    input_type: str = Field(..., description="'url' or 'text'")
    payload: str = Field(..., description="The URL or raw text to scrape")

@router.post("/extract", summary="Extract candidate data using n8n webhook")
async def extract_candidate_data(request: ScraperRequest):
    """
    Accepts a URL (like LinkedIn) or raw text.
    Forwards it to an external n8n webhook which handles the actual scraping/parsing.
    Returns the structured candidate data JSON.
    """
    if request.input_type not in ["url", "text"]:
        raise HTTPException(status_code=400, detail="input_type must be 'url' or 'text'")

    webhook_url = os.getenv("N8N_WEBHOOK_URL")
    if not webhook_url:
        raise HTTPException(
            status_code=500, 
            detail="N8N_WEBHOOK_URL environment variable is not set"
        )

    try:
        # Use httpx for async HTTP requests
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                webhook_url,
                json={"input_type": request.input_type, "payload": request.payload}
            )
            response.raise_for_status()
            
            # Assuming n8n returns JSON
            return response.json()
            
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code, 
            detail=f"n8n webhook error: {e.response.text}"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to communicate with n8n webhook: {str(e)}"
        )
