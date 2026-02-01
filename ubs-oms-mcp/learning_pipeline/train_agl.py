"""
Offline RL Training with Agent Lightning
Uses APO (Automatic Prompt Optimization) or VERL for batch training
"""
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import agentlightning as agl

# Add parent to path
import sys
sys.path.append(str(Path(__file__).parent.parent / "mcp_server"))
from agl_integration import store, AGL_ENABLED
from config import PROMPTS_DIR, ANALYSIS_DIR

# Also load from old corrections for backwards compatibility
from config import CORRECTIONS_DIR


def load_corrections_into_agl_store() -> int:
    """
    Load existing JSON corrections into Agent Lightning store
    This migrates old correction format to AGL format
    
    Returns:
        Number of corrections loaded
    """
    if not AGL_ENABLED:
        print("❌ Agent Lightning not enabled")
        return 0
    
    count = 0
    
    # Iterate through daily directories
    for daily_dir in CORRECTIONS_DIR.iterdir():
        if not daily_dir.is_dir():
            continue
        
        # Load all JSON files
        for json_file in daily_dir.glob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    correction = json.load(f)
                
                # Extract data
                interaction_id = correction.get("interaction_id")
                input_data = correction.get("input", {})
                ai_suggestion = correction.get("ai_suggestion", {})
                user_correction = correction.get("user_correction", {})
                
                # Create span in AGL store
                with store.span(
                    name="strategy_suggestion",
                    rollout_id=interaction_id,
                    metadata={
                        "task": input_data,
                        "ai_output": ai_suggestion,
                        "timestamp": correction.get("timestamp")
                    }
                ) as span:
                    # Emit prompt
                    agl.emit_prompt(
                        span=span,
                        messages=[{
                            "role": "user",
                            "content": f"Security: {input_data.get('security')}, Quantity: {input_data.get('quantity')}"
                        }]
                    )
                    
                    # Emit completion
                    agl.emit_completion(
                        span=span,
                        completion={
                            "strategy": ai_suggestion.get("strategy"),
                            "reasoning": ai_suggestion.get("reasoning", "")
                        }
                    )
                    
                    # Calculate reward
                    ai_strat = ai_suggestion.get("strategy", "").upper()
                    user_strat = user_correction.get("strategy", "").upper()
                    reward = 1.0 if ai_strat == user_strat else 0.0
                    
                    # Emit reward
                    agl.emit_reward(span=span, reward=reward)
                
                count += 1
                
            except Exception as e:
                print(f"⚠️  Error loading {json_file}: {e}")
    
    print(f"✅ Loaded {count} corrections into Agent Lightning store")
    return count


def analyze_agl_data() -> Dict[str, Any]:
    """
    Analyze Agent Lightning store data
    
    Returns:
        Analysis results
    """
    if not AGL_ENABLED:
        return {"error": "Agent Lightning not enabled"}
    
    # Query all spans
    all_spans = store.query_spans()
    rewarded_spans = store.query_spans(has_reward=True)
    
    # Calculate statistics
    total_interactions = len(all_spans)
    rewarded_interactions = len(rewarded_spans)
    
    if rewarded_interactions == 0:
        return {
            "total_interactions": total_interactions,
            "rewarded_interactions": 0,
            "average_reward": 0.0,
            "ready_for_training": False,
            "message": "No rewarded interactions yet. Need user corrections."
        }
    
    # Calculate average reward
    rewards = [span.reward for span in rewarded_spans if hasattr(span, 'reward')]
    avg_reward = sum(rewards) / len(rewards) if rewards else 0.0
    
    # Extract strategies
    ai_strategies = []
    user_strategies = []
    
    for span in rewarded_spans:
        metadata = span.metadata or {}
        ai_output = metadata.get("ai_output", {})
        
        if ai_output:
            ai_strategies.append(ai_output.get("strategy"))
        
        # User strategy would be in correction data
        # For now, infer from reward (1.0 = same, 0.0 = different)
        if hasattr(span, 'reward'):
            if span.reward < 0.5:
                # User chose different strategy
                # (we'd need to store this explicitly in real implementation)
                pass
    
    return {
        "total_interactions": total_interactions,
        "rewarded_interactions": rewarded_interactions,
        "average_reward": round(avg_reward, 3),
        "reward_distribution": {
            "accepted": sum(1 for r in rewards if r > 0.5),
            "rejected": sum(1 for r in rewards if r <= 0.5)
        },
        "ready_for_training": rewarded_interactions >= 10,
        "recommendation": "Ready for training!" if rewarded_interactions >= 10 else f"Need {10 - rewarded_interactions} more corrections"
    }


