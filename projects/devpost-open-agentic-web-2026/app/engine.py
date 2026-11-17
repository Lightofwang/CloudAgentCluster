"""Local deterministic rule engine for AgentBazaar capabilities and multi-agent scenarios."""

import datetime
import hashlib
import time
from typing import Any, Dict, List, Optional, Tuple
from app.models import Agent, Run, RunStep


# Curated merchant catalog prices for high realism
CATALOG_PRICES = {
    # Tea products
    "龙井": {"base": 128, "unit": "250g", "name": "特级高山西湖龙井"},
    "龙井 250g": {"base": 128, "unit": "250g", "name": "特级高山西湖龙井"},
    "碧螺春": {"base": 115, "unit": "200g", "name": "明前洞庭碧螺春"},
    "普洱": {"base": 180, "unit": "饼", "name": "陈年老树普洱生茶饼"},
    "红茶": {"base": 98, "unit": "200g", "name": "正山小种红茶"},
    # Flower products
    "玫瑰": {"base": 99, "unit": "束", "name": "香槟玫瑰11枝礼盒"},
    "玫瑰花束": {"base": 99, "unit": "束", "name": "香槟玫瑰11枝礼盒"},
    "百合": {"base": 128, "unit": "篮", "name": "多头白百合花篮"},
    "向日葵": {"base": 68, "unit": "束", "name": "阳光向日葵5枝"},
    # Book products
    "智能体未来": {"base": 68, "unit": "本", "name": "《智能体未来：开放网络与多智能体系统》"},
    "开放网络简史": {"base": 55, "unit": "本", "name": "《开放网络简史》精装版"},
    "Python编程": {"base": 89, "unit": "本", "name": "《Python高并发与多智能体实战》"},
    # Repair services
    "屏幕更换": {"base": 260, "unit": "次", "name": "原厂品质OLED屏幕总成更换"},
    "电池更换": {"base": 150, "unit": "次", "name": "高容量聚合物电池更换"},
    "清洁除尘": {"base": 50, "unit": "次", "name": "全机超声波深度清洁与除尘"},
    # Coffee products
    "咖啡豆": {"base": 78, "unit": "250g", "name": "日晒耶加雪菲精品咖啡豆"},
    "拿铁豆": {"base": 65, "unit": "250g", "name": "经典意式拼配深烘咖啡豆"},
    "挂耳包": {"base": 45, "unit": "盒", "name": "便携挂耳咖啡混合装(10袋)"},
    # Stationery
    "宣纸": {"base": 45, "unit": "刀", "name": "手工特种生宣纸100张"},
    "毛笔": {"base": 75, "unit": "支", "name": "特级纯狼毫中楷毛笔"},
    "墨汁": {"base": 38, "unit": "瓶", "name": "一得阁高级精装油烟墨汁"},
}


def _derive_price_from_item(agent: Agent, item: str) -> int:
    """Deterministically compute price for any given item based on agent and item."""
    # Check if item hits catalog
    clean_item = item.strip()
    for cat_key, cat_val in CATALOG_PRICES.items():
        if cat_key in clean_item or clean_item in cat_key:
            base = cat_val["base"]
            # Small agent-specific variation (+/- 15%) derived deterministically
            h = int(hashlib.md5(f"{agent.id}:{cat_key}".encode("utf-8")).hexdigest(), 16)
            diff = (h % 31) - 15  # -15 to +15
            return max(15, base + diff)

    # Fallback: parse agent price_range, e.g. "¥50–¥500"
    min_p, max_p = 50, 200
    try:
        parts = agent.price_range.replace("¥", "").replace("$", "").split("–")
        if len(parts) == 2:
            min_p = int(parts[0].strip())
            max_p = int(parts[1].strip())
    except Exception:
        pass
    h = int(hashlib.md5(f"{agent.id}:{clean_item}".encode("utf-8")).hexdigest(), 16)
    return min_p + (h % max(1, max_p - min_p + 1))


