import json
import logging
from typing import Iterable, List, Dict, Any

logger = logging.getLogger(__name__)

def parse_lines(lines: Iterable[str]) -> List[Dict[str, Any]]:
    """
    Parses an iterable of raw JSONL strings, pairs corresponding tool_use 
    and tool_result blocks using unique identifiers, and returns a list 
    of completed, fully-paired tool interactions with accurate token telemetry.
    """
    completed_invocations: List[Dict[str, Any]] = []
    
    # In-memory storage to keep track of tool_use blocks waiting for their results
    # Structure: { tool_use_id: { "tool_name": ..., "tool_input": ..., "timestamp": ..., "usage": ... } }
    pending_tool_uses: Dict[str, Dict[str, Any]] = {}

    for line_num, line in enumerate(lines, 1):
        clean_line = line.strip()
        if not clean_line:
            continue
            
        try:
            record = json.loads(clean_line)
            timestamp = record.get("timestamp")
            
            # --- PHASE 1: EXTRACT & CACHE TOOL_USE + TELEMETRY ---
            if record.get("type") == "assistant" and "message" in record:
                # Extract the usage object directly from the assistant message block where it lives
                usage = record["message"].get("usage", {})
                content_blocks = record["message"].get("content", [])
                
                if isinstance(content_blocks, list):
                    for block in content_blocks:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            tool_id = block.get("id")
                            tool_name = block.get("name")
                            
                            if not tool_id:
                                logger.warning(f"[Line {line_num}] Skipping tool_use missing an 'id'.")
                                continue
                                
                            # Cache the tool invocation details and its token footprint using its unique ID
                            pending_tool_uses[tool_id] = {
                                "tool_name": tool_name,
                                "tool_input": block.get("input"),
                                "timestamp": timestamp,
                                "usage": usage  # Safely cached for pairing step
                            }
                            logger.info(f"[Line {line_num}] Cached pending tool_use '{tool_name}' [ID: {tool_id}]")

            # --- PHASE 2: EXTRACT & PAIR WITH TOOL_RESULT ---
            elif record.get("type") == "user" and record.get("userType") == "tool_result" and "message" in record:
                content_blocks = record["message"].get("content", [])
                if isinstance(content_blocks, list):
                    for block in content_blocks:
                        if isinstance(block, dict) and block.get("type") == "tool_result":
                            tool_use_id = block.get("tool_use_id")
                            
                            if not tool_use_id:
                                logger.warning(f"[Line {line_num}] Skipping tool_result missing a 'tool_use_id'.")
                                continue
                                
                            # Check if we have the matching invocation cached
                            if tool_use_id in pending_tool_uses:
                                invocation_context = pending_tool_uses.pop(tool_use_id)
                                
                                # Retrieve token telemetry parsed during Phase 1
                                usage = invocation_context.get("usage", {}) or {}
                                
                                # Construct the finalized CompletedToolInvocation schema object
                                completed_invocation = {
                                    "tool_name": invocation_context["tool_name"],
                                    "tool_input": invocation_context["tool_input"],
                                    "tool_result": block.get("content"),
                                    "is_error": block.get("is_error", False),
                                    "timestamp": invocation_context["timestamp"],
                                    "input_tokens": usage.get("input_tokens", 0),
                                    "output_tokens": usage.get("output_tokens", 0),
                                    "cache_read_tokens": usage.get("cache_read_input_tokens", 0),
                                }
                                
                                completed_invocations.append(completed_invocation)
                                logger.info(f"[Line {line_num}] Successfully paired interaction for tool: {completed_invocation['tool_name']}")
                            else:
                                logger.warning(f"[Line {line_num}] Orphaned tool_result found. No matching tool_use ID: {tool_use_id}")
                                
        except json.JSONDecodeError:
            logger.warning(f"[Line {line_num}] Skipping invalid JSON sequence.")
            continue
        except Exception as e:
            logger.error(f"[Line {line_num}] Unexpected runtime error: {str(e)}")
            continue

    logger.info(f"Parser tracking complete. Generated {len(completed_invocations)} CompletedToolInvocation objects.")
    
    if pending_tool_uses:
        logger.warning(f"Pipeline finished with {len(pending_tool_uses)} unpaired pending tool calls.")

    return completed_invocations