"""
Pydantic Models for FastAPI Gateway
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import date
from enum import Enum


class TimeInForce(str, Enum):
    DAY = "DAY"
    GTD = "GTD"
    GTC = "GTC"
    FOK = "FOK"


class ContactMethod(str, Enum):
    PHONE = "phone"
    EMAIL = "email"
    MEETING = "meeting"
    PORTAL = "portal"


class SecurityInfo(BaseModel):
    symbol: str
    market: str
    currency: str
    name: str
    price: float


class OrderFormModel(BaseModel):
    security: Optional[SecurityInfo] = None
    contact_method: ContactMethod = ContactMethod.PHONE
    quantity: Optional[int] = None
    price: Optional[float] = None
    time_in_force: TimeInForce = TimeInForce.DAY
    gtd_date: Optional[date] = None
    trader_text: str = ""
    requested_strategy: Optional[str] = None


class AlgoType(str, Enum):
    VWAP = "vwap"
    TWAP = "twap"
    POV = "pov"
    MOC = "moc"


class TraderTextParsed(BaseModel):
    structured: str
    backend_format: str
    description: str
    algo: Optional[AlgoType] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    confidence: float
    reasoning: str


class NaturalLanguageOrderRequest(BaseModel):
    text: str


class TraderTextRequest(BaseModel):
    text: str
    context: Optional[Dict[str, Any]] = None


class AutocompleteRequest(BaseModel):
    text: str


class SmartSuggestionRequest(BaseModel):
    security: str
    quantity: int
    timeInForce: str = "DAY"


class SmartSuggestionResponse(BaseModel):
    suggested_strategy: str
    reasoning: str
    warnings: List[str]
    market_impact_risk: str
    behavioral_notes: str
    context: Optional[Dict[str, Any]] = None


class CorrectionRequest(BaseModel):
    """Request to capture a user correction"""
    interaction_id: str
    input_data: Dict[str, Any]
    ai_suggestion: Dict[str, Any]
    user_correction: Dict[str, Any]


class CorrectionResponse(BaseModel):
    """Response after capturing correction"""
    success: bool
    filepath: str
    message: str
