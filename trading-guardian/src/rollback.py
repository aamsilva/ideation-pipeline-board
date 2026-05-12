#!/usr/bin/env python3
"""
Rollback Manager (FP3 Fix)
Provides automatic rollback on failure
"""

import os
import json
import time
import shutil
import logging
from typing import Optional, Dict, List
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RollbackManager:
    """
    Manages system snapshots and rollback operations
    """
    
    def __init__(self, guardian):
        self.guardian = guardian
        self.snapshots_path = f"{guardian.project_path}/backups/snapshots"
        os.makedirs(self.snapshots_path, exist_ok=True)
        
        # Track active snapshots
        self.active_snapshots: List[str] = []
    
    def create_snapshot(self, label: str) -> Dict:
        """
        Create a system snapshot before risky operation
        Returns snapshot metadata
        """
        snapshot_id = f"snap_{int(time.time())}_{label}"
        snapshot_dir = f"{self.snapshots_path}/{snapshot_id}"
        os.makedirs(snapshot_dir, exist_ok=True)
        
        metadata = {
            "id": snapshot_id,
            "label": label,
            "timestamp": datetime.now().isoformat(),
            "files_backed_up": [],
            "config_backed_up": False,
        }
        
        # Backup critical files
        critical_files = [
            "config/config.yaml",
            ".env",
            "src/guardian_core.py",
        ]
        
        for rel_path in critical_files:
            src = f"{self.guardian.project_path}/{rel_path}"
            if os.path.exists(src):
                dst = f"{snapshot_dir}/{os.path.basename(rel_path)}"
                shutil.copy2(src, dst)
                metadata["files_backed_up"].append(rel_path)
        
        # Save metadata
        with open(f"{snapshot_dir}/metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        self.active_snapshots.append(snapshot_id)
        logger.info(f"📸 Snapshot created: {snapshot_id}")
        
        return metadata
    
    def restore_snapshot(self, snapshot_id: str) -> bool:
        """
        Restore system to a previous snapshot
        Returns: success
        """
        snapshot_dir = f"{self.snapshots_path}/{snapshot_id}"
        
        if not os.path.exists(snapshot_dir):
            logger.error(f"Snapshot not found: {snapshot_id}")
            return False
        
        try:
            # Load metadata
            with open(f"{snapshot_dir}/metadata.json", 'r') as f:
                metadata = json.load(f)
            
            # Restore files
            for rel_path in metadata.get("files_backed_up", []):
                src = f"{snapshot_dir}/{os.path.basename(rel_path)}"
                dst = f"{self.guardian.project_path}/{rel_path}"
                
                if os.path.exists(src):
                    shutil.copy2(src, dst)
                    logger.info(f"Restored: {rel_path}")
            
            logger.info(f"✅ Snapshot restored: {snapshot_id}")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
    
    def list_snapshots(self) -> List[Dict]:
        """List all available snapshots"""
        snapshots = []
        for d in os.listdir(self.snapshots_path):
            meta_path = f"{self.snapshots_path}/{d}/metadata.json"
            if os.path.exists(meta_path):
                with open(meta_path, 'r') as f:
                    snapshots.append(json.load(f))
        return sorted(snapshots, key=lambda x: x["timestamp"], reverse=True)
    
    def cleanup_old_snapshots(self, keep: int = 10):
        """Delete old snapshots, keeping the most recent `keep` ones"""
        snapshots = self.list_snapshots()
        
        if len(snapshots) <= keep:
            return
        
        to_delete = snapshots[keep:]
        for snap in to_delete:
            snapshot_dir = f"{self.snapshots_path}/{snap['id']}"
            shutil.rmtree(snapshot_dir)
            logger.info(f"Deleted old snapshot: {snap['id']}")
