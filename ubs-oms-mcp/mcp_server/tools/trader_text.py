"""
Additional MCP Tools
- Trader text parser
- Autocomplete
- Securities lookup
"""
import json
import re
from typing import Dict, Any, List
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


async def parse_trader_text_tool(text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    MCP Tool: Parse trader execution instructions
    
    Args:
        text: Trader instructions (e.g., "VWAP Market Close")
        context: Optional context (symbol, quantity)
    
    Returns:
        Parsed algo details
    """
    if USE_MOCK_LLM:
        return _mock_parse_trader_text(text)
    
    prompt = f"""Parse trader execution instruction. Return ONLY valid JSON.

Trader text: "{text}"

Allowed algos: VWAP, TWAP, POV, MOC

Extract:
- algo: algorithm name or null
- structured: human-readable format
- backend_format: pipe-separated (e.g., "VWAP|START=09:30|END=16:00")
- description: what this strategy does
- parameters: dict of extracted params
- confidence: 0.0-1.0

Return JSON only."""

    try:
        response = azure_client.chat.completions.create(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are a trader text parser. Return JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=300
        )
        
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = re.sub(r'^```(?:json)?\s*|\s*```$', '', content, flags=re.MULTILINE).strip()
        
        return json.loads(content)
        
    except Exception as e:
        print(f"Parse trader text error: {e}")
        return _mock_parse_trader_text(text)


def _mock_parse_trader_text(text: str) -> Dict[str, Any]:
    """Fallback trader text parser"""
    lower = text.lower()
    
    if 'vwap' in lower:
        return {
            "algo": "vwap",
            "structured": "VWAP Market Close [16:00]",
            "backend_format": "VWAP|START=09:30|END=16:00|AUCTIONS=false",
            "description": "Execute throughout day to match volume-weighted average price",
            "parameters": {"start_time": "09:30", "end_time": "16:00"},
            "confidence": 0.9,
            "reasoning": "VWAP keyword detected"
        }
    elif 'twap' in lower:
        return {
            "algo": "twap",
            "structured": "TWAP execution over trading day",
            "backend_format": "TWAP|START=09:30|END=16:00|SLICES=30",
            "description": "Distribute order evenly over time period",
            "parameters": {"duration": "full day", "slices": 30},
            "confidence": 0.9,
            "reasoning": "TWAP keyword detected"
        }
    elif 'pov' in lower:
        return {
            "algo": "pov",
            "structured": "POV 10% participation rate",
            "backend_format": "POV|RATE=0.1|MIN=0.05|MAX=0.15",
            "description": "Execute as percentage of market volume",
            "parameters": {"participation_rate": 0.1},
            "confidence": 0.85,
            "reasoning": "POV keyword detected"
        }
    elif 'moc' in lower:
        return {
            "algo": "moc",
            "structured": "MOC - Market on Close",
            "backend_format": "MOC|SUBMIT=15:45",
            "description": "Execute at market close auction",
            "parameters": {},
            "confidence": 0.9,
            "reasoning": "MOC keyword detected"
        }
    else:
        return {
            "algo": None,
            "structured": f"Custom: {text}",
            "backend_format": f"CUSTOM|{text}",
            "description": "Custom execution strategy",
            "parameters": {},
            "confidence": 0.5,
            "reasoning": "No specific algorithm detected"
        }


async def autocomplete_tool(text: str) -> List[str]:
    """
    MCP Tool: Get autocomplete suggestions
    
    Args:
        text: Partial text input
    
    Returns:
        List of suggestions
    """
    if len(text) < 2:
        return []
    
    # Simple keyword matching
    suggestions_map = {
        'vwap': [
            'VWAP Market Close [16:00] on all auctions',
            'VWAP full day with 10% participation',
            'VWAP aggressive slice'
        ],
        'twap': [
            'TWAP over 2 hours with 30 slices',
            'TWAP full day even distribution',
            'TWAP with random intervals'
        ],
        'pov': [
            'POV 10% participation rate',
            'POV 5-15% dynamic rate',
            'POV low impact mode'
        ],
        'moc': [
            'MOC - Market on Close execution',
            'MOC with limit protection',
            'MOC passive submit'
        ]
    }
    
    text_lower = text.lower().strip()
    
    for key, suggestions in suggestions_map.items():
        if text_lower.startswith(key):
            return [s for s in suggestions if s.lower().startswith(text_lower)]
    
    return []


async def get_securities_tool() -> List[Dict[str, Any]]:
    """
    MCP Tool: Get list of available securities
    
    Returns:
        List of security info dicts
    """
    return list(SECURITIES_DB.values())


async def get_security_tool(symbol: str) -> Dict[str, Any]:
    """
    MCP Tool: Get specific security info
    
    Args:
        symbol: Security symbol
    
    Returns:
        Security info or error
    """
    symbol_upper = symbol.upper()
    if symbol_upper in SECURITIES_DB:
        return SECURITIES_DB[symbol_upper]
    
    return {"error": f"Security {symbol} not found"}
