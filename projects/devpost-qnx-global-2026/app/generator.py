import json
import random
from typing import Any, Dict, Generator, List, Optional, Set

def generate_qnx_trace_events(
    threads_count: int = 8,
    duration_seconds: int = 10,
    inject: Optional[List[str]] = None,
    seed: int = 42
) -> Generator[Dict[str, Any], None, None]:
    """
    Deterministically generates a stream of QNX trace events matching QNX 8.0 event model.
    Supports anomaly injection:
      - 'priority-inversion'
      - 'deadline-miss'
      - 'interrupt-storm'
      - 'message-queue-backlog'
    """
    rng = random.Random(seed)
    inject_set: Set[str] = set(inject or [])
    duration_ns = duration_seconds * 1_000_000_000

    # Thread definitions
    base_threads = [
        {"tid": 1, "name": "sensor-fusion", "proc": "fusion-svc", "prio": 60, "cpu": 0, "period_ns": 50_000_000},
        {"tid": 2, "name": "motor-loop", "proc": "motor-ctrl", "prio": 55, "cpu": 0, "period_ns": 20_000_000},
        {"tid": 3, "name": "msg-broker", "proc": "ipc-router", "prio": 40, "cpu": 1, "period_ns": 40_000_000},
        {"tid": 4, "name": "ui-renderer", "proc": "gui-host", "prio": 25, "cpu": 1, "period_ns": 33_333_333},
        {"tid": 5, "name": "telemetry-tx", "proc": "telemetry", "prio": 20, "cpu": 1, "period_ns": 100_000_000},
        {"tid": 6, "name": "disk-logger", "proc": "logger-svc", "prio": 10, "cpu": 0, "period_ns": 80_000_000},
        {"tid": 7, "name": "system-watchdog", "proc": "watchdog", "prio": 65, "cpu": 0, "period_ns": 100_000_000},
        {"tid": 8, "name": "health-monitor", "proc": "diag-svc", "prio": 15, "cpu": 1, "period_ns": 200_000_000},
    ]

    all_threads = list(base_threads)
    if threads_count > len(base_threads):
        for i in range(len(base_threads) + 1, threads_count + 1):
            all_threads.append({
                "tid": i,
                "name": f"worker-task-{i}",
                "proc": f"worker-svc-{(i % 3) + 1}",
                "prio": 12 + (i % 30),
                "cpu": i % 2,
                "period_ns": 50_000_000 + (i * 5_000_000)
            })
    elif threads_count < len(base_threads):
        all_threads = all_threads[:max(2, threads_count)]

    # Collect scheduled event timestamps
    # Each thread has state transitions and periodic events
    events: List[Dict[str, Any]] = []

    # Initial boot slog2 event
    events.append({
        "timestamp_ns": 0,
        "event_class": "slog2",
        "process": "procnto-smp",
        "thread_id": 0,
        "thread_name": "kernel-idle",
        "severity": "info",
        "message": "QNX Neutrino 8.0 Kernel initialized with SMP (2 cores)"
    })

    # Initial state for all threads: READY
    for th in all_threads:
        events.append({
            "timestamp_ns": 1_000_000,
            "event_class": "thread-state",
            "thread_id": th["tid"],
            "thread_name": th["name"],
            "process": th["proc"],
            "old_state": "READY",
            "new_state": "RUNNING" if th["tid"] <= 2 else "READY",
            "cpu": th["cpu"],
            "priority": th["prio"]
        })

    # Generate normal periodic runs
    deadline_miss_injected = False
    for th in all_threads:
        tid = th["tid"]
        period = th["period_ns"]
        run_duration = int(period * 0.12)  # ~12% execution time
        current_t = 10_000_000 + (tid * 2_000_000)

        while current_t < duration_ns:
            # Skip periodic runs during injected priority inversion for high-priority thread (tid == 1)
            if "priority-inversion" in inject_set and tid == 1 and 2_100_000_000 <= current_t <= 2_370_000_000:
                current_t += period
                continue

            # Check deadline miss injection (inject once for tid == 2)
            if "deadline-miss" in inject_set and tid == 2 and current_t >= 4_000_000_000 and not deadline_miss_injected:
                deadline_miss_injected = True
                miss_delay = int(period * 4)  # 80ms delay, exceeds 1.5x period
                events.append({
                    "timestamp_ns": current_t + miss_delay,
                    "event_class": "slog2",
                    "process": th["proc"],
                    "thread_id": tid,
                    "thread_name": th["name"],
                    "severity": "warn",
                    "message": f"Periodic execution interval exceeded deadline (actual: {miss_delay // 1_000_000}ms, expected: {period // 1_000_000}ms)"
                })
                current_t += miss_delay
                if current_t >= duration_ns:
                    break

            # Thread runs
            run_end = min(current_t + run_duration, duration_ns)
            events.append({
                "timestamp_ns": current_t,
                "event_class": "thread-state",
                "thread_id": tid,
                "thread_name": th["name"],
                "process": th["proc"],
                "old_state": "READY",
                "new_state": "RUNNING",
                "cpu": th["cpu"],
                "priority": th["prio"]
            })

            # Emit occasional kernel call or IPC message during run
            if rng.random() < 0.4:
                events.append({
                    "timestamp_ns": current_t + 500_000,
                    "event_class": "kernel-call",
                    "thread_id": tid,
                    "thread_name": th["name"],
                    "process": th["proc"],
                    "call_name": "MsgSendv",
                    "entry_exit": "entry",
                    "cpu": th["cpu"]
                })
                events.append({
                    "timestamp_ns": current_t + 1_200_000,
                    "event_class": "kernel-call",
                    "thread_id": tid,
                    "thread_name": th["name"],
                    "process": th["proc"],
                    "call_name": "MsgSendv",
                    "entry_exit": "exit",
                    "cpu": th["cpu"]
                })
                # Matching IPC message
                events.append({
                    "timestamp_ns": current_t + 600_000,
                    "event_class": "ipc-message",
                    "channel_id": 100 + (tid % 4),
                    "channel_name": f"chan-svc-{(tid % 4) + 1}",
                    "sender_tid": tid,
                    "sender_name": th["name"],
                    "receiver_tid": 3,
                    "receiver_name": "msg-broker",
                    "msg_type": "send",
                    "msg_size": 64,
                    "roundtrip_ns": 700_000
                })

            # Occasional pulse
            if rng.random() < 0.25:
                events.append({
                    "timestamp_ns": current_t + 800_000,
                    "event_class": "pulse",
                    "channel_id": 100 + (tid % 4),
                    "channel_name": f"chan-svc-{(tid % 4) + 1}",
                    "sender_tid": tid,
                    "code": 42,
                    "value": rng.randint(1, 100)
                })

            # Thread finishes cycle and blocks
            events.append({
                "timestamp_ns": run_end,
                "event_class": "thread-state",
                "thread_id": tid,
                "thread_name": th["name"],
                "process": th["proc"],
                "old_state": "RUNNING",
                "new_state": "BLOCKED",
                "cpu": th["cpu"],
                "priority": th["prio"]
            })

            current_t += period

    # Regular interrupts (IRQ 21 Timer @ ~50ms, IRQ 42 CAN @ ~40ms)
    t_irq = 5_000_000
    while t_irq < duration_ns:
        events.append({
            "timestamp_ns": t_irq,
            "event_class": "interrupt",
            "irq": 21,
            "entry_exit": "entry",
            "cpu": 0,
            "duration_ns": 15_000
        })
        t_irq += 50_000_000

    t_can = 12_000_000
    while t_can < duration_ns:
        events.append({
            "timestamp_ns": t_can,
            "event_class": "interrupt",
            "irq": 42,
            "entry_exit": "entry",
            "cpu": 1,
            "duration_ns": 25_000
        })
        t_can += 40_000_000

    # 1. Anomaly: Priority Inversion injection
    if "priority-inversion" in inject_set and duration_ns >= 2_500_000_000:
        inv_start = 2_100_000_000
        inv_block = 2_120_000_000
        inv_end = 2_370_000_000  # 250ms duration > 100ms
        low_th = next((t for t in all_threads if t["name"] == "disk-logger"), all_threads[-1])
        high_th = next((t for t in all_threads if t["name"] == "sensor-fusion"), all_threads[0])

        # Low prio thread locks mutex
        events.append({
            "timestamp_ns": inv_start,
            "event_class": "kernel-call",
            "thread_id": low_th["tid"],
            "thread_name": low_th["name"],
            "process": low_th["proc"],
            "call_name": "SyncMutexLock",
            "entry_exit": "entry",
            "cpu": 0,
            "mutex_id": 999
        })
        events.append({
            "timestamp_ns": inv_start + 10_000,
            "event_class": "kernel-call",
            "thread_id": low_th["tid"],
            "thread_name": low_th["name"],
            "process": low_th["proc"],
            "call_name": "SyncMutexLock",
            "entry_exit": "exit",
            "cpu": 0,
            "mutex_id": 999
        })

        # High prio thread attempts to lock same mutex and blocks
        events.append({
            "timestamp_ns": inv_block,
            "event_class": "kernel-call",
            "thread_id": high_th["tid"],
            "thread_name": high_th["name"],
            "process": high_th["proc"],
            "call_name": "SyncMutexLock",
            "entry_exit": "entry",
            "cpu": 0,
            "mutex_id": 999
        })
        events.append({
            "timestamp_ns": inv_block + 50_000,
            "event_class": "thread-state",
            "thread_id": high_th["tid"],
            "thread_name": high_th["name"],
            "process": high_th["proc"],
            "old_state": "RUNNING",
            "new_state": "BLOCKED",
            "cpu": 0,
            "priority": high_th["prio"],
            "block_reason": "mutex_999",
            "holder_thread": low_th["name"],
            "holder_tid": low_th["tid"]
        })

        # Low prio thread finally unlocks mutex after 250ms delay
        events.append({
            "timestamp_ns": inv_end,
            "event_class": "kernel-call",
            "thread_id": low_th["tid"],
            "thread_name": low_th["name"],
            "process": low_th["proc"],
            "call_name": "SyncMutexUnlock",
            "entry_exit": "entry",
            "cpu": 0,
            "mutex_id": 999
        })
        events.append({
            "timestamp_ns": inv_end + 20_000,
            "event_class": "kernel-call",
            "thread_id": low_th["tid"],
            "thread_name": low_th["name"],
            "process": low_th["proc"],
            "call_name": "SyncMutexUnlock",
            "entry_exit": "exit",
            "cpu": 0,
            "mutex_id": 999
        })
        # High prio thread unblocks and runs
        events.append({
            "timestamp_ns": inv_end + 50_000,
            "event_class": "thread-state",
            "thread_id": high_th["tid"],
            "thread_name": high_th["name"],
            "process": high_th["proc"],
            "old_state": "BLOCKED",
            "new_state": "READY",
            "cpu": 0,
            "priority": high_th["prio"]
        })
        events.append({
            "timestamp_ns": inv_end + 100_000,
            "event_class": "thread-state",
            "thread_id": high_th["tid"],
            "thread_name": high_th["name"],
            "process": high_th["proc"],
            "old_state": "READY",
            "new_state": "RUNNING",
            "cpu": 0,
            "priority": high_th["prio"]
        })

    # 2. Anomaly: Interrupt Storm injection
    if "interrupt-storm" in inject_set and duration_ns >= 6_000_000_000:
        storm_start = 5_200_000_000
        storm_count = 620  # > 500 in 1 second window
        step_ns = 800_000_000 // storm_count  # 620 interrupts in 800ms
        for i in range(storm_count):
            t = storm_start + (i * step_ns)
            events.append({
                "timestamp_ns": t,
                "event_class": "interrupt",
                "irq": 42,
                "entry_exit": "entry",
                "cpu": 1,
                "duration_ns": 8_000
            })
        events.append({
            "timestamp_ns": storm_start + 850_000_000,
            "event_class": "slog2",
            "process": "procnto-smp",
            "thread_id": 0,
            "thread_name": "kernel-idle",
            "severity": "warn",
            "message": "IRQ 42 storm detected: 620 interrupts triggered in 800ms window"
        })

    # 3. Anomaly: Message Queue Backlog injection
    if "message-queue-backlog" in inject_set and duration_ns >= 7_000_000_000:
        backlog_start = 6_500_000_000
        # 30 messages queued in rapid succession to chan_telemetry (channel_id 505)
        for i in range(30):
            events.append({
                "timestamp_ns": backlog_start + (i * 1_000_000),  # 1ms apart
                "event_class": "ipc-message",
                "channel_id": 505,
                "channel_name": "chan_telemetry",
                "sender_tid": 1,
                "sender_name": "sensor-fusion",
                "receiver_tid": 5,
                "receiver_name": "telemetry-tx",
                "msg_type": "send",
                "msg_size": 128,
                "pending_queue_size": i + 1
            })
        # Unhandled until backlog_end = backlog_start + 120ms
        events.append({
            "timestamp_ns": backlog_start + 120_000_000,
            "event_class": "slog2",
            "process": "ipc-router",
            "thread_id": 3,
            "thread_name": "msg-broker",
            "severity": "warn",
            "message": "Channel chan_telemetry queue backlog: 30 pending messages held over 120ms without drain"
        })
        # Drained with reply
        events.append({
            "timestamp_ns": backlog_start + 130_000_000,
            "event_class": "ipc-message",
            "channel_id": 505,
            "channel_name": "chan_telemetry",
            "sender_tid": 5,
            "sender_name": "telemetry-tx",
            "receiver_tid": 1,
            "receiver_name": "sensor-fusion",
            "msg_type": "reply",
            "msg_size": 16,
            "roundtrip_ns": 130_000_000,
            "pending_queue_size": 0
        })

    # Sort all events chronologically
    events.sort(key=lambda e: e["timestamp_ns"])

    # Assign sequential IDs
    for idx, ev in enumerate(events, start=1):
        ev["id"] = idx
        yield ev

def generate_qnx_trace_jsonl(
    threads_count: int = 8,
    duration_seconds: int = 10,
    inject: Optional[List[str]] = None,
    seed: int = 42
) -> str:
    """Convenience helper returning the trace as a JSON Lines formatted string."""
    lines = [
        json.dumps(ev, ensure_ascii=False)
        for ev in generate_qnx_trace_events(
            threads_count=threads_count,
            duration_seconds=duration_seconds,
            inject=inject,
            seed=seed
        )
    ]
    return "\n".join(lines) + "\n"
