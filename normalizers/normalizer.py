import logging
from typing import Dict, Any
from models.models import EventType, NormalizedEvent

logger = logging.getLogger(__name__)

class ClaudeNormalizer:
    @staticmethod
    def normalize_record(invocation: Dict[str, Any]) -> NormalizedEvent:
        """
        Converts a single CompletedToolInvocation into a strongly-typed NormalizedEvent.
        Raises a ValueError if an unmapped tool variant is encountered.
        """
        tool_name = invocation.get("tool_name")
        tool_input = invocation.get("tool_input") or {}
        tool_result = invocation.get("tool_result") or ""
        is_error = invocation.get("is_error", False)
        timestamp = invocation.get("timestamp", "")

        status = "failure" if is_error else "success"

        if tool_name == "Read":
            event_type = EventType.FILE_READ
            target = tool_input.get("file_path", "")
            payload = tool_result if isinstance(tool_result, str) else str(tool_result)

        elif tool_name == "Write":
            event_type = EventType.FILE_WRITE
            target = tool_input.get("file_path", "")
            payload = tool_input.get("content", "")

        elif tool_name == "Edit":
            event_type = EventType.FILE_WRITE
            target = tool_input.get("file_path", "")
            
            edits_list = tool_input.get("edits", [])
            if edits_list and isinstance(edits_list, list) and isinstance(edits_list[0], dict):
                payload = edits_list[0].get("new_string", "")
            else:
                payload = tool_input.get("new_string", str(tool_input))

        elif tool_name == "Bash":
            event_type = EventType.COMMAND_EXEC
            target = tool_input.get("command", "")
            payload = tool_result if isinstance(tool_result, str) else str(tool_result)

        else:
            # Normalizer fails loudly to signal telemetry abnormalities
            raise ValueError(f"Unsupported tool type '{tool_name}' encountered.")

        return NormalizedEvent(
            event_type=event_type,
            target=target,
            payload=payload,
            status=status,
            timestamp=timestamp,
            input_tokens=invocation.get("input_tokens", 0),
            output_tokens=invocation.get("output_tokens", 0),
            cache_read_tokens=invocation.get("cache_read_tokens", 0),
        )