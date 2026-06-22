import logging
from datetime import datetime
from typing import List, Dict
from pydantic import BaseModel
import re
from models.models import EventType, NormalizedEvent, DetectionFinding

logger = logging.getLogger(__name__)


class RepeatedTargetReadDetector:
    """
    Rule: 3+ consecutive FILE_READ events on the SAME exact file within 60 seconds.
    """
    @staticmethod
    def analyze(events: List[NormalizedEvent]) -> List[DetectionFinding]:
        findings: List[DetectionFinding] = []
        
        reads_by_target: Dict[str, List[NormalizedEvent]] = {}
        for event in events:
            if event.event_type == EventType.FILE_READ:
                reads_by_target.setdefault(event.target, []).append(event)

        for target, target_events in reads_by_target.items():
            if len(target_events) < 3:
                continue

            sorted_events = sorted(
                target_events, 
                key=lambda e: datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))
            )

            for i in range(len(sorted_events) - 2):
                window = sorted_events[i:i+3]
                t1 = datetime.fromisoformat(window[0].timestamp.replace("Z", "+00:00"))
                t3 = datetime.fromisoformat(window[2].timestamp.replace("Z", "+00:00"))

                if (t3 - t1).total_seconds() <= 60.0:
                    # Sum token burn metrics for the events in this specific window
                    window_tokens = sum(
                        (getattr(e, "input_tokens", 0) or 0) + (getattr(e, "output_tokens", 0) or 0)
                        for e in window
                    )

                    findings.append(
                        DetectionFinding(
                            detector_name="RepeatedTargetReadDetector",
                            business_label="Redundant Read Context Drain",
                            severity="HIGH",
                            target=target,
                            count=3,
                            evidence=[e.timestamp for e in window],
                            tokens_burned=window_tokens
                        )
                    )
                    break 

        return findings

class RapidFileEnumerationDetector:
    """
    Rule: 3+ DISTINCT file paths accessed via FILE_READ within 60 seconds globally.
    """
    @staticmethod
    def analyze(events: List[NormalizedEvent]) -> List[DetectionFinding]:
        findings: List[DetectionFinding] = []
        
        global_reads = [e for e in events if e.event_type == EventType.FILE_READ]
        global_reads.sort(key=lambda e: datetime.fromisoformat(e.timestamp.replace("Z", "+00:00")))

        if len(global_reads) < 3:
            return findings

        for i in range(len(global_reads) - 2):
            window = global_reads[i:i+3]
            t1 = datetime.fromisoformat(window[0].timestamp.replace("Z", "+00:00"))
            t3 = datetime.fromisoformat(window[2].timestamp.replace("Z", "+00:00"))

            if (t3 - t1).total_seconds() <= 60.0:
                distinct_targets = {e.target for e in window}
                if len(distinct_targets) >= 3:
                    targets_desc = ", ".join(sorted(list(distinct_targets)))
                    window_tokens = sum(
                        (getattr(e, "input_tokens", 0) or 0) + (getattr(e, "output_tokens", 0) or 0)
                        for e in window
                    )
                    
                    findings.append(
                        DetectionFinding(
                            detector_name="RapidFileEnumerationDetector",
                            business_label="Excessive Repository Context Scan",
                            severity="MEDIUM",
                            target=f"Multiple Files ({targets_desc})",
                            count=3,
                            # INJECTED HERE: Swapped the raw timestamp list for clean, human-readable logging
                            evidence=[f"[{e.timestamp.split('T')[1][:8]}] READ {e.target}" for e in window],
                            tokens_burned=window_tokens
                        )
                    )
                    break 

        return findings

