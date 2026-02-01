"""
Offline Learning Pipeline - Deploy
Deploys a new prompt version to production
"""
import json
import argparse
import shutil
from pathlib import Path
from datetime import datetime

import sys
sys.path.append(str(Path(__file__).parent.parent / "mcp_server"))
from config import PROMPTS_DIR


def list_available_versions() -> list:
    """List all available prompt versions"""
    versions = []
    for prompt_file in PROMPTS_DIR.glob("strategy_v*.txt"):
        version = prompt_file.stem.replace("strategy_", "")
        
        # Load metadata if exists
        metadata_file = PROMPTS_DIR / f"{prompt_file.stem}_metadata.json"
        metadata = {}
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        
        versions.append({
            "version": version,
            "file": prompt_file,
            "created_at": metadata.get("created_at", "Unknown"),
            "corrections_analyzed": metadata.get("corrections_analyzed", 0),
            "patterns_found": metadata.get("patterns_found", 0)
        })
    
    # Sort by version number
    versions.sort(key=lambda x: int(x["version"].replace("v", "")), reverse=True)
    return versions


def get_current_version() -> str:
    """Get currently deployed version from environment or config"""
    # Check if there's a current.txt file
    current_file = PROMPTS_DIR / "strategy_current.txt"
    
    if current_file.exists():
        # Try to read version from symlink or file
        try:
            if current_file.is_symlink():
                target = current_file.resolve()
                version = target.stem.replace("strategy_", "")
                return version
            else:
                # Read first line for version info
                first_line = current_file.read_text().split('\n')[0]
                if "VERSION:" in first_line:
                    return first_line.split("VERSION:")[1].strip()
        except:
            pass
    
    return "v1"  # Default


def deploy_version(version: str, dry_run: bool = False) -> bool:
    """
    Deploy a specific prompt version
    
    Args:
        version: Version to deploy (e.g., "v2")
        dry_run: If True, just show what would be deployed
    
    Returns:
        Success status
    """
    # Validate version exists
    version_file = PROMPTS_DIR / f"strategy_{version}.txt"
    
    if not version_file.exists():
        print(f"❌ Version {version} not found: {version_file}")
        return False
    
    # Load metadata
    metadata_file = PROMPTS_DIR / f"strategy_{version}_metadata.json"
    metadata = {}
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
    
    print("\n" + "=" * 80)
    print(f"DEPLOYING VERSION: {version}")
    print("=" * 80)
    print(f"File: {version_file}")
    print(f"Created: {metadata.get('created_at', 'Unknown')}")
    print(f"Corrections Analyzed: {metadata.get('corrections_analyzed', 0)}")
    print(f"Patterns Found: {metadata.get('patterns_found', 0)}")
    print(f"Few-Shot Examples: {metadata.get('few_shot_examples', 0)}")
    
    if metadata.get("insights"):
        print("\nKey Insights:")
        for insight in metadata["insights"]:
            print(f"  • {insight}")
    
    if dry_run:
        print("\n🔍 DRY RUN - No changes made")
        print("=" * 80)
        return True
    
    # Backup current version
    current_version = get_current_version()
    if current_version != version:
        backup_dir = PROMPTS_DIR / "backups"
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"strategy_{current_version}_backup_{timestamp}.txt"
        
        current_file = PROMPTS_DIR / f"strategy_{current_version}.txt"
        if current_file.exists():
            shutil.copy2(current_file, backup_file)
            print(f"\n💾 Backed up {current_version} to: {backup_file}")
    
    # Update "current" marker
    current_marker = PROMPTS_DIR / "strategy_current.txt"
    
    # Copy version file to current
    shutil.copy2(version_file, current_marker)
    
    # Add version header
    content = version_file.read_text()
    versioned_content = f"# VERSION: {version}\n# DEPLOYED: {datetime.now().isoformat()}\n\n{content}"
    current_marker.write_text(versioned_content)
    
    # Update environment variable suggestion
    print(f"\n✅ Deployed version {version}")
    print("\n" + "=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print("1. Set environment variable:")
    print(f"   export STRATEGY_PROMPT_VERSION={version}")
    print("")
    print("2. Restart MCP server:")
    print("   pkill -f 'mcp_server/server.py'")
    print("   python mcp_server/server.py")
    print("")
    print("3. Restart FastAPI gateway:")
    print("   # Ctrl+C and restart uvicorn")
    print("")
    print("4. Monitor corrections to validate improvement")
    print("=" * 80)
    
    # Create deployment log
    deploy_log = {
        "version": version,
        "deployed_at": datetime.now().isoformat(),
        "previous_version": current_version,
        "deployed_by": "manual",
        "metadata": metadata
    }
    
    deploy_log_file = PROMPTS_DIR / f"deployment_log_{version}.json"
    with open(deploy_log_file, 'w') as f:
        json.dump(deploy_log, f, indent=2)
    
    return True


def rollback_version() -> bool:
    """Rollback to previous version"""
    # Find most recent backup
    backup_dir = PROMPTS_DIR / "backups"
    
    if not backup_dir.exists():
        print("❌ No backups found")
        return False
    
    backups = sorted(backup_dir.glob("strategy_v*_backup_*.txt"), reverse=True)
    
    if not backups:
        print("❌ No backups found")
        return False
    
    latest_backup = backups[0]
    
    # Extract version from backup filename
    # Format: strategy_v1_backup_20260131_123456.txt
    parts = latest_backup.stem.split("_")
    version = parts[1]  # v1, v2, etc.
    
    print(f"🔄 Rolling back to {version} from backup: {latest_backup.name}")
    
    # Deploy the backup version
    return deploy_version(version, dry_run=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy prompt version")
    parser.add_argument("--version", type=str, help="Version to deploy (e.g., v2)")
    parser.add_argument("--list", action="store_true", help="List available versions")
    parser.add_argument("--current", action="store_true", help="Show current version")
    parser.add_argument("--rollback", action="store_true", help="Rollback to previous version")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deployed without deploying")
    
    args = parser.parse_args()
    
    if args.list:
        print("\n📋 Available Versions:")
        print("=" * 80)
        versions = list_available_versions()
        current = get_current_version()
        
        for v in versions:
            marker = "★ CURRENT" if v["version"] == current else ""
            print(f"\n{v['version']} {marker}")
            print(f"  Created: {v['created_at']}")
            print(f"  Corrections: {v['corrections_analyzed']}")
            print(f"  Patterns: {v['patterns_found']}")
            print(f"  File: {v['file']}")
        print("\n" + "=" * 80)
    
    elif args.current:
        current = get_current_version()
        print(f"\n📌 Current Version: {current}")
        
        version_file = PROMPTS_DIR / f"strategy_{current}.txt"
        if version_file.exists():
            print(f"   File: {version_file}")
            
            metadata_file = PROMPTS_DIR / f"strategy_{current}_metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                print(f"   Created: {metadata.get('created_at', 'Unknown')}")
                print(f"   Corrections: {metadata.get('corrections_analyzed', 0)}")
    
    elif args.rollback:
        rollback_version()
    
    elif args.version:
        deploy_version(args.version, dry_run=args.dry_run)
    
    else:
        parser.print_help()
