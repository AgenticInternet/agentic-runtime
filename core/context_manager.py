from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ContextFrame:
    role: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextManager:
    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self._frames: List[ContextFrame] = []

    def add_frame(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        frame = ContextFrame(role=role, content=content, metadata=metadata or {})
        self._frames.append(frame)
        if len(self._frames) > self.max_history:
            self._frames = self._frames[-self.max_history:]

    def get_history(self) -> List[ContextFrame]:
        return self._frames.copy()

    def clear(self) -> None:
        self._frames.clear()

    def to_messages(self) -> List[Dict[str, str]]:
        return [{"role": f.role, "content": f.content} for f in self._frames]
