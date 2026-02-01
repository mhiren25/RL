"""
UBS OMS FastAPI Gateway
Routes HTTP requests to MCP server and captures corrections
"""
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from models import (
    OrderFormModel,
    TraderTextParsed,
    SmartSuggestionResponse,
    NaturalLanguageOrderRequest,
    TraderTextRequest,
    AutocompleteRequest,
    SmartSuggestionRequest,
    CorrectionRequest,
    CorrectionResponse,
    SecurityInfo,
    TimeInForce,
    ContactMethod,
    AlgoType
)
from mcp_client import get_mcp_client

# Import correction capture from MCP server
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "mcp_server"))
from tools.strategy import capture_correction


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager - connect/disconnect MCP client"""
    mcp = get_mcp_client()
    await mcp.connect()
    print("✅ FastAPI Gateway started, MCP client connected")
    yield
    await mcp.close()
    print("👋 FastAPI Gateway shutting down")


app = FastAPI(
    title="UBS OMS Gateway API",
    version="4.0.0-MCP",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Health check"""
    return {
        "service": "UBS OMS Gateway API",
        "version": "4.0.0-MCP",
        "status": "operational",
        "architecture": "FastAPI → MCP Server → Azure OpenAI",
        "features": {
            "mcp_protocol": True,
            "vendor_agnostic": True,
            "offline_learning": True,
            "correction_capture": True
        }
    }