def train_with_apo(
    algorithm_config: Dict[str, Any] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Train using APO (Automatic Prompt Optimization)
    This is CPU-only, lightweight, perfect for offline batch training
    
    Args:
        algorithm_config: APO configuration
        dry_run: If True, analyze but don't train
    
    Returns:
        Training results
    """
    if not AGL_ENABLED:
        return {"error": "Agent Lightning not enabled"}
    
    print("🎓 Starting APO training...")
    
    # Analyze first
    analysis = analyze_agl_data()
    print(f"📊 Analysis: {json.dumps(analysis, indent=2)}")
    
    if not analysis.get("ready_for_training"):
        return {
            "success": False,
            "message": analysis.get("recommendation"),
            "analysis": analysis
        }
    
    if dry_run:
        print("🔍 Dry run - stopping before training")
        return {
            "success": True,
            "dry_run": True,
            "analysis": analysis,
            "message": "Ready for training. Run without --dry-run to proceed."
        }
    
    # Configure APO algorithm
    if algorithm_config is None:
        algorithm_config = {
            "num_rounds": 3,  # Number of optimization rounds
            "num_samples_per_round": 5,  # Samples to generate per round
            "temperature": 0.7
        }
    
    try:
        # Create APO algorithm instance
        apo = agl.APO(
            store=store,
            **algorithm_config
        )
        
        # Create trainer
        trainer = agl.Trainer(
            algorithm=apo,
            store=store
        )
        
        # Run training
        print("⚡ Running APO training...")
        results = trainer.train()
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = ANALYSIS_DIR / f"apo_training_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "algorithm": "APO",
                "config": algorithm_config,
                "results": str(results),  # Convert to string for JSON
                "analysis": analysis
            }, f, indent=2)
        
        print(f"✅ Training complete! Results saved to: {results_file}")
        
        # Extract improved prompt from results
        # (APO will have generated improved prompts)
        improved_prompt = extract_improved_prompt_from_apo(results)
        
        # Save as new prompt version
        if improved_prompt:
            save_new_prompt_version(improved_prompt, "apo", analysis)
        
        return {
            "success": True,
            "algorithm": "APO",
            "results_file": str(results_file),
            "analysis": analysis,
            "improved_prompt_available": improved_prompt is not None
        }
    
    except Exception as e:
        print(f"❌ Training error: {e}")
        return {
            "success": False,
            "error": str(e),
            "analysis": analysis
        }


def extract_improved_prompt_from_apo(results: Any) -> str:
    """
    Extract improved prompt from APO training results
    
    Args:
        results: APO training results
    
    Returns:
        Improved prompt text
    """
    # APO stores improved prompts in resources
    # This is a simplified extraction - real implementation would parse APO results
    try:
        if hasattr(results, 'resources'):
            for resource in results.resources:
                if resource.type == "prompt":
                    return resource.content
    except:
        pass
    
    return None


def save_new_prompt_version(
    improved_prompt: str,
    method: str,
    analysis: Dict[str, Any]
) -> str:
    """
    Save improved prompt as new version
    
    Args:
        improved_prompt: New prompt text
        method: Training method used (apo, verl, etc.)
        analysis: Training analysis data
    
    Returns:
        Path to new prompt file
    """
    # Determine new version number
    existing_versions = list(PROMPTS_DIR.glob("strategy_v*.txt"))
    version_numbers = []
    for v in existing_versions:
        try:
            num = int(v.stem.split("_v")[1])
            version_numbers.append(num)
        except:
            pass
    
    new_version_num = max(version_numbers, default=0) + 1
    new_version = f"v{new_version_num}"
    
    # Save prompt
    prompt_file = PROMPTS_DIR / f"strategy_{new_version}.txt"
    prompt_file.write_text(improved_prompt)
    
    # Save metadata
    metadata = {
        "version": new_version,
        "created_at": datetime.now().isoformat(),
        "training_method": method,
        "analysis": analysis,
        "note": "Generated by Agent Lightning offline training"
    }
    
    metadata_file = PROMPTS_DIR / f"strategy_{new_version}_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"✅ Saved new prompt: {new_version}")
    print(f"   Prompt: {prompt_file}")
    print(f"   Metadata: {metadata_file}")
    
    return str(prompt_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train with Agent Lightning")
    parser.add_argument("--migrate", action="store_true", help="Migrate old corrections to AGL store")
    parser.add_argument("--analyze", action="store_true", help="Analyze AGL data")
    parser.add_argument("--train", action="store_true", help="Run APO training")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (analyze only)")
    parser.add_argument("--algorithm", choices=["apo", "verl"], default="apo", help="Training algorithm")
    
    args = parser.parse_args()
    
    if args.migrate:
        print("📦 Migrating corrections to Agent Lightning store...")
        count = load_corrections_into_agl_store()
        print(f"✅ Migrated {count} corrections")
    
    elif args.analyze:
        print("📊 Analyzing Agent Lightning data...")
        analysis = analyze_agl_data()
        print(json.dumps(analysis, indent=2))
    
    elif args.train:
        if args.algorithm == "apo":
            result = train_with_apo(dry_run=args.dry_run)
            print(json.dumps(result, indent=2))
        elif args.algorithm == "verl":
            print("❌ VERL training requires GPU setup. Use APO for CPU-only training.")
    
    else:
        parser.print_help()
