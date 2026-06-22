import os
import sys
import json
import subprocess
import argparse
from typing import List
from dotenv import load_dotenv
from parsers.parser import parse_lines
from normalizers.normalizer import ClaudeNormalizer  
from models.models import NormalizedEvent, DetectionFinding, EventType

from detectors.detector import (
    RapidFileEnumerationDetector, 
    SecretAccessDetector, 
    RepeatedTargetReadDetector,
    RetryLoopDetector
)

from intelligence.analyzer import AgentIntelligenceAnalyzer
from reports.report import MarkdownReportGenerator
from reports.report import _calc_cost

load_dotenv()

def print_header():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=" * 60)
    print(" 👀  OBSERVERMODEL LIVE AGENT RUNTIME MONITOR")
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="ObserverModel Real-Time Runtime Monitor Console")
    parser.add_argument("logfile", nargs="?", default=None, help="Path to the JSONL log file to stream")
    args = parser.parse_args()

    target_log = args.logfile
    if target_log is None:
        print_header()
        print("📋 SELECT AN AGENT RISK SCENARIO TO LIVE-STREAM:\n")
        print("  [1] Primary User Session Trace (Real Profile)")
        print("  [2] Runaway AI Agent Infinite Retry Loop")
        print("  [3] Excessive Repository Context Scan (Resource Drain)")
        print("  [4] Protected Configuration Mutation (Compliance Risk)")
        print("-" * 60)
        
        choice = input("👉 Enter scenario number (1-4, Default: 1): ").strip()
        
        mapping = {
            "1": "data/claude/real_session_user_profile.jsonl",
            "2": "data/claude/scenario_01_retry_loop.jsonl",
            "3": "data/claude/scenario_02_rapid_scan.jsonl",
            "4": "data/claude/scenario_03_secret_leakage.jsonl"
        }
        target_log = mapping.get(choice, "data/claude/real_session_user_profile.jsonl")

    if not os.path.exists(target_log):
        print(f"❌ Error: Scenario log file '{target_log}' does not exist.")
        sys.exit(1)

    print_header()
    print(f"📡 Initializing live telemetry stream for: `{target_log}`")
    print("🟢 Status: Ingesting active stream traces...")
    print("-" * 60)

    raw_lines_buffer: List[str] = []
    seen_alerts = set()
    total_events_count = 0
    last_printed_event_id = None
    cmd = [sys.executable, "-u", "telemetry_replay.py", target_log, "--delay", "0.4"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    try:
        for line in process.stdout:
            clean_line = line.strip()
            if not clean_line:
                continue
                
            raw_lines_buffer.append(clean_line)
            total_events_count += 1
            
            try:
                raw_dicts = parse_lines(raw_lines_buffer)
                events: List[NormalizedEvent] = [ClaudeNormalizer.normalize_record(r) for r in raw_dicts]
            except Exception:
                continue

            total_input = sum(e.input_tokens for e in events)
            total_output = sum(e.output_tokens for e in events)
            total_cache = sum(e.cache_read_tokens for e in events)
            current_cost = _calc_cost(total_input, total_output, total_cache)

            if events:
                latest_event = events[-1]
                event_id = (latest_event.timestamp, latest_event.event_type, latest_event.target)
                if event_id != last_printed_event_id:
                    ts = latest_event.timestamp.split('T')[1][:8] if 'T' in latest_event.timestamp else "LOG"
                    print(f"  [{ts}] {latest_event.event_type} -> {latest_event.target}")
                    sys.stdout.flush()
                    last_printed_event_id = event_id  

            active_findings: List[DetectionFinding] = []
            active_findings.extend(RapidFileEnumerationDetector.analyze(events))
            active_findings.extend(SecretAccessDetector.analyze(events))
            active_findings.extend(RepeatedTargetReadDetector.analyze(events))
            active_findings.extend(RetryLoopDetector.analyze(events))

            if active_findings:
                for finding in active_findings:
                    alert_key = (finding.detector_name, finding.target)
                    if alert_key not in seen_alerts:
                        seen_alerts.add(alert_key)
                        sys.stdout.write('\a')  # Audio beep alert
                        print(f"\n🚨 ALERT INJECTED: [{finding.severity}] {finding.business_label}")
                        print(f"   └─ Source Rule:    {finding.detector_name}")
                        print(f"   └─ Target Resource: {finding.target}")
                        print(f"   └─ Live Cost Metric Accumulation: ${current_cost:.4f}\n")
                        sys.stdout.flush()

        process.wait()

    except KeyboardInterrupt:
        print("\n🛑 Stream interrupted by user.")
        process.terminate()
        sys.exit(0)

    print("\n" + "=" * 60)
    print("🏁 SESSION COMPLETE: Agent execution has terminated safely.")
    print("🧠 Initializing Premium AI Intelligence Enrichment Layer...")
    print("=" * 60)

    final_dicts = parse_lines(raw_lines_buffer)
    final_events = [ClaudeNormalizer.normalize_record(r) for r in final_dicts]
    
    final_findings = []
    final_findings.extend(RapidFileEnumerationDetector.analyze(final_events))
    final_findings.extend(SecretAccessDetector.analyze(final_events))
    final_findings.extend(RepeatedTargetReadDetector.analyze(final_events))
    final_findings.extend(RetryLoopDetector.analyze(final_events))

    enriched_findings = AgentIntelligenceAnalyzer.enrich_findings(final_findings)

    print("📝 Compiling finalized markdown Executive Audit Report document...")
    report_md = MarkdownReportGenerator.generate(enriched_findings, final_events)
    
    output_path = "AUDIT_REPORT.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"\n✅ Success! Premium audit report generated cleanly at: {output_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()