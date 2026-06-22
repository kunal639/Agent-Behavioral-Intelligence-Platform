from pydantic import BaseModel
from enum import Enum
from typing import List

class EventType(str, Enum):
    FILE_READ = "FILE_READ"
    FILE_WRITE = "FILE_WRITE"
    COMMAND_EXEC = "COMMAND_EXEC"  # Standardized to match the official normalizer token

class NormalizedEvent(BaseModel):
    event_type: EventType
    target: str
    payload: str
    status: str
    timestamp: str
    input_tokens: int = 0       
    output_tokens: int = 0      
    cache_read_tokens: int = 0  

class DetectionFinding(BaseModel):
    detector_name: str
    business_label: str       
    severity: str
    target: str
    count: int
    evidence: List[str]
    tokens_burned: int = 0    
    
    # AI Intelligence Layer Fields
    root_cause: str = ""
    remediation_command: str = ""
    fault_classification: str = ""