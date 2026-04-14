import asyncio
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from backend.logging_config import get_logger

logger = get_logger(__name__)


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


# Alias so orchestrator code can use the more descriptive name
AgentResultStatus = AgentStatus


@dataclass
class AgentResult:
    agent_type: str
    status: AgentStatus
    data: dict | None = None
    error: str | None = None
    duration_ms: int = 0
    attempts: int = 1


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(self, agent_type: str):
        self.agent_type = agent_type
        self._logger = get_logger(f"{__name__}.{agent_type}")

    @abstractmethod
    async def execute(self, context: dict) -> AgentResult:
        """Execute agent task. Implement in subclass."""
        pass

    async def run_with_retry(
        self,
        context: dict,
        max_retries: int = 3,
        base_delay: float = 1.0,
        failure_rate: float = 0.0,
    ) -> AgentResult:
        """
        Run agent with exponential backoff retry.
        If failure_rate > 0, randomly fails before executing (for mock simulation).
        """
        last_result: AgentResult | None = None

        for attempt in range(max_retries):
            # Simulate random failure for mock agents
            if failure_rate > 0 and random.random() < failure_rate:
                self._logger.warning(f"[attempt {attempt + 1}/{max_retries}] Simulated failure")
                last_result = AgentResult(
                    agent_type=self.agent_type,
                    status=AgentStatus.FAILED,
                    error="Simulated random failure",
                    duration_ms=0,
                    attempts=attempt + 1,
                )
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    self._logger.info(f"Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                continue

            start = time.perf_counter()
            try:
                result = await self.execute(context)
                duration_ms = int((time.perf_counter() - start) * 1000)
                result.duration_ms = duration_ms
                result.attempts = attempt + 1
                last_result = result

                if result.status == AgentStatus.SUCCESS:
                    self._logger.info(
                        f"[attempt {attempt + 1}/{max_retries}] SUCCESS in {duration_ms}ms"
                    )
                    return result
                else:
                    self._logger.warning(
                        f"[attempt {attempt + 1}/{max_retries}] FAILED: {result.error}"
                    )
                    if attempt < max_retries - 1:
                        delay = base_delay * (2**attempt)
                        self._logger.info(f"Retrying in {delay:.1f}s...")
                        await asyncio.sleep(delay)
            except Exception as e:
                duration_ms = int((time.perf_counter() - start) * 1000)
                self._logger.error(
                    f"[attempt {attempt + 1}/{max_retries}] EXCEPTION: {e}",
                    exc_info=True,
                )
                last_result = AgentResult(
                    agent_type=self.agent_type,
                    status=AgentStatus.FAILED,
                    error=str(e),
                    duration_ms=duration_ms,
                    attempts=attempt + 1,
                )
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    await asyncio.sleep(delay)

        self._logger.error(f"All {max_retries} attempts failed")
        return last_result or AgentResult(
            agent_type=self.agent_type,
            status=AgentStatus.FAILED,
            error="Max retries exceeded",
            attempts=max_retries,
        )
