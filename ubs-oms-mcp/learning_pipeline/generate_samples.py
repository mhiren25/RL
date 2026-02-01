"""
Generate Sample Corrections for Testing
Creates realistic correction data to test the learning pipeline
"""
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import random

import sys
sys.path.append(str(Path(__file__).parent.parent / "mcp_server"))
from config import CORRECTIONS_DIR


# Sample correction scenarios
SAMPLE_SCENARIOS = [
    # Scenario 1: Users prefer VWAP for large AAPL orders
    {
        "input": {"security": "AAPL", "quantity": 5000, "timeInForce": "DAY"},
        "ai_suggestion": {"strategy": "TWAP", "reasoning": "Medium-large order suitable for TWAP"},
        "user_correction": {"strategy": "VWAP", "reason": "Client prefers VWAP for large AAPL orders"},
        "count": 5
    },
    {
        "input": {"security": "AAPL", "quantity": 8000, "timeInForce": "DAY"},
        "ai_suggestion": {"strategy": "TWAP", "reasoning": "Order size warrants time distribution"},
        "user_correction": {"strategy": "VWAP", "reason": "Always use VWAP for AAPL"},
        "count": 3
    },
    
    # Scenario 2: Users prefer POV for TSLA (high volatility)
    {
        "input": {"security": "TSLA", "quantity": 2000, "timeInForce": "DAY"},
        "ai_suggestion": {"strategy": "VWAP", "reasoning": "Large order needs VWAP"},
        "user_correction": {"strategy": "POV", "reason": "TSLA volatility requires POV to follow market"},
        "count": 4
    },
    {
        "input": {"security": "TSLA", "quantity": 3500, "timeInForce": "DAY"},
        "ai_suggestion": {"strategy": "VWAP", "reasoning": "High ADV percentage"},
        "user_correction": {"strategy": "POV", "reason": "POV better for volatile stocks"},
        "count": 3
    },
    
    # Scenario 3: MOC preferred for small orders
    {
        "input": {"security": "MSFT", "quantity": 200, "timeInForce": "DAY"},
        "ai_suggestion": {"strategy": "TWAP", "reasoning": "Small order, TWAP suitable"},
        "user_correction": {"strategy": "MOC", "reason": "Small orders go to close auction"},
        "count": 4
    },
    {
        "input": {"security": "GOOGL", "quantity": 150, "timeInForce": "DAY"},
        "ai_suggestion": {"strategy": "TWAP", "reasoning": "Low impact order"},
        "user_correction": {"strategy": "MOC", "reason": "Closing auction for small sizes"},
        "count": 3
    },
    
    # Scenario 4: GTC orders prefer VWAP
    {
        "input": {"security": "MSFT", "quantity": 1000, "timeInForce": "GTC"},
        "ai_suggestion": {"strategy": "TWAP", "reasoning": "GTC order, even distribution"},
        "user_correction": {"strategy": "VWAP", "reason": "GTC orders need VWAP for consistency"},
        "count": 2
    },
    
    # Scenario 5: Large institutional orders always VWAP
    {
        "input": {"security": "GOOGL", "quantity": 10000, "timeInForce": "DAY"},
        "ai_suggestion": {"strategy": "POV", "reasoning": "Large order with participation rate"},
        "user_correction": {"strategy": "VWAP", "reason": "Institutional mandate: all large orders use VWAP"},
        "count": 3
    }
]


def generate_corrections(scenarios: list, days_spread: int = 7):
    """
    Generate sample corrections spread over recent days
    
    Args:
        scenarios: List of correction scenarios
        days_spread: Number of days to spread corrections over
    """
    print(f"🎲 Generating sample corrections...")
    
    total_corrections = 0
    
    for scenario in scenarios:
        count = scenario.get("count", 1)
        
        for i in range(count):
            # Random day within spread
            days_ago = random.randint(0, days_spread)
            correction_date = datetime.now() - timedelta(days=days_ago)
            date_str = correction_date.strftime("%Y-%m-%d")
            
            # Create daily directory
            daily_dir = CORRECTIONS_DIR / date_str
            daily_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate unique ID
            interaction_id = str(uuid.uuid4())
            
            # Add some time variation
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)
            timestamp = correction_date.replace(
                hour=hours_ago,
                minute=minutes_ago,
                second=0
            )
            
            # Create correction record
            correction = {
                "interaction_id": interaction_id,
                "timestamp": timestamp.isoformat(),
                "input": scenario["input"],
                "ai_suggestion": scenario["ai_suggestion"],
                "user_correction": scenario["user_correction"],
                "metadata": {
                    "correction_type": "strategy_suggestion",
                    "version": "v1",
                    "sample_data": True  # Mark as sample
                }
            }
            
            # Save
            filepath = daily_dir / f"{interaction_id}.json"
            with open(filepath, 'w') as f:
                json.dump(correction, f, indent=2)
            
            total_corrections += 1
    
    print(f"✅ Generated {total_corrections} sample corrections across {days_spread} days")
    print(f"   Stored in: {CORRECTIONS_DIR}")
    
    # Show summary
    print("\n📊 Correction Summary by Strategy:")
    ai_strategies = {}
    user_strategies = {}
    
    for scenario in scenarios:
        ai = scenario["ai_suggestion"]["strategy"]
        user = scenario["user_correction"]["strategy"]
        count = scenario["count"]
        
        ai_strategies[ai] = ai_strategies.get(ai, 0) + count
        user_strategies[user] = user_strategies.get(user, 0) + count
    
    print("\n  AI Suggested:")
    for strategy, count in sorted(ai_strategies.items(), key=lambda x: -x[1]):
        print(f"    {strategy}: {count}")
    
    print("\n  Users Chose:")
    for strategy, count in sorted(user_strategies.items(), key=lambda x: -x[1]):
        print(f"    {strategy}: {count}")


if __name__ == "__main__":
    print("=" * 80)
    print("SAMPLE CORRECTION GENERATOR")
    print("=" * 80)
    print("\nThis will create realistic correction data for testing the learning pipeline.")
    print("The corrections will show patterns like:")
    print("  • Users prefer VWAP for large AAPL orders")
    print("  • POV is better for volatile stocks like TSLA")
    print("  • Small orders should go to MOC (closing auction)")
    print("  • GTC orders need VWAP for consistency")
    print("\n" + "=" * 80)
    
    response = input("\nGenerate sample corrections? (y/n): ")
    
    if response.lower() == 'y':
        generate_corrections(SAMPLE_SCENARIOS, days_spread=14)
        
        print("\n" + "=" * 80)
        print("NEXT STEPS:")
        print("=" * 80)
        print("1. Analyze corrections:")
        print("   python learning_pipeline/analyze.py")
        print("")
        print("2. Train new prompt version:")
        print("   python learning_pipeline/train.py")
        print("")
        print("3. Review and deploy:")
        print("   python learning_pipeline/deploy.py --list")
        print("   python learning_pipeline/deploy.py --version v2")
        print("=" * 80)
    else:
        print("Cancelled.")
