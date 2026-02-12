from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import json
import re
from pydantic import BaseModel

app = FastAPI(title="Veritas API")

# CORS - allow your GitHub Pages frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yourusername.github.io",  # CHANGE THIS to your actual GitHub Pages URL
        "http://localhost:8000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QuestionRequest(BaseModel):
    question: str
    context: str = ""

@app.post("/api/rules")
async def get_rules(request: QuestionRequest):
    """
    Get MTG ruling from Scryfall + logic
    """
    try:
        # 1. Search Scryfall for relevant cards
        cards = await search_scryfall(request.question)
        
        # 2. Build response with card data
        if cards:
            card = cards[0]  # Use first result
            ruling = await get_card_rulings(card.get("rulings_uri", ""))
            
            return {
                "title": card.get("name", "Unknown Card"),
                "rule": card.get("oracle_text", "No rule text available"),
                "reference": f"Scryfall: {card.get('set_name', 'Unknown Set')}",
                "explanation": f"This card has {len(ruling)} official rulings.",
                "action": "Check the official ruling below or ask a judge for complex interactions.",
                "rulings": ruling[:3],  # Top 3 rulings
                "scryfall_uri": card.get("scryfall_uri", "")
            }
        
        # No card found - generic response
        return {
            "title": "General Rules Question",
            "rule": "The Comprehensive Rules cover this interaction.",
            "reference": "CR - Comprehensive Rules",
            "explanation": "I couldn't find a specific card. Try mentioning the card name clearly.",
            "action": "Ask about a specific card (e.g., 'How does Lightning Bolt work?') or consult the Comprehensive Rules.",
            "rulings": [],
            "scryfall_uri": None
        }
        
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def search_scryfall(query: str):
    """Search Scryfall for cards"""
    try:
        # Clean query - extract potential card names
        # Remove common question words
        clean_query = re.sub(r'(?i)(how does|what is|can i|do|does|the|a|an|work|with|target)\s+', ' ', query)
        clean_query = clean_query.strip()[:50]  # Limit length
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.scryfall.com/cards/search",
                params={"q": clean_query, "unique": "cards", "order": "relevance"}
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])[:1]  # Return top result
            
            return []
    except Exception as e:
        print(f"Scryfall error: {e}")
        return []

async def get_card_rulings(rulings_uri: str):
    """Get official rulings for a card"""
    if not rulings_uri:
        return []
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(rulings_uri)
            if response.status_code == 200:
                data = response.json()
                return [r["comment"] for r in data.get("data", [])]
            return []
    except Exception as e:
        print(f"Rulings error: {e}")
        return []

@app.get("/health")
async def health():
    return {"status": "ok", "service": "Veritas API"}

# For local testing
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)