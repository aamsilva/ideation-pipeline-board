#!/usr/bin/env python3
"""
AutoResearch Engine - Karpathy Style Experiment Loop
Based on Andrej Karpathy's AutoResearch methodology

Protocol:
1. ANALYZE - Current system state, performance, failures
2. HYPOTHESIZE - Generate improvement hypothesis
3. EXPERIMENT - Controlled test on separate branch/context
4. EVALUATE - Measure results against baseline
5. DECIDE - KEEP (merge) or REVERT (discard)
6. REPEAT - Continuous improvement loop

INTEGRATED WITH DEXTER TOOLS:
- Uses Dexter-style financial tools (Python port)
- LLM analysis via smart-router/litellm ONLY (NO Claude/OpenAI direct)
- Financial Datasets API for market data
"""

import json
import time
import os
import sys
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import logging

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv("/Volumes/disco1tb/projects/trading-guardian/.env")
except ImportError:
    pass

logger = logging.getLogger(__name__)

# Add project src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Dexter tools (Python port)
try:
    from dexter_tools import (
        get_stock_prices,
        get_income_statements,
        get_balance_sheets,
        get_cash_flow_statements,
        get_insider_trades,
        get_analyst_estimates,
        screen_stocks,
        get_all_financials,
        dexter_analysis,
        analyze_with_llm
    )
    DEXTER_TOOLS_AVAILABLE = True
    logger.info("✅ Dexter Tools loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️  Dexter Tools not available: {e}")
    DEXTER_TOOLS_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Experiment:
    """Represents a single AutoResearch experiment"""
    id: str
    hypothesis: str
    changes: List[str]
    baseline_metrics: Dict
    experiment_metrics: Dict = field(default_factory=dict)
    status: str = "pending"  # pending, running, success, failed
    result: Optional[str] = None  # KEEP, REVERT, INCONCLUSIVE
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "hypothesis": self.hypothesis,
            "changes": self.changes,
            "baseline_metrics": self.baseline_metrics,
            "experiment_metrics": self.experiment_metrics,
            "status": self.status,
            "result": self.result,
            "created_at": self.created_at
        }


