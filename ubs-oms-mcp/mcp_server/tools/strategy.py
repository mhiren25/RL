"""
Strategy Suggestion Tool
Recommends execution strategy with correction capture
"""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from ..config import (
    MARKET_DATA, USER_HISTORY, ALLOWED_STRATEGIES,
    CORRECTIONS_DIR, load_prompt, USE_MOCK_LLM
)

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


def get_market_context(security: str) -> Dict[str, Any]:
    """Get market context for a security"""
    if security in MARKET_DATA:
        return MARKET_DATA[security]
    return {"adv": 1_000_000, "recent_volatility": "MEDIUM"}


def get_trader_history(security: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Get trader's recent history for this security"""
    symbol_history = [h for h in USER_HISTORY if h["symbol"] == security]
    if not symbol_history:
        symbol_history = USER_HISTORY[:limit]  # Fallback to general history
    return symbol_history[:limit]


def format_history_summary(history: List[Dict[str, Any]]) -> str:
    """Format history as human-readable summary"""
    if not history:
        return "No specific history for this symbol."
    
    lines = []
    for h in history:
        lines.append(
            f"- {h['days_ago']} days ago: {h['side']} {h['quantity']} {h['symbol']} "
            f"using {h['strategy']} ({h['tif']})"
        )
    return "\n".join(lines)


def suggest_strategy_with_llm(
    security: str,
    quantity: int,
    time_in_force: str
) -> Dict[str, Any]:
    """
    Suggest execution strategy using Azure OpenAI
    
    Args:
        security: Security symbol
        quantity: Order quantity
        time_in_force: DAY, GTC, GTD, or FOK
    
    Returns:
        Dictionary with suggestion details
    """
    # Get market context
    market_ctx = get_market_context(security)
    adv = market_ctx["adv"]
    volatility = market_ctx["recent_volatility"]
    order_pct = (quantity / adv) * 100 if adv > 0 else 0
    
    # Get trader history
    history = get_trader_history(security)
    history_summary = format_history_summary(history)
    
    # Load prompt template
    prompt_template = load_prompt("strategy")
    
    # Format prompt with context
    prompt = prompt_template.format(
        security=security,
        quantity=quantity,
        order_pct_adv=round(order_pct, 2),
        time_in_force=time_in_force,
        history_summary=history_summary,
        adv=adv,
        volatility=volatility
    )
    
    # Call LLM
    if USE_MOCK_LLM:
        return _mock_strategy_suggestion(security, quantity, order_pct, time_in_force)
    
    try:
        response = azure_client.chat.completions.create(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are a precise execution strategist. Always return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=400
        )
        
        content = response.choices[0].message.content.strip()
        
        # Clean markdown if present
        if content.startswith("```"):
            content = re.sub(r'^```(?:json)?\s*|\s*```$', '', content, flags=re.MULTILINE).strip()
        
        result = json.loads(content)
        
        # Validate strategy
        suggested = result.get("suggested_strategy", "TWAP")
        if suggested not in ALLOWED_STRATEGIES:
            suggested = "TWAP"
        
        return {
            "suggested_strategy": suggested,
            "reasoning": result.get("reasoning", "AI-recommended strategy"),
            "warnings": result.get("warnings", []),
            "market_impact_risk": result.get("market_impact_risk", "MODERATE"),
            "behavioral_notes": result.get("behavioral_notes", "Based on historical patterns"),
            "context": {
                "adv": adv,
                "order_pct_adv": round(order_pct, 2),
                "volatility": volatility
            }
        }
        
    except Exception as e:
        print(f"LLM error: {e}")
        return _mock_strategy_suggestion(security, quantity, order_pct, time_in_force)


def _mock_strategy_suggestion(
    security: str,
    quantity: int,
    order_pct: float,
    time_in_force: str
) -> Dict[str, Any]:
    """Fallback mock suggestion"""
    # Simple rule-based logic
    if order_pct > 10:
        strategy = "VWAP"
        reasoning = f"Large order ({order_pct:.1f}% of ADV) requires VWAP to minimize market impact"
        risk = "HIGH"
    elif order_pct > 5:
        strategy = "VWAP"
        reasoning = f"Moderate-large order ({order_pct:.1f}% of ADV) benefits from VWAP execution"
        risk = "MODERATE"
    elif order_pct > 1:
        strategy = "TWAP"
        reasoning = f"Medium order ({order_pct:.1f}% of ADV) suitable for TWAP distribution"
        risk = "LOW"
    else:
        strategy = "TWAP"
        reasoning = f"Small order ({order_pct:.1f}% of ADV) can use simple TWAP or MOC"
        risk = "LOW"
    
    warnings = []
    if order_pct > 15:
        warnings.append(f"⚠️ Order is {order_pct:.1f}% of ADV - consider splitting across multiple days")
    
    return {
        "suggested_strategy": strategy,
        "reasoning": reasoning,
        "warnings": warnings,
        "market_impact_risk": risk,
        "behavioral_notes": "Rule-based recommendation (LLM unavailable)",
        "context": {
            "adv": MARKET_DATA.get(security, {}).get("adv", 1_000_000),
            "order_pct_adv": round(order_pct, 2),
            "volatility": MARKET_DATA.get(security, {}).get("recent_volatility", "MEDIUM")
        }
    }


def capture_correction(
    interaction_id: str,
    input_data: Dict[str, Any],
    ai_suggestion: Dict[str, Any],
    user_correction: Dict[str, Any]
) -> str:
    """
    Capture user correction for offline learning
    
    Args:
        interaction_id: Unique ID for this interaction
        input_data: Original input (security, quantity, etc.)
        ai_suggestion: What AI suggested
        user_correction: What user chose instead
    
    Returns:
        Path to saved correction file
    """
    # Create daily directory
    today = datetime.now().strftime("%Y-%m-%d")
    daily_dir = CORRECTIONS_DIR / today
    daily_dir.mkdir(parents=True, exist_ok=True)
    
    # Create correction record
    correction = {
        "interaction_id": interaction_id,
        "timestamp": datetime.now().isoformat(),
        "input": input_data,
        "ai_suggestion": ai_suggestion,
        "user_correction": user_correction,
        "metadata": {
            "correction_type": "strategy_suggestion",
            "version": "v1"
        }
    }
    
    # Save to JSON file
    filepath = daily_dir / f"{interaction_id}.json"
    with open(filepath, 'w') as f:
        json.dump(correction, f, indent=2)
    
    print(f"✅ Correction saved: {filepath}")
    return str(filepath)


# MCP Tool Definition
async def smart_suggestion_tool(
    security: str,
    quantity: int,
    timeInForce: str = "DAY"
) -> Dict[str, Any]:
    """
    MCP Tool: Get smart strategy suggestion
    
    Args:
        security: Security symbol (e.g., AAPL)
        quantity: Number of shares
        timeInForce: DAY, GTC, GTD, or FOK
    
    Returns:
        Strategy suggestion with reasoning
    """
    result = suggest_strategy_with_llm(security, quantity, timeInForce)
    return result
