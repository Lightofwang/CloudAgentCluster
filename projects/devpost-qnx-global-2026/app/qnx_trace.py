import json
import re
from typing import Any, Dict, Generator, Iterator, List, Optional, Set, Tuple

VALID_EVENT_CLASSES = {
    "thread-state",
    "kernel-call",
    "interrupt",
    "ipc-message",
    "pulse",
    "slog2"
}

VALID_THREAD_STATES = {"READY", "RUNNING", "BLOCKED", "DEAD"}
VALID_ENTRY_EXIT = {"entry", "exit"}
VALID_IPC_MSG_TYPES = {"send", "receive", "reply"}

SLOG2_PATTERN = re.compile(
    r"^\[?slog2\]?\s+(?P<ts>\d+)\s+\[?(?P<sev>[A-Za-z]+)\]?\s+(?P<proc>[a-zA-Z0-9_\-\.]+)(?:\[(?P<tid>\d+)\])?:\s+(?P<msg>.+)$",
    re.IGNORECASE
)

class QnxTraceParseError(Exception):
    pass

def validate_and_normalize_event(obj: Dict[str, Any], line_num: int) -> Dict[str, Any]:
    if not isinstance(obj, dict):
        raise QnxTraceParseError(f"Line {line_num}: Root event must be a JSON object")

    if "timestamp_ns" not in obj:
        raise QnxTraceParseError(f"Line {line_num}: Missing 'timestamp_ns'")
    try:
        ts = int(obj["timestamp_ns"])
        if ts < 0:
            raise ValueError()
        obj["timestamp_ns"] = ts
    except Exception:
        raise QnxTraceParseError(f"Line {line_num}: 'timestamp_ns' must be a non-negative integer")

    event_class = obj.get("event_class")
    if not event_class or not isinstance(event_class, str):
        raise QnxTraceParseError(f"Line {line_num}: Missing or invalid 'event_class'")

    event_class = event_class.strip()
    if event_class not in VALID_EVENT_CLASSES:
        raise QnxTraceParseError(f"Line {line_num}: Unknown event class '{event_class}'")
    obj["event_class"] = event_class

    # Validate class-specific fields
    if event_class == "thread-state":
        if "thread_id" not in obj:
            raise QnxTraceParseError(f"Line {line_num}: thread-state requires 'thread_id'")
        obj["thread_id"] = int(obj["thread_id"])
        obj["thread_name"] = str(obj.get("thread_name") or f"tid-{obj['thread_id']}")
        obj["process"] = str(obj.get("process") or "unknown-proc")
        
        old_st = str(obj.get("old_state", "")).upper()
        new_st = str(obj.get("new_state", "")).upper()
        if old_st not in VALID_THREAD_STATES or new_st not in VALID_THREAD_STATES:
            raise QnxTraceParseError(f"Line {line_num}: Invalid thread state '{old_st}' -> '{new_st}'")
        obj["old_state"] = old_st
        obj["new_state"] = new_st
        obj["cpu"] = int(obj.get("cpu", 0))
        if "priority" in obj:
            obj["priority"] = int(obj["priority"])

    elif event_class == "kernel-call":
        if "call_name" not in obj or not obj["call_name"]:
            raise QnxTraceParseError(f"Line {line_num}: kernel-call requires 'call_name'")
        entry_exit = str(obj.get("entry_exit", "")).lower()
        if entry_exit not in VALID_ENTRY_EXIT:
            raise QnxTraceParseError(f"Line {line_num}: kernel-call 'entry_exit' must be 'entry' or 'exit'")
        obj["entry_exit"] = entry_exit
        obj["thread_id"] = int(obj.get("thread_id", 0))
        obj["thread_name"] = str(obj.get("thread_name") or f"tid-{obj['thread_id']}")
        obj["process"] = str(obj.get("process") or "unknown-proc")
        obj["cpu"] = int(obj.get("cpu", 0))

    elif event_class == "interrupt":
        if "irq" not in obj:
            raise QnxTraceParseError(f"Line {line_num}: interrupt requires 'irq'")
        obj["irq"] = int(obj["irq"])
        entry_exit = str(obj.get("entry_exit", "entry")).lower()
        if entry_exit not in VALID_ENTRY_EXIT:
            entry_exit = "entry"
        obj["entry_exit"] = entry_exit
        obj["cpu"] = int(obj.get("cpu", 0))
        if "duration_ns" in obj:
            obj["duration_ns"] = int(obj["duration_ns"])

    elif event_class == "ipc-message":
        if "channel_id" not in obj:
            raise QnxTraceParseError(f"Line {line_num}: ipc-message requires 'channel_id'")
        obj["channel_id"] = int(obj["channel_id"])
        msg_type = str(obj.get("msg_type", "send")).lower()
        if msg_type not in VALID_IPC_MSG_TYPES:
            raise QnxTraceParseError(f"Line {line_num}: invalid ipc msg_type '{msg_type}'")
        obj["msg_type"] = msg_type
        obj["channel_name"] = str(obj.get("channel_name") or f"chan-{obj['channel_id']}")
        if "sender_tid" in obj:
            obj["sender_tid"] = int(obj["sender_tid"])
        if "receiver_tid" in obj:
            obj["receiver_tid"] = int(obj["receiver_tid"])
        if "roundtrip_ns" in obj:
            obj["roundtrip_ns"] = int(obj["roundtrip_ns"])

    elif event_class == "pulse":
        if "channel_id" not in obj:
            raise QnxTraceParseError(f"Line {line_num}: pulse requires 'channel_id'")
        obj["channel_id"] = int(obj["channel_id"])
        obj["code"] = int(obj.get("code", 0))
        obj["value"] = int(obj.get("value", 0))
        obj["channel_name"] = str(obj.get("channel_name") or f"chan-{obj['channel_id']}")

    elif event_class == "slog2":
        obj["process"] = str(obj.get("process") or "slog2-proc")
        obj["severity"] = str(obj.get("severity") or "info").lower()
        obj["message"] = str(obj.get("message") or "")
        if "thread_id" in obj:
            obj["thread_id"] = int(obj["thread_id"])

    return obj

