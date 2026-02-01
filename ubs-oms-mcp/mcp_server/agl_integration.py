"""
Agent Lightning Integration for MCP Server
Wraps strategy suggestion tool for RL training
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
import agentlightning as agl

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
AGL_STORE_DIR = PROJECT_ROOT / "data" / "agl_store"
AGL_STORE_DIR.mkdir(parents=True, exist_ok=True)

# Initialize Agent Lightning Store
# This captures all traces (prompts, responses, rewards) for later training
try:
    store = agl.FSStore(str(AGL_STORE_DIR))
    AGL_ENABLED = True
    print("✅ Agent Lightning store initialized")
except Exception as e:
    print(f"⚠️ Agent Lightning not available: {e}")
    AGL_ENABLED = False
    store = None


def emit_strategy_suggestion(
    rollout_id: str,
    task_input: Dict[str, Any],
    ai_suggestion: Dict[str, Any],
    reward: Optional[float] = None
) -> None:
    """
    Emit a strategy suggestion event to Agent Lightning for RL training
    
    Args:
        rollout_id: Unique ID for this interaction
        task_input: Input data (security, quantity, etc.)
        ai_suggestion: AI's suggested strategy
        reward: Reward signal (0-1), where:
            - 1.0 = user accepted AI suggestion
            - 0.0 = user rejected and chose different strategy
            - None = no user feedback yet
    
    Example:
        emit_strategy_suggestion(
            rollout_id="uuid",
            task_input={"security": "AAPL", "quantity": 5000},
            ai_suggestion={"strategy": "TWAP", "reasoning": "..."},
            reward=0.0  # User chose VWAP instead
        )
    """
    if not AGL_ENABLED or store is None:
        return
    
    try:
        # Create a span (trace) for this interaction
        with store.span(
            name="strategy_suggestion",
            rollout_id=rollout_id,
            metadata={
                "task": task_input,
                "ai_output": ai_suggestion
            }
        ) as span:
            # Emit prompt (what we asked the LLM)
            agl.emit_prompt(
                span=span,
                messages=[{
                    "role": "user",
                    "content": f"Suggest strategy for {task_input}"
                }]
            )
            
            # Emit response (what LLM suggested)
            agl.emit_completion(
                span=span,
                completion={
                    "strategy": ai_suggestion.get("suggested_strategy"),
                    "reasoning": ai_suggestion.get("reasoning")
                }
            )
            
            # Emit reward if available
            if reward is not None:
                agl.emit_reward(
                    span=span,
                    reward=reward
                )
    
    except Exception as e:
        print(f"⚠️ Error emitting to Agent Lightning: {e}")


def calculate_reward(
    ai_suggestion: Dict[str, Any],
    user_correction: Optional[Dict[str, Any]]
) -> float:
    """
    Calculate reward signal from user correction
    
    Args:
        ai_suggestion: What AI suggested
        user_correction: What user chose (None if accepted AI)
    
    Returns:
        Reward between 0.0 and 1.0
    """
    if user_correction is None:
        # User accepted AI suggestion
        return 1.0
    
    ai_strategy = ai_suggestion.get("suggested_strategy", "").upper()
    user_strategy = user_correction.get("strategy", "").upper()
    
    if ai_strategy == user_strategy:
        # User chose same strategy (reinforces AI)
        return 1.0
    else:
        # User chose different strategy (penalty)
        return 0.0


def update_reward_for_correction(
    rollout_id: str,
    user_correction: Dict[str, Any]
) -> None:
    """
    Update reward signal when user provides correction
    
    This is called AFTER user corrects the AI suggestion
    
    Args:
        rollout_id: Original interaction ID
        user_correction: User's correction data
    """
    if not AGL_ENABLED or store is None:
        return
    
    try:
        # Find the original span
        spans = store.query_spans(rollout_id=rollout_id)
        
        if spans:
            # Update with reward
            for span in spans:
                if span.name == "strategy_suggestion":
                    # Calculate reward based on correction
                    original_ai = span.metadata.get("ai_output", {})
                    reward = calculate_reward(original_ai, user_correction)
                    
                    # Update span with reward
                    agl.emit_reward(span=span, reward=reward)
                    
                    print(f"✅ Updated reward for {rollout_id}: {reward}")
    
    except Exception as e:
        print(f"⚠️ Error updating reward: {e}")


def get_training_ready_count() -> int:
    """
    Get count of interactions ready for training
    (interactions with rewards assigned)
    
    Returns:
        Number of training-ready interactions
    """
    if not AGL_ENABLED or store is None:
        return 0
    
    try:
        # Query all spans with rewards
        spans = store.query_spans(has_reward=True)
        return len(spans)
    except:
        return 0


# Export for use in other modules
__all__ = [
    'AGL_ENABLED',
    'store',
    'emit_strategy_suggestion',
    'update_reward_for_correction',
    'calculate_reward',
    'get_training_ready_count'
]
