from dataclasses import dataclass
from textual.types import UnusedParameter

UNUSED = UnusedParameter()

@dataclass
class StageEvent:
    message: str

@dataclass
class ProgressEvent:
    total: int | UnusedParameter = UNUSED
    progress: int | UnusedParameter = UNUSED
    advance: int | UnusedParameter = UNUSED

DownloadEvent = StageEvent | ProgressEvent