@app.post("/api/parse-order", response_model=OrderFormModel)
async def parse_order_endpoint(request: NaturalLanguageOrderRequest):
    """
    Parse natural language order via MCP server
    
    Example: "Buy 100 shares of AAPL as a GTC order"
    """
    try:
        mcp = get_mcp_client()
        result = await mcp.parse_order(request.text)
        
        # Map to OrderFormModel
        security = None
        if result.get("security"):
            sec_data = result["security"]
            security = SecurityInfo(**sec_data)
        
        return OrderFormModel(
            security=security,
            quantity=result.get("quantity"),
            price=result.get("price"),
            time_in_force=TimeInForce(result.get("tif", "DAY")),
            contact_method=ContactMethod.PHONE,
            trader_text="",
            requested_strategy=result.get("requested_strategy")
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parse order error: {str(e)}")


@app.post("/api/parse-trader-text", response_model=TraderTextParsed)
async def parse_trader_text_endpoint(request: TraderTextRequest):
    """
    Parse trader execution instructions via MCP server
    
    Example: "VWAP Market Close" → structured format
    """
    try:
        mcp = get_mcp_client()
        result = await mcp.parse_trader_text(request.text, request.context)
        
        return TraderTextParsed(
            structured=result.get("structured", request.text),
            backend_format=result.get("backend_format", f"CUSTOM|{request.text}"),
            description=result.get("description", "Custom execution"),
            algo=AlgoType(result["algo"]) if result.get("algo") else None,
            parameters=result.get("parameters", {}),
            confidence=result.get("confidence", 0.5),
            reasoning=result.get("reasoning", "Parsed via MCP")
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parse trader text error: {str(e)}")


@app.post("/api/smart-suggestion", response_model=SmartSuggestionResponse)
async def smart_suggestion_endpoint(request: SmartSuggestionRequest):
    """
    Get smart strategy suggestion via MCP server
    
    This endpoint generates an AI suggestion that can later be corrected by the user.
    Corrections are captured for offline learning.
    """
    try:
        mcp = get_mcp_client()
        result = await mcp.smart_suggestion(
            security=request.security,
            quantity=request.quantity,
            time_in_force=request.timeInForce
        )
        
        return SmartSuggestionResponse(
            suggested_strategy=result.get("suggested_strategy", "TWAP"),
            reasoning=result.get("reasoning", "AI recommendation"),
            warnings=result.get("warnings", []),
            market_impact_risk=result.get("market_impact_risk", "MODERATE"),
            behavioral_notes=result.get("behavioral_notes", "Based on historical patterns"),
            context=result.get("context")
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Smart suggestion error: {str(e)}")


@app.post("/api/capture-correction", response_model=CorrectionResponse)
async def capture_correction_endpoint(request: CorrectionRequest):
    """
    Capture user correction for offline learning
    
    When user corrects an AI suggestion, this endpoint saves it for future training.
    
    Request body:
    {
      "interaction_id": "uuid",
      "input_data": {"security": "AAPL", "quantity": 1000, "timeInForce": "DAY"},
      "ai_suggestion": {"strategy": "TWAP", "reasoning": "..."},
      "user_correction": {"strategy": "VWAP", "reason": "Client prefers VWAP"}
    }
    """
    try:
        filepath = capture_correction(
            interaction_id=request.interaction_id,
            input_data=request.input_data,
            ai_suggestion=request.ai_suggestion,
            user_correction=request.user_correction
        )
        
        return CorrectionResponse(
            success=True,
            filepath=filepath,
            message=f"Correction captured successfully: {filepath}"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Capture correction error: {str(e)}")


@app.post("/api/autocomplete")
async def autocomplete_endpoint(request: AutocompleteRequest):
    """Get autocomplete suggestions via MCP server"""
    try:
        mcp = get_mcp_client()
        suggestions = await mcp.autocomplete(request.text)
        return suggestions
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Autocomplete error: {str(e)}")


@app.get("/api/securities")
async def get_securities():
    """Get all securities via MCP server"""
    try:
        mcp = get_mcp_client()
        securities = await mcp.get_securities()
        return securities
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Get securities error: {str(e)}")


@app.get("/api/securities/{symbol}")
async def get_security(symbol: str):
    """Get specific security via MCP server"""
    try:
        mcp = get_mcp_client()
        security = await mcp.get_security(symbol)
        
        if "error" in security:
            raise HTTPException(status_code=404, detail=security["error"])
        
        return security
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Get security error: {str(e)}")


@app.get("/api/health")
async def health_check():
    """Detailed health check"""
    try:
        mcp = get_mcp_client()
        
        # Test MCP connection
        securities = await mcp.get_securities()
        
        return {
            "status": "healthy",
            "mcp_server": "connected",
            "securities_count": len(securities),
            "features": {
                "vendor_agnostic": True,
                "offline_learning": True,
                "correction_capture": True
            }
        }
    
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
            "mcp_server": "disconnected"
        }


# ============================================================================
# CORRECTION HELPER ENDPOINT (for frontend convenience)
# ============================================================================

@app.post("/api/correction/strategy")
async def quick_strategy_correction(
    security: str,
    quantity: int,
    timeInForce: str,
    ai_strategy: str,
    ai_reasoning: str,
    user_strategy: str,
    user_reason: str
):
    """
    Simplified endpoint for capturing strategy corrections from frontend
    
    Example usage in frontend:
    ```javascript
    await fetch('/api/correction/strategy', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        security: 'AAPL',
        quantity: 1000,
        timeInForce: 'DAY',
        ai_strategy: 'TWAP',
        ai_reasoning: 'Medium order suitable for TWAP',
        user_strategy: 'VWAP',
        user_reason: 'Client explicitly requested VWAP'
      })
    })
    ```
    """
    try:
        interaction_id = str(uuid.uuid4())
        
        filepath = capture_correction(
            interaction_id=interaction_id,
            input_data={
                "security": security,
                "quantity": quantity,
                "timeInForce": timeInForce
            },
            ai_suggestion={
                "strategy": ai_strategy,
                "reasoning": ai_reasoning
            },
            user_correction={
                "strategy": user_strategy,
                "reason": user_reason
            }
        )
        
        return {
            "success": True,
            "interaction_id": interaction_id,
            "filepath": filepath,
            "message": "Strategy correction captured for offline learning"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Strategy correction error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    print("🚀 UBS OMS FastAPI Gateway starting...")
    print("📡 Connecting to MCP server...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