class AutoResearchEngine:
    """
    Karpathy-style AutoResearch Engine for continuous system improvement
    """
    
    def __init__(self, project_path: str = "/Volumes/disco1tb/projects/trading-guardian"):
        self.project_path = project_path
        self.experiments_path = f"{project_path}/data/experiments.jsonl"
        self.metrics_path = f"{project_path}/data/metrics.jsonl"
        self.experiments: List[Experiment] = []
        self._load_experiments()
        
    def _load_experiments(self):
        """Load past experiments from disk"""
        try:
            with open(self.experiments_path, 'r') as f:
                for line in f:
                    data = json.loads(line.strip())
                    exp = Experiment(**data)
                    self.experiments.append(exp)
        except FileNotFoundError:
            pass
    
    def _save_experiment(self, exp: Experiment):
        """Append experiment to JSONL"""
        with open(self.experiments_path, 'a') as f:
            f.write(json.dumps(exp.to_dict()) + '\n')
    
    def get_system_state(self) -> Dict:
        """Analyze current system state - Phase 1"""
        state = {
            "timestamp": datetime.now().isoformat(),
            "project_path": self.project_path,
            "files_count": self._count_files(),
            "last_commit": self._get_last_commit(),
            "health_score": self._calculate_health_score(),
        }
        
        # Check 4 critical failure points
        state["failure_points"] = self._detect_failure_points()
        
        return state
    
    def _count_files(self) -> int:
        result = subprocess.run(
            f"find {self.project_path} -type f | wc -l",
            shell=True, capture_output=True, text=True
        )
        return int(result.stdout.strip())
    
    def _get_last_commit(self) -> str:
        result = subprocess.run(
            "git log -1 --oneline",
            shell=True, capture_output=True, text=True,
            cwd=self.project_path
        )
        return result.stdout.strip() or "No git repo"
    
    def _calculate_health_score(self) -> float:
        """Score 0-100 based on system health"""
        score = 50.0  # baseline
        
        # Check if config exists
        if os.path.exists(f"{self.project_path}/config/config.yaml"):
            score += 15
        
        # Check if credentials configured
        if os.path.exists(f"{self.project_path}/.env"):
            score += 20
        
        # Check if tests exist
        test_count = subprocess.run(
            f"find {self.project_path}/tests -name '*.py' | wc -l",
            shell=True, capture_output=True, text=True
        )
        if int(test_count.stdout.strip()) > 0:
            score += 15
        
        return min(score, 100.0)
    
    def _detect_failure_points(self) -> List[Dict]:
        """Detect the 4 critical failure points mentioned by user"""
        failures = []
        
        # Point 1: No credentials / auth failure
        if not os.path.exists(f"{self.project_path}/.env"):
            failures.append({
                "id": "FP1",
                "name": "Authentication Failure",
                "severity": "CRITICAL",
                "description": "No .env file with API credentials"
            })
        
        # Point 2: No pre-execution validation
        if not os.path.exists(f"{self.project_path}/src/validation.py"):
            failures.append({
                "id": "FP2",
                "name": "Missing Pre-Execution Validation",
                "severity": "HIGH",
                "description": "No validation gates before trade execution"
            })
        
        # Point 3: No rollback mechanism
        if not os.path.exists(f"{self.project_path}/src/rollback.py"):
            failures.append({
                "id": "FP3",
                "name": "No Rollback Mechanism",
                "severity": "HIGH",
                "description": "Cannot revert failed experiments automatically"
            })
        
        # Point 4: No health monitoring
        if not os.path.exists(f"{self.project_path}/src/monitor.py"):
            failures.append({
                "id": "FP4",
                "name": "No Health Monitoring",
                "severity": "MEDIUM",
                "description": "System cannot self-diagnose issues"
            })
        
        return failures
    
    def generate_hypothesis(self, state: Dict) -> Experiment:
        """Generate improvement hypothesis - Phase 2"""
        failures = state.get("failure_points", [])
        
        if not failures:
            # No critical failures - optimize something
            hyp = Experiment(
                id=f"exp_{int(time.time())}",
                hypothesis="Optimize system performance by adding caching layer",
                changes=["Add request caching", "Add metrics collection"],
                baseline_metrics=state
            )
        else:
            # Fix highest severity failure
            critical = [f for f in failures if f["severity"] == "CRITICAL"]
            if critical:
                failure = critical[0]
            else:
                failure = failures[0]
            
            hyp = Experiment(
                id=f"exp_{int(time.time())}",
                hypothesis=f"Fix {failure['name']} by implementing required component",
                changes=[f"Create {failure['id']} component", "Add tests", "Update docs"],
                baseline_metrics=state
            )
        
        return hyp
    
    def run_experiment(self, exp: Experiment) -> Tuple[bool, str]:
        """
        Run controlled experiment - Phase 3
        Returns (success, metrics_json)
        """
        logger.info(f"Running experiment: {exp.hypothesis}")
        exp.status = "running"
        
        try:
            # In a real implementation, this would:
            # 1. Create git branch
            # 2. Apply changes
            # 3. Run tests
            # 4. Measure metrics
            
            # Simulate experiment
            time.sleep(1)  # Simulate work
            
            exp.experiment_metrics = {
                "timestamp": datetime.now().isoformat(),
                "tests_passed": True,
                "new_files": 3,
                "health_score_improvement": 10
            }
            
            exp.status = "success"
            self._save_experiment(exp)
            
            return True, json.dumps(exp.experiment_metrics)
            
        except Exception as e:
            exp.status = "failed"
            exp.result = f"ERROR: {str(e)}"
            self._save_experiment(exp)
            return False, str(e)
    
    def evaluate_experiment(self, exp: Experiment) -> str:
        """
        Evaluate experiment results - Phase 4
        Returns: KEEP, REVERT, or INCONCLUSIVE
        """
        if exp.status != "success":
            return "REVERT"
        
        baseline = exp.baseline_metrics.get("health_score", 0)
        improvement = exp.experiment_metrics.get("health_score_improvement", 0)
        
        new_score = baseline + improvement
        
        if new_score > baseline + 5:  # 5 point improvement threshold
            return "KEEP"
        elif new_score > baseline:
            return "INCONCLUSIVE"
        else:
            return "REVERT"
    
    def run_cycle(self) -> Dict:
        """
        Run one complete AutoResearch cycle - Phases 1-6
        NOW INTEGRATED WITH DEXTER TOOLS + SMART-ROUTER
        """
        logger.info("=== AUTO-RESEARCH CYCLE START (Dexter Integrated) ===")
        
        # Phase 1: Analyze
        state = self.get_system_state()
        logger.info(f"System State: Health={state['health_score']}")
        
        # NEW: Dexter-style financial analysis (if tools available)
        if DEXTER_TOOLS_AVAILABLE:
            logger.info("🔍 Running Dexter-style financial analysis...")
            try:
                # Analyze a sample ticker for market insights
                dexter_result = dexter_analysis("AAPL", "What is the current financial health and trend?")
                state["dexter_analysis"] = dexter_result
                logger.info(f"✅ Dexter analysis complete: {dexter_result.get('status')}")
            except Exception as e:
                logger.warning(f"⚠️  Dexter analysis failed: {e}")
                state["dexter_analysis"] = {"status": "error", "error": str(e)}
        
        # Phase 2: Hypothesize
        exp = self.generate_hypothesis(state)
        logger.info(f"Hypothesis: {exp.hypothesis}")
        
        # Phase 3: Experiment
        success, metrics = self.run_experiment(exp)
        
        # Phase 4: Evaluate
        decision = self.evaluate_experiment(exp)
        exp.result = decision
        
        # Phase 5: Act (KEEP or REVERT)
        if decision == "KEEP":
            logger.info("✅ KEEPING changes - merging to main")
            # In real implementation: merge branch
        elif decision == "REVERT":
            logger.info("🔄 REVERTING changes - discarding experiment")
            # In real implementation: delete branch
        
        # Phase 6: Repeat (scheduled by cron or loop)
        logger.info("=== CYCLE COMPLETE ===")
        
        return {
            "experiment_id": exp.id,
            "hypothesis": exp.hypothesis,
            "decision": decision,
            "health_before": state["health_score"],
            "health_after": state["health_score"] + exp.experiment_metrics.get("health_score_improvement", 0),
            "dexter_integrated": DEXTER_TOOLS_AVAILABLE,
            "dexter_analysis_status": state.get("dexter_analysis", {}).get("status", "not run")
        }
    
    # ─── NEW: DEXTER TOOLS INTEGRATION ─────────────────────────
    
    def analyze_trading_opportunity(self, ticker: str, question: str) -> Dict:
        """
        Analyze a trading opportunity using Dexter Tools + smart-router
        
        CRITICAL: Uses ONLY smart-router/litellm - NO Claude/OpenAI direct!
        """
        if not DEXTER_TOOLS_AVAILABLE:
            return {
                "ticker": ticker,
                "status": "error",
                "error": "Dexter Tools not available. Install dependencies and set FINANCIAL_DATASETS_API_KEY"
            }
        
        logger.info(f"🧠 Analyzing trading opportunity: {ticker}")
        
        try:
            # Use Dexter tools + smart-router for analysis
            result = dexter_analysis(ticker, question)
            
            # Add Trading Guardian context
            result["guardian_context"] = {
                "health_score": self._calculate_health_score(),
                "failure_points": self._detect_failure_points(),
                "timestamp": datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Trading analysis failed: {e}")
            return {
                "ticker": ticker,
                "status": "error",
                "error": str(e)
            }
    
    def screen_market_opportunities(self, criteria: Dict) -> Dict:
        """
        Screen for market opportunities using Dexter Tools
        
        Example criteria:
        {
            "market_cap": ">1000000000",  # > $1B
            "sector": "Technology",
            "price_to_earnings": "<20"
        }
        """
        if not DEXTER_TOOLS_AVAILABLE:
            return {
                "status": "error",
                "error": "Dexter Tools not available"
            }
        
        logger.info(f"🔍 Screening market with criteria: {criteria}")
        
        try:
            # Use Dexter's screen_stocks function
            result = screen_stocks(criteria)
            
            # Use LLM (smart-router ONLY) to analyze results
            if result.get("status") == "success" and result.get("results"):
                prompt = f"""
Analyze these stock screening results and identify the top 3 opportunities:

CRITERIA: {json.dumps(criteria, indent=2)}

RESULTS: {json.dumps(result.get("results", [])[:10], indent=2)}

TASK:
1. Rank top 3 opportunities with reasoning
2. Identify key risks for each
3. Suggest position sizing (1-10 scale)
4. Provide entry/exit strategy

Be concise but data-driven.
"""
                
                llm_analysis = analyze_with_llm(prompt)
                result["llm_analysis"] = llm_analysis
            
            return result
            
        except Exception as e:
            logger.error(f"Market screening failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


if __name__ == "__main__":
    import os
    engine = AutoResearchEngine()
    result = engine.run_cycle()
    print(json.dumps(result, indent=2))
