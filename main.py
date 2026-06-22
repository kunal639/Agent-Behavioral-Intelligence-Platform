import os
from typing import List
from dotenv import load_dotenv

# Core Model Imports
from models.models import NormalizedEvent, DetectionFinding

# The Unified Component Pipeline Footprint
from parsers.parser import parse_lines
from normalizers.normalizer import ClaudeNormalizer
from detectors.detector import (
    RepeatedTargetReadDetector,
    RapidFileEnumerationDetector,
    RetryLoopDetector,
    SecretAccessDetector
)
from intelligence.analyzer import AgentIntelligenceAnalyzer
from reports.report import MarkdownReportGenerator

# Load credentials from .env safely before any pipeline stages trigger
load_dotenv()

# ==========================================
# CHANGE THIS FILE NAME TO TEST EACH RUN
# ==========================================
INPUT_LOG_FILE = "data/claude/real_session_user_profile.jsonl"
OUTPUT_REPORT_FILE = "AUDIT_REPORT.md"


def load_telemetry_log(file_path: str) -> List[NormalizedEvent]:
    """Orchestrates ingestion by routing raw strings into the parsing packages."""
    if not os.path.exists(file_path):
        print(f"❌ Error: Telemetry log file not found at '{file_path}'")
        return []

    # Read raw string sequences from the source profile log
    with open(file_path, "r", encoding="utf-8") as f:
        raw_lines = f.readlines()

    # 1. Run structural pairing engine
    paired_invocations = parse_lines(raw_lines)
    
    # 2. Run telemetry mapping normalizer
    normalized_events: List[NormalizedEvent] = []
    for invocation in paired_invocations:
        try:
            event = ClaudeNormalizer.normalize_record(invocation)
            normalized_events.append(event)
        except Exception as e:
            print(f"⚠️ Warning: Normalization failure on record: {e}")
            
    return normalized_events

def run_pipeline():
    print(f"🚀 Starting Engine Lifecycle on: `{INPUT_LOG_FILE}`")
    
    # Step 1: Ingest execution data traces using centralized logic
    events = load_telemetry_log(INPUT_LOG_FILE)
    if not events:
        print("❌ Ingestion yielded 0 events. Aborting pipeline execution.")
        return
    print(f"📥 Successfully parsed & normalized {len(events)} trace records.")

    # Step 2: Route tokens into deterministic rule analyzers
    findings: List[DetectionFinding] = []
    
    print("🔍 Executing behavioral rule heuristics...")
    findings.extend(RepeatedTargetReadDetector.analyze(events))
    findings.extend(RapidFileEnumerationDetector.analyze(events))
    findings.extend(RetryLoopDetector.analyze(events))
    findings.extend(SecretAccessDetector.analyze(events))
    
    print(f"🎯 Rule engine isolated {len(findings)} budget or security anomalies.")

    # Step 3: Add the Intelligence Layer for forensic diagnosis
    enriched_findings = AgentIntelligenceAnalyzer.enrich_findings(findings)

    # Step 4: Compile report using our presentation engine
    print("📝 Compiling final executive markdown document...")
    report_markdown = MarkdownReportGenerator.generate(enriched_findings, events)

    # Step 5: Write the document out to disk
    try:
        with open(OUTPUT_REPORT_FILE, "w", encoding="utf-8") as out_file:
            out_file.write(report_markdown)
        print(f"✅ Success! Audit report generated cleanly at: {OUTPUT_REPORT_FILE}\n")
    except Exception as e:
        print(f"❌ Failed to write report file to disk: {e}")

if __name__ == "__main__":
    run_pipeline()