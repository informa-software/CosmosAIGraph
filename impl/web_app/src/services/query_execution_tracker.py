import time
import textwrap
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

class ExecutionStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"

@dataclass
class ExecutionStep:
    """Represents a single step in query execution"""
    step_number: int
    name: str
    strategy: str
    collection: str
    status: ExecutionStatus
    start_time: float
    end_time: float = 0.0
    duration_ms: float = 0.0
    ru_cost: float = 0.0
    documents_found: int = 0
    error_message: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    is_fallback: bool = False

    def complete(self, status: ExecutionStatus, ru_cost: float = 0.0,
                 docs_found: int = 0, error: str = None, metadata: Dict = None):
        """Mark step as complete with results"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status
        self.ru_cost = ru_cost
        self.documents_found = docs_found
        self.error_message = error
        if metadata:
            self.metadata.update(metadata)

class QueryExecutionTracker:
    """
    Tracks actual query execution including planned strategy,
    executed steps, fallbacks, and performance metrics.
    """

    def __init__(self, query: str, planned_strategy: str, llm_plan: Dict = None):
        self.query = query
        self.planned_strategy = planned_strategy
        self.actual_strategy = planned_strategy
        self.start_time = time.time()
        self.end_time = None
        self.steps: List[ExecutionStep] = []
        self.fallback_count = 0
        self.total_ru_cost = 0.0
        self.total_documents = 0
        self.alternatives_compared: List[Dict] = []

        # LLM query plan comparison (Phase 1)
        self.llm_plan = llm_plan
        self.llm_strategy = llm_plan.get("strategy") if llm_plan else None
        self.llm_confidence = llm_plan.get("confidence") if llm_plan else None
        self.llm_reasoning = llm_plan.get("reasoning") if llm_plan else None
        self.llm_query_text = llm_plan.get("query_text") if llm_plan else None
        self.llm_validation_status = llm_plan.get("validation_status") if llm_plan else None
        self.strategy_match = self._check_strategy_match() if llm_plan else None

    def start_step(self, name: str, strategy: str, collection: str,
                   is_fallback: bool = False) -> ExecutionStep:
        """Start tracking a new execution step"""
        step = ExecutionStep(
            step_number=len(self.steps) + 1,
            name=name,
            strategy=strategy,
            collection=collection,
            status=ExecutionStatus.SUCCESS,
            start_time=time.time(),
            is_fallback=is_fallback
        )
        self.steps.append(step)

        if is_fallback:
            self.fallback_count += 1
            self.actual_strategy = strategy

        return step

    def complete_step(self, step: ExecutionStep, status: ExecutionStatus,
                     ru_cost: float = 0.0, docs_found: int = 0,
                     error: str = None, metadata: Dict = None):
        """Complete a step with results"""
        step.complete(status, ru_cost, docs_found, error, metadata)
        self.total_ru_cost += ru_cost
        if status == ExecutionStatus.SUCCESS:
            self.total_documents += docs_found

    def add_alternative_comparison(self, strategy: str, estimated_cost: float,
                                   estimated_time_ms: float):
        """Add alternative strategy for comparison"""
        self.alternatives_compared.append({
            'strategy': strategy,
            'estimated_cost': estimated_cost,
            'estimated_time_ms': estimated_time_ms
        })

    def finish(self):
        """Mark execution as complete"""
        self.end_time = time.time()

    def get_total_duration_ms(self) -> float:
        """Get total execution duration"""
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0

    def _check_strategy_match(self) -> bool:
        """Check if LLM strategy matches rule-based strategy."""
        if not self.llm_plan or self.llm_plan.get("validation_status") != "valid":
            return False

        # Map rule-based to LLM strategy names
        llm_strat = self.llm_plan.get("strategy")
        rule_strat = self.planned_strategy

        strategy_mapping = {
            "db": ["CONTRACT_DIRECT", "ENTITY_FIRST", "ENTITY_AGGREGATION"],
            "graph": ["GRAPH_TRAVERSAL"],
            "vector": ["VECTOR_SEARCH"]
        }

        return llm_strat in strategy_mapping.get(rule_strat, [])

    def get_execution_status(self) -> str:
        """Determine overall execution status"""
        if not self.steps:
            return "NO_EXECUTION"

        has_success = any(s.status == ExecutionStatus.SUCCESS for s in self.steps)
        has_failure = any(s.status == ExecutionStatus.FAILED for s in self.steps)

        if has_success and not has_failure:
            return "[SUCCESS]" if self.fallback_count == 0 else "[SUCCESS with fallbacks]"
        elif has_success and has_failure:
            return "[PARTIAL SUCCESS]"
        else:
            return "[NO RESULTS FOUND]"

    def visualize_ascii(self) -> str:
        """Generate ASCII visualization of execution"""
        lines = []

        # Header
        lines.append("=" * 72)
        lines.append(" QUERY EXECUTION TRACE")
        lines.append(f" Query: {self.query[:60]}")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        lines.append(f" Timestamp: {timestamp}")
        lines.append("=" * 72)
        lines.append("")

        # Strategy info
        lines.append(f"PLANNED STRATEGY: {self.planned_strategy}")

        # LLM comparison (if available)
        if self.llm_plan and self.llm_validation_status == "valid":
            match_indicator = "[MATCH]" if self.strategy_match else "[MISMATCH]"
            lines.append(f"LLM STRATEGY: {self.llm_strategy} {match_indicator}")
            lines.append(f"  Confidence: {self.llm_confidence:.2f}")
            lines.append(f"  Query Type: {self.llm_plan.get('query_type', 'N/A')}")
            if not self.strategy_match and self.llm_reasoning:
                lines.append(f"  Reasoning:")
                # Show full reasoning text, wrapping at 68 chars for readability
                wrapped_lines = textwrap.wrap(self.llm_reasoning, width=68, break_long_words=False)
                for wrapped_line in wrapped_lines:
                    lines.append(f"    {wrapped_line}")

            # Add LLM-generated query text
            if self.llm_query_text:
                lines.append(f"  LLM Generated Query:")
                query_lines = self.llm_query_text.split('\n')
                if len(query_lines) == 1 and len(self.llm_query_text) <= 80:
                    # Single line, short query
                    lines.append(f"    {self.llm_query_text}")
                else:
                    # Multi-line or long query
                    for query_line in query_lines:
                        if query_line.strip():
                            lines.append(f"    {query_line[:76]}")
        elif self.llm_plan:
            lines.append(f"LLM STRATEGY: [{self.llm_validation_status}]")
            if self.llm_plan.get("validation_error"):
                lines.append(f"  Validation Error: {self.llm_plan.get('validation_error')[:60]}...")

        lines.append("ACTUAL EXECUTION PATH:")
        lines.append("-" * 72)
        lines.append("")

        # Steps
        for step in self.steps:
            status_icon = {
                ExecutionStatus.SUCCESS: "[OK]",
                ExecutionStatus.FAILED: "[FAIL]",
                ExecutionStatus.PARTIAL: "[WARN]",
                ExecutionStatus.SKIPPED: "[SKIP]"
            }.get(step.status, "[?]")

            fallback_note = " (Fallback)" if step.is_fallback else ""
            status_text = f"[{step.status.value.upper()}]"

            lines.append(f"{status_icon} Step {step.step_number}: {step.name}{fallback_note}".ljust(50) +
                        f"{status_text} {int(step.duration_ms)}ms")
            lines.append(f"   +- Collection: {step.collection}")

            # Add step-specific metadata
            for key, value in step.metadata.items():
                if key in ['key', 'filter', 'method', 'ids', 'query', 'sql', 'sparql']:
                    # For queries, show on multiple lines if long
                    if key in ['query', 'sql', 'sparql']:
                        label = key.upper()
                        query_text = str(value)
                        if len(query_text) > 80:
                            lines.append(f"   +- {label}:")
                            # Indent query text
                            for line in query_text.split('\n'):
                                if line.strip():
                                    lines.append(f"   |    {line[:76]}")
                        else:
                            lines.append(f"   +- {label}: {query_text}")
                    else:
                        display_value = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                        lines.append(f"   +- {key.replace('_', ' ').title()}: {display_value}")

            lines.append(f"   +- Documents Found: {step.documents_found}")

            if step.error_message:
                lines.append(f"   +- Error: {step.error_message}")

            lines.append(f"   +- RU Cost: {step.ru_cost:.1f}")
            lines.append("")

            # Add fallback notice between steps
            if step.status == ExecutionStatus.FAILED and step.step_number < len(self.steps):
                next_step = self.steps[step.step_number]
                lines.append(f"[WARN] FALLBACK TRIGGERED: Switching to {next_step.strategy} strategy")
                lines.append("")

        lines.append("-" * 72)

        # Summary
        lines.append("EXECUTION SUMMARY:")
        lines.append(f"  Status: {self.get_execution_status()}")
        lines.append(f"  Total Time: {int(self.get_total_duration_ms())}ms")
        lines.append(f"  Total RU Cost: {self.total_ru_cost:.1f}")
        lines.append(f"  Documents Returned: {self.total_documents}")
        lines.append(f"  Fallbacks Used: {self.fallback_count}")
        lines.append("")

        # Fallback chain if any
        if self.fallback_count > 0:
            lines.append("FALLBACK CHAIN:")
            for i, step in enumerate(self.steps, 1):
                status_icon = "[OK]" if step.status == ExecutionStatus.SUCCESS else "[FAIL]"
                fallback_marker = "(fallback)" if step.is_fallback else "(planned)"
                result = step.error_message if step.status == ExecutionStatus.FAILED else f"Found {step.documents_found} docs"
                lines.append(f"  {i}.  {step.strategy} {fallback_marker} -> {status_icon} {result}")
            lines.append("")

        # Performance comparison
        if self.alternatives_compared:
            lines.append("PERFORMANCE COMPARISON:")
            actual_time = self.get_total_duration_ms()
            lines.append(f"  [USED] {self.actual_strategy} (used):     {self.total_ru_cost:.1f} RUs   {int(actual_time)}ms")

            for alt in self.alternatives_compared:
                if alt['strategy'] != self.actual_strategy:
                    cost_diff = ((alt['estimated_cost'] - self.total_ru_cost) / self.total_ru_cost * 100) if self.total_ru_cost > 0 else 0
                    time_diff = ((alt['estimated_time_ms'] - actual_time) / actual_time * 100) if actual_time > 0 else 0
                    lines.append(f"  [ALT] {alt['strategy']}:".ljust(30) +
                               f"{alt['estimated_cost']:.1f} RUs   {int(alt['estimated_time_ms'])}ms  " +
                               f"(+{int(cost_diff)}% cost)")

            if self.total_ru_cost > 0 and self.alternatives_compared:
                best_alt_cost = min(a['estimated_cost'] for a in self.alternatives_compared if a['strategy'] != self.actual_strategy)
                if best_alt_cost > self.total_ru_cost:
                    savings = best_alt_cost - self.total_ru_cost
                    pct = (savings / best_alt_cost * 100)
                    lines.append("")
                    lines.append(f"  [SAVINGS]: {savings:.1f} RUs ({int(pct)}% reduction)")

        # Recommendations
        recommendations = self._generate_recommendations()
        if recommendations:
            lines.append("")
            lines.append("RECOMMENDATIONS:")
            for rec in recommendations:
                lines.append(f"  [TIP] {rec}")

        return "\n".join(lines)

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on execution"""
        recommendations = []

        for step in self.steps:
            if step.status == ExecutionStatus.FAILED:
                if "not found" in (step.error_message or "").lower():
                    entity = step.metadata.get('key', 'entity')
                    recommendations.append(f"Consider adding '{entity}' to entity catalog")

                if step.collection != "contracts" and step.documents_found == 0:
                    recommendations.append(f"Entity collection '{step.collection}' may need updating")

        if self.fallback_count > 1:
            recommendations.append("High fallback count suggests entity catalog may be incomplete")

        if self.total_ru_cost > 50:
            recommendations.append("Consider adding indexes for frequently queried fields")

        return recommendations

    def to_dict(self) -> Dict:
        """Export tracker data as dictionary"""
        result = {
            'query': self.query,
            'planned_strategy': self.planned_strategy,
            'actual_strategy': self.actual_strategy,
            'execution_status': self.get_execution_status(),
            'total_duration_ms': self.get_total_duration_ms(),
            'total_ru_cost': self.total_ru_cost,
            'total_documents': self.total_documents,
            'fallback_count': self.fallback_count,
            'steps': [
                {
                    'step_number': s.step_number,
                    'name': s.name,
                    'strategy': s.strategy,
                    'collection': s.collection,
                    'status': s.status.value,
                    'duration_ms': s.duration_ms,
                    'ru_cost': s.ru_cost,
                    'documents_found': s.documents_found,
                    'is_fallback': s.is_fallback,
                    'error': s.error_message,
                    'metadata': s.metadata
                }
                for s in self.steps
            ],
            'alternatives': self.alternatives_compared,
            'recommendations': self._generate_recommendations()
        }

        # Add LLM comparison fields (Phase 1)
        if self.llm_plan:
            result['llm_comparison'] = {
                'llm_strategy': self.llm_strategy,
                'llm_confidence': self.llm_confidence,
                'llm_query_type': self.llm_plan.get('query_type'),
                'llm_query_text': self.llm_query_text,
                'llm_reasoning': self.llm_reasoning,
                'llm_validation_status': self.llm_validation_status,
                'strategy_match': self.strategy_match
            }

        return result
