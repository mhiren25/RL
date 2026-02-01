"""
MCP Server Configuration
Centralized config for Azure OpenAI and other settings
"""
import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CORRECTIONS_DIR = DATA_DIR / "corrections"
PROMPTS_DIR = DATA_DIR / "prompts"
ANALYSIS_DIR = DATA_DIR / "analysis"

# Ensure directories exist
CORRECTIONS_DIR.mkdir(parents=True, exist_ok=True)
PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

# Mock mode if no API key
USE_MOCK_LLM = not AZURE_OPENAI_API_KEY

# Prompt versions
CURRENT_STRATEGY_PROMPT_VERSION = os.getenv("STRATEGY_PROMPT_VERSION", "v1")

# Securities database
SECURITIES_DB = {
    'AAPL': {'symbol': 'AAPL', 'market': 'NASDAQ', 'currency': 'USD', 'name': 'Apple Inc.', 'price': 178.50},
    'GOOGL': {'symbol': 'GOOGL', 'market': 'NASDAQ', 'currency': 'USD', 'name': 'Alphabet Inc.', 'price': 140.25},
    'MSFT': {'symbol': 'MSFT', 'market': 'NASDAQ', 'currency': 'USD', 'name': 'Microsoft Corporation', 'price': 378.91},
    'TSLA': {'symbol': 'TSLA', 'market': 'NASDAQ', 'currency': 'USD', 'name': 'Tesla Inc.', 'price': 242.84},
    'NOVN': {'symbol': 'NOVN', 'market': 'SIX', 'currency': 'CHF', 'name': 'Novartis AG', 'price': 95.20},
    'NESN': {'symbol': 'NESN', 'market': 'SIX', 'currency': 'CHF', 'name': 'Nestlé S.A.', 'price': 87.45},
}

# Market data for ADV calculations
MARKET_DATA = {
    "AAPL": {"adv": 52_000_000, "recent_volatility": "LOW"},
    "MSFT": {"adv": 42_000_000, "recent_volatility": "LOW"},
    "GOOGL": {"adv": 26_000_000, "recent_volatility": "MEDIUM"},
    "TSLA": {"adv": 88_000_000, "recent_volatility": "HIGH"},
    "NOVN": {"adv": 3_200_000, "recent_volatility": "LOW"},
    "NESN": {"adv": 5_300_000, "recent_volatility": "LOW"},
}

# User trading history (for behavioral analysis)
USER_HISTORY = [
    {"symbol": "AAPL", "strategy": "VWAP", "side": "BUY", "quantity": 500, "tif": "DAY", "volatility": "LOW", "days_ago": 5},
    {"symbol": "AAPL", "strategy": "VWAP", "side": "BUY", "quantity": 750, "tif": "GTC", "volatility": "MEDIUM", "days_ago": 12},
    {"symbol": "MSFT", "strategy": "TWAP", "side": "BUY", "quantity": 200, "tif": "DAY", "volatility": "LOW", "days_ago": 3},
    {"symbol": "TSLA", "strategy": "VWAP", "side": "BUY", "quantity": 1000, "tif": "DAY", "volatility": "HIGH", "days_ago": 8},
    {"symbol": "GOOGL", "strategy": "POV", "side": "SELL", "quantity": 300, "tif": "GTC", "volatility": "MEDIUM", "days_ago": 15},
]

# Allowed strategies
ALLOWED_STRATEGIES = ["VWAP", "TWAP", "POV", "MOC"]

def get_prompt_path(prompt_type: str, version: str = None) -> Path:
    """Get path to prompt file"""
    if version is None:
        version = CURRENT_STRATEGY_PROMPT_VERSION
    return PROMPTS_DIR / f"{prompt_type}_{version}.txt"

def load_prompt(prompt_type: str, version: str = None) -> str:
    """Load prompt from file"""
    path = get_prompt_path(prompt_type, version)
    if path.exists():
        return path.read_text()
    # Fallback to v1
    v1_path = get_prompt_path(prompt_type, "v1")
    if v1_path.exists():
        return v1_path.read_text()
    return ""