def parse_line(line_str: str, line_num: int) -> Dict[str, Any]:
    line = line_str.strip()
    if not line:
        raise QnxTraceParseError("Empty line")

    if line.startswith("{") and line.endswith("}"):
        try:
            data = json.loads(line)
        except json.JSONDecodeError as e:
            raise QnxTraceParseError(f"Invalid JSON: {e}")
        return validate_and_normalize_event(data, line_num)

    # Check for text slog2 line
    m = SLOG2_PATTERN.match(line)
    if m:
        ts = int(m.group("ts"))
        tid = int(m.group("tid")) if m.group("tid") else 1
        event = {
            "timestamp_ns": ts,
            "event_class": "slog2",
            "process": m.group("proc"),
            "thread_id": tid,
            "thread_name": f"{m.group('proc')}-{tid}",
            "severity": m.group("sev").lower(),
            "message": m.group("msg").strip()
        }
        return validate_and_normalize_event(event, line_num)

    raise QnxTraceParseError("Line is neither JSON nor recognized slog2 text")

def stream_parse_trace_lines(
    lines_iterator: Iterator[str],
    batch_size: int = 2000
) -> Generator[Tuple[List[Dict[str, Any]], Dict[str, Any]], None, Dict[str, Any]]:
    """
    Streams and parses lines, yielding batches of validated events.
    Returns overall statistics upon completion.
    """
    total_lines = 0
    parsed_events = 0
    failed_lines: List[Dict[str, Any]] = []
    min_ts: Optional[int] = None
    max_ts: Optional[int] = None
    unique_threads: Set[int] = set()

    batch: List[Dict[str, Any]] = []

    for idx, raw_line in enumerate(lines_iterator, start=1):
        line_clean = raw_line.strip()
        if not line_clean:
            continue
        total_lines += 1

        try:
            event = parse_line(line_clean, idx)
            batch.append(event)
            parsed_events += 1

            ts = event["timestamp_ns"]
            if min_ts is None or ts < min_ts:
                min_ts = ts
            if max_ts is None or ts > max_ts:
                max_ts = ts

            tid = event.get("thread_id")
            if tid is not None:
                unique_threads.add(tid)

            if len(batch) >= batch_size:
                yield batch, {
                    "total_lines": total_lines,
                    "parsed_events": parsed_events
                }
                batch = []

        except QnxTraceParseError as err:
            failed_lines.append({"line": idx, "reason": str(err)})

    if batch:
        yield batch, {
            "total_lines": total_lines,
            "parsed_events": parsed_events
        }

    stats = {
        "total_lines": total_lines,
        "parsed_events": parsed_events,
        "failed_lines": failed_lines,
        "time_range": {
            "start_ns": min_ts if min_ts is not None else 0,
            "end_ns": max_ts if max_ts is not None else 0
        },
        "threads": len(unique_threads)
    }
    return stats
