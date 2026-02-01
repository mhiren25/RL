"""
Offline Learning Pipeline - Analysis
Analyzes captured corrections to identify patterns
"""
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
from collections import Counter, defaultdict
import pandas as pd

# Add parent to path
import sys
sys.path.append(str(Path(__file__).parent.parent / "mcp_server"))
from config import CORRECTIONS_DIR, ANALYSIS_DIR


def load_corrections(days: int = 30) -> List[Dict[str, Any]]:
    """
    Load all corrections from the last N days
    
    Args:
        days: Number of days to look back
    
    Returns:
        List of correction records
    """
    corrections = []
    cutoff_date = datetime.now() - timedelta(days=days)
    
    # Iterate through daily directories
    for daily_dir in CORRECTIONS_DIR.iterdir():
        if not daily_dir.is_dir():
            continue
        
        try:
            dir_date = datetime.strptime(daily_dir.name, "%Y-%m-%d")
            if dir_date < cutoff_date:
                continue
        except ValueError:
            continue
        
        # Load all JSON files in this directory
        for json_file in daily_dir.glob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    correction = json.load(f)
                    corrections.append(correction)
            except Exception as e:
                print(f"⚠️  Error loading {json_file}: {e}")
    
    return corrections


def analyze_strategy_corrections(corrections: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze strategy correction patterns
    
    Returns:
        Analysis results with patterns and insights
    """
    if not corrections:
        return {
            "total_corrections": 0,
            "message": "No corrections found. System is either perfect or needs more usage! 🎯"
        }
    
    # Filter to strategy corrections only
    strategy_corrections = [
        c for c in corrections
        if c.get("metadata", {}).get("correction_type") == "strategy_suggestion"
    ]
    
    if not strategy_corrections:
        return {
            "total_corrections": 0,
            "message": "No strategy corrections found."
        }
    
    # Extract patterns
    ai_strategies = []
    user_strategies = []
    securities = []
    order_sizes = []
    ai_to_user_map = defaultdict(list)
    
    for corr in strategy_corrections:
        ai_strat = corr.get("ai_suggestion", {}).get("strategy")
        user_strat = corr.get("user_correction", {}).get("strategy")
        security = corr.get("input", {}).get("security")
        quantity = corr.get("input", {}).get("quantity")
        
        if ai_strat and user_strat:
            ai_strategies.append(ai_strat)
            user_strategies.append(user_strat)
            ai_to_user_map[ai_strat].append(user_strat)
        
        if security:
            securities.append(security)
        
        if quantity:
            order_sizes.append(quantity)
    
    # Calculate statistics
    total = len(strategy_corrections)
    
    # Most corrected AI strategies
    ai_strategy_counts = Counter(ai_strategies)
    
    # User preferences
    user_strategy_counts = Counter(user_strategies)
    
    # Correction pairs (AI → User)
    correction_pairs = []
    for ai_strat, user_strats in ai_to_user_map.items():
        user_count = Counter(user_strats)
        for user_strat, count in user_count.most_common():
            correction_pairs.append({
                "ai_suggested": ai_strat,
                "user_chose": user_strat,
                "frequency": count,
                "percentage": round((count / total) * 100, 1)
            })
    
    correction_pairs.sort(key=lambda x: x["frequency"], reverse=True)
    
    # Securities with most corrections
    security_counts = Counter(securities)
    
    # Order size analysis
    if order_sizes:
        avg_size = sum(order_sizes) / len(order_sizes)
        max_size = max(order_sizes)
        min_size = min(order_sizes)
    else:
        avg_size = max_size = min_size = 0
    
    # Patterns and insights
    patterns = []
    
    # Pattern 1: Frequent AI → User corrections
    if correction_pairs:
        top_correction = correction_pairs[0]
        if top_correction["frequency"] >= 3:
            patterns.append({
                "type": "frequent_correction",
                "insight": f"AI frequently suggests {top_correction['ai_suggested']} but "
                          f"users prefer {top_correction['user_chose']} ({top_correction['frequency']} times)",
                "action": f"Consider defaulting to {top_correction['user_chose']} in similar scenarios",
                "correction_pair": top_correction
            })
    
    # Pattern 2: Security-specific preferences
    for security, count in security_counts.most_common(3):
        if count >= 2:
            # Find what users prefer for this security
            sec_corrections = [
                c for c in strategy_corrections
                if c.get("input", {}).get("security") == security
            ]
            user_prefs = [
                c.get("user_correction", {}).get("strategy")
                for c in sec_corrections
                if c.get("user_correction", {}).get("strategy")
            ]
            
            if user_prefs:
                most_common_pref = Counter(user_prefs).most_common(1)[0]
                patterns.append({
                    "type": "security_specific",
                    "insight": f"For {security}, users prefer {most_common_pref[0]} "
                              f"({most_common_pref[1]}/{count} corrections)",
                    "action": f"Add few-shot example: '{security} orders → {most_common_pref[0]}'",
                    "security": security,
                    "preferred_strategy": most_common_pref[0],
                    "frequency": most_common_pref[1]
                })
    
    # Pattern 3: Order size thresholds
    if len(order_sizes) >= 5:
        # Group by corrected strategy
        size_by_strategy = defaultdict(list)
        for corr in strategy_corrections:
            user_strat = corr.get("user_correction", {}).get("strategy")
            quantity = corr.get("input", {}).get("quantity")
            if user_strat and quantity:
                size_by_strategy[user_strat].append(quantity)
        
        for strategy, sizes in size_by_strategy.items():
            if len(sizes) >= 2:
                avg = sum(sizes) / len(sizes)
                patterns.append({
                    "type": "order_size_threshold",
                    "insight": f"Users choose {strategy} for orders averaging {avg:,.0f} shares",
                    "action": f"Adjust ADV thresholds to favor {strategy} around this size",
                    "strategy": strategy,
                    "avg_order_size": avg,
                    "sample_count": len(sizes)
                })
    
    return {
        "total_corrections": total,
        "ai_strategy_counts": dict(ai_strategy_counts),
        "user_strategy_counts": dict(user_strategy_counts),
        "correction_pairs": correction_pairs,
        "security_counts": dict(security_counts.most_common(10)),
        "order_size_stats": {
            "average": round(avg_size, 0),
            "max": max_size,
            "min": min_size,
            "count": len(order_sizes)
        },
        "patterns": patterns,
        "insights_count": len(patterns)
    }


def generate_report(analysis: Dict[str, Any], output_path: Path = None) -> str:
    """
    Generate human-readable analysis report
    
    Args:
        analysis: Analysis results
        output_path: Optional path to save report
    
    Returns:
        Report text
    """
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = ANALYSIS_DIR / f"analysis_{timestamp}.txt"
    
    lines = []
    lines.append("=" * 80)
    lines.append("UBS OMS - CORRECTION ANALYSIS REPORT")
    lines.append("=" * 80)
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Total Corrections: {analysis['total_corrections']}")
    lines.append("")
    
    if analysis["total_corrections"] == 0:
        lines.append(analysis.get("message", "No data available"))
        report_text = "\n".join(lines)
        output_path.write_text(report_text)
        return report_text
    
    # AI Strategy Distribution
    lines.append("─" * 80)
    lines.append("AI STRATEGY DISTRIBUTION (What AI Suggested)")
    lines.append("─" * 80)
    for strategy, count in sorted(analysis["ai_strategy_counts"].items(), key=lambda x: -x[1]):
        pct = (count / analysis["total_corrections"]) * 100
        lines.append(f"  {strategy:10s} : {count:3d} corrections ({pct:5.1f}%)")
    lines.append("")
    
    # User Strategy Preferences
    lines.append("─" * 80)
    lines.append("USER STRATEGY PREFERENCES (What Users Chose)")
    lines.append("─" * 80)
    for strategy, count in sorted(analysis["user_strategy_counts"].items(), key=lambda x: -x[1]):
        pct = (count / analysis["total_corrections"]) * 100
        lines.append(f"  {strategy:10s} : {count:3d} selections ({pct:5.1f}%)")
    lines.append("")
    
    # Correction Pairs
    lines.append("─" * 80)
    lines.append("CORRECTION PAIRS (AI → User)")
    lines.append("─" * 80)
    for pair in analysis["correction_pairs"][:10]:
        lines.append(f"  {pair['ai_suggested']:10s} → {pair['user_chose']:10s} : "
                    f"{pair['frequency']:2d} times ({pair['percentage']:5.1f}%)")
    lines.append("")
    
    # Patterns & Insights
    if analysis["patterns"]:
        lines.append("─" * 80)
        lines.append(f"PATTERNS & INSIGHTS ({len(analysis['patterns'])} found)")
        lines.append("─" * 80)
        for i, pattern in enumerate(analysis["patterns"], 1):
            lines.append(f"\n{i}. {pattern['type'].upper()}")
            lines.append(f"   📊 Insight: {pattern['insight']}")
            lines.append(f"   💡 Action: {pattern['action']}")
        lines.append("")
    
    # Order Size Stats
    if analysis["order_size_stats"]["count"] > 0:
        lines.append("─" * 80)
        lines.append("ORDER SIZE STATISTICS")
        lines.append("─" * 80)
        stats = analysis["order_size_stats"]
        lines.append(f"  Average: {stats['average']:,.0f} shares")
        lines.append(f"  Max:     {stats['max']:,.0f} shares")
        lines.append(f"  Min:     {stats['min']:,.0f} shares")
        lines.append(f"  Count:   {stats['count']} orders")
        lines.append("")
    
    lines.append("=" * 80)
    
    report_text = "\n".join(lines)
    output_path.write_text(report_text)
    print(f"✅ Report saved: {output_path}")
    
    return report_text


if __name__ == "__main__":
    print("🔍 Analyzing corrections...")
    
    corrections = load_corrections(days=30)
    print(f"📊 Loaded {len(corrections)} corrections from last 30 days")
    
    analysis = analyze_strategy_corrections(corrections)
    print(f"✨ Found {analysis.get('insights_count', 0)} patterns")
    
    report = generate_report(analysis)
    print("\n" + report)
