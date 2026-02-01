"""
Order Parser Tool
Parses natural language into structured order
"""
import json
import re
from typing import Dict, Any
from ..config import SECURITIES_DB, USE_MOCK_LLM

if not USE_MOCK_LLM:
    from openai import AzureOpenAI
    from ..config import (
        AZURE_OPENAI_API_KEY,
        AZURE_OPENAI_ENDPOINT,
        AZURE_OPENAI_CHAT_DEPLOYMENT,
        AZURE_OPENAI_API_VERSION
    )
    
    azure_client = AzureOpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_version=AZURE_OPENAI_API_VERSION
    )


async def parse_order_tool(text: str) -> Dict[str, Any]:
    """
    MCP Tool: Parse natural language order
    
    Args:
        text: Natural language order description
    
    Returns:
        Structured order details
    """
    if USE_MOCK_LLM:
        return _mock_parse_order(text)
    
    prompt = f"""Parse this trading order into structured format. Return ONLY valid JSON.

Order text: "{text}"

Available securities: AAPL, MSFT, GOOGL, TSLA, NOVN, NESN

Extract:
- symbol: ticker symbol or "UNKNOWN"
- quantity: number of shares (default 100)
- side: "BUY" or "SELL"
- price: limit price if mentioned, else null
- tif: "DAY", "GTC", "GTD", or "FOK"
- requested_strategy: "VWAP", "TWAP", "POV", "MOC" if mentioned, else null

Return JSON only:
{{
  "symbol": "AAPL",
  "quantity": 100,
  "side": "BUY",
  "price": null,
  "tif": "DAY",
  "requested_strategy": null
}}"""

    try:
        response = azure_client.chat.completions.create(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are an order parser. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=300
        )
        
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = re.sub(r'^```(?:json)?\s*|\s*```$', '', content, flags=re.MULTILINE).strip()
        
        parsed = json.loads(content)
        
        # Add security info if symbol is valid
        symbol = parsed.get("symbol", "UNKNOWN")
        if symbol in SECURITIES_DB:
            parsed["security"] = SECURITIES_DB[symbol]
        
        return parsed
        
    except Exception as e:
        print(f"Parse error: {e}")
        return _mock_parse_order(text)


def _mock_parse_order(text: str) -> Dict[str, Any]:
    """Fallback parser"""
    lower = text.lower()
    
    # Find symbol
    symbol = None
    for sym in SECURITIES_DB.keys():
        if sym.lower() in lower:
            symbol = sym
            break
    
    # Quantity
    qty_match = re.search(r'(\d+)', text)
    quantity = int(qty_match.group(1)) if qty_match else 100
    
    # Side
    side = "SELL" if any(w in lower for w in ["sell", "selling"]) else "BUY"
    
    # Price
    price_match = re.search(r'[@at]\s*(\d+(?:\.\d+)?)', lower)
    price = float(price_match.group(1)) if price_match else None
    
    # TIF
    tif = "GTC" if "gtc" in lower else "DAY"
    
    # Strategy
    strategy = None
    for s in ["VWAP", "TWAP", "POV", "MOC"]:
        if s.lower() in lower:
            strategy = s
            break
    
    result = {
        "symbol": symbol or "UNKNOWN",
        "quantity": quantity,
        "side": side,
        "price": price,
        "tif": tif,
        "requested_strategy": strategy
    }
    
    if symbol and symbol in SECURITIES_DB:
        result["security"] = SECURITIES_DB[symbol]
    
    return result
