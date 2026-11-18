"""
Anomaly Detection Rules and Thresholds for TraceLens QNX Workbench.
"""

# Priority Inversion Thresholds
# High-priority thread blocked on a resource held by a lower-priority thread
PRIORITY_INVERSION_THRESHOLD_NS = 100_000_000  # 100 ms

# Deadline Miss Thresholds
# Ratio of actual interval to configured/expected task period
DEADLINE_MISS_RATIO = 1.5

# Interrupt Storm Thresholds
# Maximum allowable interrupts per IRQ within a 1-second rolling window
INTERRUPT_STORM_WINDOW_NS = 1_000_000_000  # 1 second
INTERRUPT_STORM_THRESHOLD = 500            # >500 events / sec is a storm

# Message Queue Backlog Thresholds
# Maximum pending unhandled messages or pulses on a QNX channel
QUEUE_BACKLOG_COUNT_THRESHOLD = 20
QUEUE_BACKLOG_DURATION_THRESHOLD_NS = 50_000_000  # 50 ms

# Severity Definitions
SEVERITY_CRITICAL = "critical"
SEVERITY_HIGH = "high"
SEVERITY_MEDIUM = "medium"
SEVERITY_LOW = "low"

# Remediations
SUGGESTIONS = {
    "priority-inversion": "对共享资源改用优先级继承互斥锁 (PTHREAD_PRIO_INHERIT)，或提升低优先级持有者的基础优先级，避免被中优先级线程持续抢占。",
    "deadline-miss": "检查周期任务被更高优先级中断或线程抢占情况；优化计算热点或重新评估线程周期与 CPU 亲和性分配。",
    "interrupt-storm": "排查外设硬件引脚抖动或电平触发未及时清除中断标志；将中断服务程序改为轻量级 Pulse 投递到底半部线程处理。",
    "message-queue-backlog": "增加接收端 Worker 线程数或启用非阻塞脉冲 (Pulse)；拆分通道吞吐或排查接收方 MsgReply 延迟。"
}