class RetryLoopDetector:
    """
    Rule: Same command execution fails 3 times within a 60-second window.
    """
    @staticmethod
    def analyze(events: List[NormalizedEvent]) -> List[DetectionFinding]:
        findings: List[DetectionFinding] = []
        
        failed_commands_by_target: Dict[str, List[NormalizedEvent]] = {}
        for event in events:
            if event.event_type == EventType.COMMAND_EXEC and event.status == "failure":
                failed_commands_by_target.setdefault(event.target, []).append(event)

        for command, command_events in failed_commands_by_target.items():
            if len(command_events) < 3:
                continue

            sorted_events = sorted(
                command_events, 
                key=lambda e: datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))
            )

            for i in range(len(sorted_events) - 2):
                window = sorted_events[i:i+3]
                t1 = datetime.fromisoformat(window[0].timestamp.replace("Z", "+00:00"))
                t3 = datetime.fromisoformat(window[2].timestamp.replace("Z", "+00:00"))

                if (t3 - t1).total_seconds() <= 60.0:
                    evidence_payloads = []
                    window_tokens = 0
                    
                    for idx, ev in enumerate(window, 1):
                        window_tokens += (getattr(ev, "input_tokens", 0) or 0) + (getattr(ev, "output_tokens", 0) or 0)
                        err_snippet = ev.payload.replace('\n', ' ')[:70]
                        evidence_payloads.append(
                            f"[Fail #{idx} at {ev.timestamp}] Error: {err_snippet}..."
                        )

                    findings.append(
                        DetectionFinding(
                            detector_name="RetryLoopDetector",
                            business_label="Compute Looping Waste Alert",
                            severity="HIGH",
                            target=command,
                            count=3,
                            evidence=evidence_payloads,
                            tokens_burned=window_tokens
                        )
                    )
                    break 

        return findings
    
class SecretAccessDetector:
    """
    Rule: Detects when raw plaintext secrets/keys are exposed via reading (CRITICAL),
          or when high-risk credential files are written/accessed as targets (HIGH).
    """
    @staticmethod
    def analyze(events: List[NormalizedEvent]) -> List[DetectionFinding]:
        findings: List[DetectionFinding] = []
        
        SECRET_FILE_PATTERNS = re.compile(
            r"(?:\.env|\.pem|credential(?:s)?\.[a-z]+|secret(?:s)?\.[a-z]+|id_rsa)", 
            re.IGNORECASE
        )
        
        SECRET_CONTENT_PATTERNS = {
            "Database Connection URI": re.compile(r"(?:postgresql|mongodb|mysql|redis)://[^\s]+", re.IGNORECASE),
            "Stripe API Key": re.compile(r"sk_live_[0-9a-zA-Z]{24}"),
            "AWS Access Key": re.compile(r"AKIA[0-9A-Z]{16}"),
            "OpenAI/Generic Token Identifier": re.compile(r"sk-proj-[0-9a-zA-Z]{32,}"),
            "Generic Sensitive Variable Assignment": re.compile(r"(?:API_KEY|SECRET_KEY|ACCESS_TOKEN)\s*=\s*[^\s]+", re.IGNORECASE)
        }

        for event in events:
            if event.status != "success":
                continue
                
            evidence_items = []
            has_content_leak = False
            event_tokens = (getattr(event, "input_tokens", 0) or 0) + (getattr(event, "output_tokens", 0) or 0)

            # Case A: READ Event Type
            if event.event_type == EventType.FILE_READ:
                if event.payload:
                    for label, regex in SECRET_CONTENT_PATTERNS.items():
                        matches = regex.findall(event.payload)
                        if matches:
                            has_content_leak = True
                            for match in matches:
                                masked = match[:12] + "..." + match[-4:] if len(match) > 16 else "********"
                                evidence_items.append(f"[Content Leak] Found plaintext {label}: {masked}")

                if SECRET_FILE_PATTERNS.search(event.target):
                    evidence_items.append(f"[Target Match] Agent read from high-risk path scope: {event.target}")

                if evidence_items:
                    severity_tier = "CRITICAL" if has_content_leak else "HIGH"
                    findings.append(
                        DetectionFinding(
                            detector_name="SecretAccessDetector",
                            business_label="Protected Configuration Modification",
                            severity=severity_tier,
                            target=event.target,
                            count=len(evidence_items),
                            evidence=evidence_items,
                            tokens_burned=event_tokens
                        )
                    )

            # Case B: WRITE Event Type
            elif event.event_type == EventType.FILE_WRITE:
                if SECRET_FILE_PATTERNS.search(event.target):
                    evidence_items.append(f"[Target Match] Agent created/modified a credential file: {event.target}")
                    
                    findings.append(
                        DetectionFinding(
                            detector_name="SecretAccessDetector",
                            business_label="Protected Configuration Modification",
                            severity="HIGH",
                            target=event.target,
                            count=1,
                            evidence=evidence_items,
                            tokens_burned=event_tokens
                        )
                    )
                    
        return findings