def execute_agent_capability(
    agent: Agent, capability: str, params: Dict[str, Any]
) -> Tuple[bool, int, Optional[Dict[str, Any]], Optional[str]]:
    """Execute a single capability on an agent using local deterministic rule engine.

    Returns: (ok, latency_ms, result, error)
    """
    start_time = time.perf_counter()

    if capability not in agent.capabilities:
        elapsed_ms = max(5, int((time.perf_counter() - start_time) * 1000) + 12)
        return (
            False,
            elapsed_ms,
            None,
            f"Capability '{capability}' is not supported by agent '{agent.id}' (Available: {agent.capabilities})",
        )

    try:
        if capability == "price.quote":
            item = str(params.get("item", "特选商品")).strip()
            quantity = int(params.get("quantity", 1))
            if quantity <= 0:
                quantity = 1
            unit_price = _derive_price_from_item(agent, item)
            total = unit_price * quantity
            result = {
                "item": item,
                "unit_price": unit_price,
                "currency": "CNY",
                "quantity": quantity,
                "total": total,
                "valid_until": "当日24:00前有效",
                "merchant": agent.name,
                "merchant_id": agent.id,
                "notes": f"{agent.name} 专供保障，营业时间 {agent.hours}",
            }

        elif capability == "stock.check":
            item = str(params.get("item", "特选商品")).strip()
            h = int(hashlib.md5(f"{agent.id}:{item}:stock".encode("utf-8")).hexdigest(), 16)
            stock_qty = (h % 30) + 3
            result = {
                "item": item,
                "in_stock": True,
                "quantity": stock_qty,
                "unit": "件",
                "warehouse": f"{agent.name} 专属仓储",
                "restock_cycle": "每周二/五定期补货",
                "merchant": agent.name,
                "merchant_id": agent.id,
            }

        elif capability == "order.status":
            order_id = str(params.get("order_id", "ORD-2026-88992")).strip()
            h = int(hashlib.md5(f"{agent.id}:{order_id}".encode("utf-8")).hexdigest(), 16)
            statuses = [
                ("in_transit", "运输中", "同城物流中心分拣完毕，正由快递专员配送"),
                ("processing", "备货中", "商家已确认订单并完成质检验货"),
                ("delivered", "已送达", "客户已签收，欢迎再次光临"),
            ]
            status_code, status_label, desc = statuses[h % len(statuses)]
            result = {
                "order_id": order_id,
                "status": status_code,
                "status_text": status_label,
                "current_location": "朝阳区分拣中心" if status_code != "delivered" else "收货地址",
                "carrier": f"{agent.name} 合作速运",
                "description": desc,
                "timeline": [
                    {"time": "09:30", "event": "商家智能体接收订单并校验库存"},
                    {"time": "10:15", "event": "商品完成质检打包并贴单出库"},
                    {"time": "11:40", "event": "同城配送干线运输中"},
                    {"time": "14:20", "event": desc},
                ],
            }

        elif capability == "appointment.book":
            service = str(params.get("service", "标准到店服务")).strip()
            slot = str(params.get("slot", "明日 14:00–15:30")).strip()
            customer_name = str(params.get("customer_name", "尊贵顾客")).strip()
            contact = str(params.get("contact", "13800000000")).strip()

            h = hashlib.md5(f"{agent.id}:{service}:{slot}:{customer_name}".encode("utf-8")).hexdigest()
            code = f"AB-{h[:6].upper()}"
            result = {
                "confirmation_code": code,
                "service": service,
                "slot": slot,
                "merchant": agent.name,
                "merchant_id": agent.id,
                "customer_name": customer_name,
                "contact": contact,
                "status": "confirmed",
                "address": f"北京市朝阳区三里屯街道 {agent.name} 旗舰店",
                "instructions": "凭预约确认码到店即可享受优先服务，无需排队",
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }

        else:
            elapsed_ms = max(5, int((time.perf_counter() - start_time) * 1000) + 15)
            return (False, elapsed_ms, None, f"Unsupported capability handler for '{capability}'")

        # Deterministic realistic simulated latency (50 - 180 ms)
        h_lat = int(hashlib.md5(f"{agent.id}:{capability}:{start_time}".encode("utf-8")).hexdigest(), 16)
        simulated_delay_ms = 45 + (h_lat % 75)
        # Small real sleep to allow realistic timing
        time.sleep(simulated_delay_ms / 1000.0)
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        return (True, elapsed_ms, result, None)

    except Exception as e:
        elapsed_ms = max(5, int((time.perf_counter() - start_time) * 1000))
        return (False, elapsed_ms, None, f"Execution failed: {str(e)}")


