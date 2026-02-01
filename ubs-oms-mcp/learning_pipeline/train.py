"""
Offline Learning Pipeline - Training
Updates prompts with few-shot examples from corrections
"""
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

import sys
sys.path.append(str(Path(__file__).parent.parent / "mcp_server"))
from config import PROMPTS_DIR, load_prompt

from analyze import load_corrections, analyze_strategy_corrections


def generate_few_shot_examples(patterns: List[Dict[str, Any]]) -> List[str]:
    """
    Generate few-shot examples from correction patterns
    
    Args:
        patterns: Identified patterns from analysis
    
    Returns:
        List of few-shot example strings
    """
    examples = []
    
    for pattern in patterns:
        if pattern["type"] == "security_specific":
            # Add security-specific example
            security = pattern["security"]
            strategy = pattern["preferred_strategy"]
            
            example = f"""
Example (based on {pattern['frequency']} user corrections):
- Security: {security}
- Historical user preference: {strategy}
- Reason: Users consistently choose {strategy} for {security} orders
→ Recommended: {strategy}
"""
            examples.append(example.strip())
        
        elif pattern["type"] == "frequent_correction":
            # Add correction pair example
            pair = pattern["correction_pair"]
            
            example = f"""
Example (based on {pair['frequency']} user corrections):
- AI initially suggested: {pair['ai_suggested']}
- Users preferred: {pair['user_chose']} ({pair['percentage']}% of corrections)
- Learning: In similar scenarios, favor {pair['user_chose']} over {pair['ai_suggested']}
"""
            examples.append(example.strip())
        
        elif pattern["type"] == "order_size_threshold":
            # Add order size example
            strategy = pattern["strategy"]
            avg_size = pattern["avg_order_size"]
            
            example = f"""
Example (based on {pattern['sample_count']} user corrections):
- Order size: ~{avg_size:,.0f} shares
- User preference: {strategy}
- Learning: Orders around this size should use {strategy}
"""
            examples.append(example.strip())
    
    return examples


def create_updated_prompt(
    base_prompt: str,
    few_shot_examples: List[str],
    insights: List[str]
) -> str:
    """
    Create updated prompt with few-shot examples
    
    Args:
        base_prompt: Original prompt template
        few_shot_examples: Generated examples
        insights: Additional insights
    
    Returns:
        Updated prompt text
    """
    # Find where to insert examples (before "Return ONLY valid JSON")
    insert_marker = "Return ONLY valid JSON"
    
    if insert_marker in base_prompt:
        parts = base_prompt.split(insert_marker, 1)
        
        # Build few-shot section
        few_shot_section = []
        
        if few_shot_examples:
            few_shot_section.append("\n")
            few_shot_section.append("=" * 80)
            few_shot_section.append("LEARNED FROM USER CORRECTIONS (Few-Shot Examples):")
            few_shot_section.append("=" * 80)
            
            for i, example in enumerate(few_shot_examples, 1):
                few_shot_section.append(f"\n[Example {i}]")
                few_shot_section.append(example)
        
        if insights:
            few_shot_section.append("\n")
            few_shot_section.append("Key Insights from Corrections:")
            for insight in insights:
                few_shot_section.append(f"- {insight}")
        
        few_shot_section.append("\n")
        few_shot_section.append("=" * 80)
        few_shot_section.append("")
        
        # Combine
        updated = parts[0] + "\n".join(few_shot_section) + "\n" + insert_marker + parts[1]
        return updated
    
    # Fallback: append to end
    updated = base_prompt + "\n\n" + "\n".join(few_shot_examples)
    return updated


def train_and_generate_new_prompt(min_corrections: int = 3) -> Dict[str, Any]:
    """
    Main training function - analyze corrections and generate new prompt
    
    Args:
        min_corrections: Minimum corrections required to generate new prompt
    
    Returns:
        Training results
    """
    print("🎓 Starting training pipeline...")
    
    # Load and analyze corrections
    corrections = load_corrections(days=30)
    print(f"📊 Loaded {len(corrections)} corrections")
    
    if len(corrections) < min_corrections:
        return {
            "success": False,
            "message": f"Not enough corrections ({len(corrections)}). Need at least {min_corrections}.",
            "corrections_count": len(corrections)
        }
    
    analysis = analyze_strategy_corrections(corrections)
    
    if analysis["total_corrections"] < min_corrections:
        return {
            "success": False,
            "message": f"Not enough strategy corrections ({analysis['total_corrections']}). Need at least {min_corrections}.",
            "corrections_count": analysis["total_corrections"]
        }
    
    print(f"✨ Found {len(analysis['patterns'])} patterns")
    
    # Generate few-shot examples
    few_shot_examples = generate_few_shot_examples(analysis["patterns"])
    
    # Extract insights
    insights = [p["insight"] for p in analysis["patterns"]]
    
    # Load current prompt
    current_version = "v1"
    current_prompt = load_prompt("strategy", current_version)
    
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
    
    # Create updated prompt
    updated_prompt = create_updated_prompt(current_prompt, few_shot_examples, insights)
    
    # Save new version
    new_prompt_path = PROMPTS_DIR / f"strategy_{new_version}.txt"
    new_prompt_path.write_text(updated_prompt)
    
    # Save metadata
    metadata = {
        "version": new_version,
        "created_at": datetime.now().isoformat(),
        "based_on": current_version,
        "corrections_analyzed": analysis["total_corrections"],
        "patterns_found": len(analysis["patterns"]),
        "few_shot_examples": len(few_shot_examples),
        "insights": insights,
        "analysis_summary": {
            "ai_strategy_counts": analysis["ai_strategy_counts"],
            "user_strategy_counts": analysis["user_strategy_counts"],
            "top_corrections": analysis["correction_pairs"][:5]
        }
    }
    
    metadata_path = PROMPTS_DIR / f"strategy_{new_version}_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"✅ New prompt version created: {new_version}")
    print(f"   Prompt: {new_prompt_path}")
    print(f"   Metadata: {metadata_path}")
    
    return {
        "success": True,
        "new_version": new_version,
        "prompt_path": str(new_prompt_path),
        "metadata_path": str(metadata_path),
        "corrections_analyzed": analysis["total_corrections"],
        "patterns_found": len(analysis["patterns"]),
        "few_shot_examples_added": len(few_shot_examples),
        "insights": insights
    }


if __name__ == "__main__":
    result = train_and_generate_new_prompt(min_corrections=3)
    
    if result["success"]:
        print("\n" + "=" * 80)
        print("TRAINING COMPLETE!")
        print("=" * 80)
        print(f"New Version: {result['new_version']}")
        print(f"Corrections Analyzed: {result['corrections_analyzed']}")
        print(f"Patterns Found: {result['patterns_found']}")
        print(f"Few-Shot Examples Added: {result['few_shot_examples_added']}")
        print("\nInsights:")
        for insight in result["insights"]:
            print(f"  • {insight}")
        print("\n" + "=" * 80)
        print(f"\n📝 Review the new prompt at: {result['prompt_path']}")
        print(f"📊 Review metadata at: {result['metadata_path']}")
        print(f"\n💡 To deploy: python learning_pipeline/deploy.py --version {result['new_version']}")
    else:
        print(f"\n⚠️  {result['message']}")