def run_orchestration(registry, scenario: str, input_data: Dict[str, Any]) -> Run:
    """Run a multi-agent orchestration workflow and record all steps and results."""
    run_id = f"run-{scenario[:8]}-{int(time.time() * 1000) % 1000000:06d}"
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    steps: List[RunStep] = []
    step_num = 1

    if scenario == "compare-price":
        item = str(input_data.get("item", "龙井 250g")).strip()
        quantity = int(input_data.get("quantity", 2))

        # Step 1: Discover agents with capability price.quote
        agents = registry.list_agents(capability="price.quote")
        steps.append(
            RunStep(
                step=step_num,
                agent_id="coordinator",
                action="discover_agents",
                status="success",
                detail={
                    "message": f"在注册表中检索具备 'price.quote' 能力的智能体，共找到 {len(agents)} 个商家智能体",
                    "matched_agents": [a.id for a in agents],
                },
                latency_ms=12,
                timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            )
        )
        step_num += 1

        # Step 2..N: Verify trust and invoke quote for top merchants
        quotes = []
        for ag in agents[:4]:  # Top 4 merchants
            t_score = ag.trust_score
            ver_status = "verified" if t_score >= 80 else ("warning" if t_score < 50 else "standard")
            steps.append(
                RunStep(
                    step=step_num,
                    agent_id=ag.id,
                    action="verify_trust",
                    status="success",
                    detail={
                        "message": f"验证商家 '{ag.name}' ({ag.id}) 的信任分",
                        "trust_score": t_score,
                        "verifiable": ag.trust_breakdown.verifiable,
                        "success_rate": ag.trust_breakdown.success_rate,
                        "latency_score": ag.trust_breakdown.latency,
                        "verdict": ver_status,
                    },
                    latency_ms=8,
                    timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                )
            )
            step_num += 1

            ok, lat, res, err = execute_agent_capability(
                ag, "price.quote", {"item": item, "quantity": quantity}
            )
            registry.record_invocation(ag.id, ok, lat)

            steps.append(
                RunStep(
                    step=step_num,
                    agent_id=ag.id,
                    action="invoke_quote",
                    status="success" if ok else "failed",
                    detail=res if ok else {"error": err},
                    latency_ms=lat,
                    timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                )
            )
            step_num += 1
            if ok and res:
                quotes.append(res)

        # Step Final: Compare and aggregate
        quotes.sort(key=lambda q: q["total"])
        best = quotes[0] if quotes else None
        steps.append(
            RunStep(
                step=step_num,
                agent_id="coordinator",
                action="aggregate_quotes",
                status="success",
                detail={
                    "message": f"完成比价汇总：已对比 {len(quotes)} 家报价，最低报价由 '{best['merchant'] if best else '无'}' 提供",
                    "lowest_total": best["total"] if best else 0,
                },
                latency_ms=5,
                timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            )
        )

        final_result = {
            "scenario": "compare-price",
            "item": item,
            "quantity": quantity,
            "best_quote": best,
            "all_quotes": quotes,
            "summary": f"比价完成！最低价为 ¥{best['total']}（单价 ¥{best['unit_price']}，来自 {best['merchant']}）"
            if best
            else "未能获取有效报价",
        }

    elif scenario == "track-order":
        order_id = str(input_data.get("order_id", "ORD-2026-88992")).strip()

        # Step 1: Discover handling agent
        agents = registry.list_agents(capability="order.status")
        target_agent = agents[0] if agents else None

        steps.append(
            RunStep(
                step=step_num,
                agent_id="coordinator",
                action="discover_logistics_agent",
                status="success",
                detail={
                    "message": f"检索具备 'order.status' 追踪能力的智能体，匹配服务商 '{target_agent.name if target_agent else '无'}'",
                    "order_id": order_id,
                },
                latency_ms=10,
                timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            )
        )
        step_num += 1

        if target_agent:
            # Step 2: Verify trust
            steps.append(
                RunStep(
                    step=step_num,
                    agent_id=target_agent.id,
                    action="verify_trust",
                    status="success",
                    detail={
                        "message": f"校验服务商 '{target_agent.name}' 签名与信任分",
                        "trust_score": target_agent.trust_score,
                    },
                    latency_ms=6,
                    timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                )
            )
            step_num += 1

            # Step 3: Invoke status
            ok, lat, res, err = execute_agent_capability(
                target_agent, "order.status", {"order_id": order_id}
            )
            registry.record_invocation(target_agent.id, ok, lat)

            steps.append(
                RunStep(
                    step=step_num,
                    agent_id=target_agent.id,
                    action="query_status",
                    status="success" if ok else "failed",
                    detail=res if ok else {"error": err},
                    latency_ms=lat,
                    timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                )
            )
            step_num += 1

            # Step 4: Cross-check stock/dispatch verification with auxiliary merchant
            aux_agents = [a for a in registry.list_agents(capability="stock.check") if a.id != target_agent.id]
            if aux_agents:
                aux = aux_agents[0]
                ok_s, lat_s, res_s, _ = execute_agent_capability(aux, "stock.check", {"item": "订单配套礼品"})
                registry.record_invocation(aux.id, ok_s, lat_s)
                steps.append(
                    RunStep(
                        step=step_num,
                        agent_id=aux.id,
                        action="cross_check_warehouse",
                        status="success",
                        detail={
                            "message": f"跨商家前置仓 '{aux.name}' 校验附赠礼品出库状态",
                            "warehouse_status": "已备妥同步派送",
                        },
                        latency_ms=lat_s,
                        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    )
                )
                step_num += 1

            final_result = {
                "scenario": "track-order",
                "order_id": order_id,
                "tracking_info": res,
                "summary": f"订单 {order_id} 状态：{res['status_text']}（当前位于：{res['current_location']}）"
                if res
                else "查询失败",
            }
        else:
            final_result = {"scenario": "track-order", "error": "未找到支持订单追踪的智能体"}

    elif scenario == "book-appointment":
        merchant_id = input_data.get("merchant_id")
        target_agent = registry.get_agent(merchant_id) if merchant_id else None
        if not target_agent:
            agents = registry.list_agents(capability="appointment.book")
            target_agent = agents[0] if agents else None

        service = str(input_data.get("service", "专业到店品鉴与选购")).strip()
        slot = str(input_data.get("slot", "明日 15:00–16:30")).strip()
        customer_name = str(input_data.get("customer_name", "王先生")).strip()
        contact = str(input_data.get("contact", "13912345678")).strip()

        # Step 1: Discover
        steps.append(
            RunStep(
                step=step_num,
                agent_id="coordinator",
                action="match_appointment_merchant",
                status="success",
                detail={
                    "message": f"为服务 '{service}' 匹配商家智能体 '{target_agent.name if target_agent else '无'}'",
                    "hours": target_agent.hours if target_agent else "",
                },
                latency_ms=8,
                timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            )
        )
        step_num += 1

        if target_agent:
            # Step 2: Verify Trust
            steps.append(
                RunStep(
                    step=step_num,
                    agent_id=target_agent.id,
                    action="verify_trust",
                    status="success",
                    detail={
                        "message": f"验证商家 '{target_agent.name}' 信任凭据与服务时间段匹配度",
                        "trust_score": target_agent.trust_score,
                    },
                    latency_ms=7,
                    timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                )
            )
            step_num += 1

            # Step 3: Check Slot Availability
            steps.append(
                RunStep(
                    step=step_num,
                    agent_id=target_agent.id,
                    action="check_slot_availability",
                    status="success",
                    detail={
                        "message": f"预约时间段 '{slot}' 处于营业时间（{target_agent.hours}）内，名额尚充裕",
                        "available": True,
                    },
                    latency_ms=15,
                    timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                )
            )
            step_num += 1

            # Step 4: Execute booking
            ok, lat, res, err = execute_agent_capability(
                target_agent,
                "appointment.book",
                {
                    "service": service,
                    "slot": slot,
                    "customer_name": customer_name,
                    "contact": contact,
                },
            )
            registry.record_invocation(target_agent.id, ok, lat)

            steps.append(
                RunStep(
                    step=step_num,
                    agent_id=target_agent.id,
                    action="confirm_booking",
                    status="success" if ok else "failed",
                    detail=res if ok else {"error": err},
                    latency_ms=lat,
                    timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                )
            )
            step_num += 1

            final_result = {
                "scenario": "book-appointment",
                "appointment": res,
                "confirmation_code": res["confirmation_code"] if res else None,
                "summary": f"预约成功！确认码：{res['confirmation_code']}，服务时间：{slot}"
                if res
                else "预约失败",
            }
        else:
            final_result = {"scenario": "book-appointment", "error": "未找到支持预约的商家智能体"}

    else:
        steps.append(
            RunStep(
                step=1,
                agent_id="coordinator",
                action="invalid_scenario",
                status="failed",
                detail={"error": f"Unknown scenario: {scenario}"},
                latency_ms=2,
                timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            )
        )
        final_result = {"error": f"Unknown scenario: {scenario}"}

    run = Run(
        run_id=run_id,
        scenario=scenario,
        input=input_data,
        status="completed" if "error" not in final_result else "failed",
        steps=steps,
        result=final_result,
        created_at=now_iso,
    )
    registry.save_run(run)
    return run
