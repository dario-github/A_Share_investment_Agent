from langchain_core.messages import HumanMessage
from src.agents.state import AgentState, show_agent_reasoning
import json


def valuation_agent(state: AgentState):
    """Performs detailed valuation analysis using multiple methodologies."""
    show_reasoning = state["metadata"]["show_reasoning"]
    data = state["data"]

    # 优先使用优化后的数据结构
    if "financials" in data and data["financials"]:
        compact_metrics = data["financials"]
        earnings_growth = compact_metrics.get("eg", 0)
    else:
        # 兼容旧版数据结构
        metrics = data["financial_metrics"][0] if data["financial_metrics"] and len(data["financial_metrics"]) > 0 else {}
        earnings_growth = metrics.get("earnings_growth", 0)

    # 获取财务报表数据
    if "statements" in data and data["statements"] and len(data["statements"]) >= 2:
        # 使用优化后的数据结构
        current_financial = data["statements"][0]
        previous_financial = data["statements"][1] if len(data["statements"]) > 1 else {}

        # 获取数据，注意单位可能是百万
        unit_multiplier = 1000000 if current_financial.get("unit") == "M" else 1

        # 获取当前期数据
        net_income = current_financial.get("ni", 0) * unit_multiplier
        depreciation = current_financial.get("da", 0) * unit_multiplier
        capex = current_financial.get("capex", 0) * unit_multiplier
        free_cash_flow = current_financial.get("fcf", 0) * unit_multiplier
        current_working_capital = current_financial.get("wc", 0) * unit_multiplier

        # 获取上一期数据
        previous_working_capital = previous_financial.get("wc", 0)
        if "unit" in previous_financial and previous_financial.get("unit") == "M":
            previous_working_capital *= 1000000
    else:
        # 兼容旧版数据结构
        current_financial_line_item = data["financial_line_items"][0] if data["financial_line_items"] and len(data["financial_line_items"]) > 0 else {}
        previous_financial_line_item = data["financial_line_items"][1] if data["financial_line_items"] and len(data["financial_line_items"]) > 1 else {}

        net_income = current_financial_line_item.get('net_income', 0)
        depreciation = current_financial_line_item.get('depreciation_and_amortization', 0)
        capex = current_financial_line_item.get('capital_expenditure', 0)
        free_cash_flow = current_financial_line_item.get('free_cash_flow', 0)
        current_working_capital = current_financial_line_item.get('working_capital', 0)
        previous_working_capital = previous_financial_line_item.get('working_capital', 0)

    # 获取市值数据
    if "market" in data and data["market"]:
        # 使用优化后的数据结构
        market_data = data["market"]
        unit_multiplier = 1000000 if market_data.get("unit") == "M" else 1
        market_cap = market_data.get("mcap", 0) * unit_multiplier
    else:
        # 兼容旧版数据结构
        market_cap = data.get("market_cap", 0)
        if not market_cap and "market_data" in data and data["market_data"]:
            market_cap = data["market_data"].get("market_cap", 0)

    # 确保市值不为零，避免除零错误
    if market_cap <= 0:
        market_cap = 1  # 设置为1以避免除零错误，但会导致极端的估值差距
        print("警告: 市值为零或负值，将使用默认值1进行计算")

    reasoning = {}

    # Calculate working capital change
    working_capital_change = current_working_capital - previous_working_capital

    # Owner Earnings Valuation (Buffett Method)
    owner_earnings_value = calculate_owner_earnings_value(
        net_income=net_income,
        depreciation=depreciation,
        capex=capex,
        working_capital_change=working_capital_change,
        growth_rate=earnings_growth,
        required_return=0.15,
        margin_of_safety=0.25
    )

    # DCF Valuation
    dcf_value = calculate_intrinsic_value(
        free_cash_flow=free_cash_flow,
        growth_rate=earnings_growth,
        discount_rate=0.10,
        terminal_growth_rate=0.03,
        num_years=5,
    )

    # Calculate combined valuation gap (average of both methods)
    dcf_gap = (dcf_value - market_cap) / market_cap if market_cap > 0 else 0
    owner_earnings_gap = (owner_earnings_value - market_cap) / market_cap if market_cap > 0 else 0
    valuation_gap = (dcf_gap + owner_earnings_gap) / 2

    if valuation_gap > 0.10:  # Changed from 0.15 to 0.10 (10% undervalued)
        signal = 'bullish'
    elif valuation_gap < -0.20:  # Changed from -0.15 to -0.20 (20% overvalued)
        signal = 'bearish'
    else:
        signal = 'neutral'

    reasoning["dcf_analysis"] = {
        "signal": "bullish" if dcf_gap > 0.10 else "bearish" if dcf_gap < -0.20 else "neutral",
        "details": f"Intrinsic Value: ${dcf_value:,.2f}, Market Cap: ${market_cap:,.2f}, Gap: {dcf_gap:.1%}"
    }

    reasoning["owner_earnings_analysis"] = {
        "signal": "bullish" if owner_earnings_gap > 0.10 else "bearish" if owner_earnings_gap < -0.20 else "neutral",
        "details": f"Owner Earnings Value: ${owner_earnings_value:,.2f}, Market Cap: ${market_cap:,.2f}, Gap: {owner_earnings_gap:.1%}"
    }

    message_content = {
        "signal": signal,
        "confidence": f"{abs(valuation_gap):.0%}",
        "reasoning": reasoning
    }

    message = HumanMessage(
        content=json.dumps(message_content),
        name="valuation",
    )

    if show_reasoning:
        show_agent_reasoning(message_content, "Valuation Analysis Agent")

    return {
        "messages": [message],
        "data": data,
    }


def calculate_owner_earnings_value(
    net_income: float,
    depreciation: float,
    capex: float,
    working_capital_change: float,
    growth_rate: float = 0.05,
    required_return: float = 0.15,
    margin_of_safety: float = 0.25,
    num_years: int = 5
) -> float:
    """
    使用改进的所有者收益法计算公司价值。

    Args:
        net_income: 净利润
        depreciation: 折旧和摊销
        capex: 资本支出
        working_capital_change: 营运资金变化
        growth_rate: 预期增长率
        required_return: 要求回报率
        margin_of_safety: 安全边际
        num_years: 预测年数

    Returns:
        float: 计算得到的公司价值
    """
    try:
        # 数据有效性检查
        if not all(isinstance(x, (int, float)) for x in [net_income, depreciation, capex, working_capital_change]):
            return 0

        # 计算初始所有者收益
        owner_earnings = (
            net_income +
            depreciation -
            capex -
            working_capital_change
        )

        if owner_earnings <= 0:
            return 0

        # 调整增长率，确保合理性
        growth_rate = min(max(growth_rate, 0), 0.25)  # 限制在0-25%之间

        # 计算预测期收益现值
        future_values = []
        for year in range(1, num_years + 1):
            # 使用递减增长率模型
            year_growth = growth_rate * (1 - year / (2 * num_years))  # 增长率逐年递减
            future_value = owner_earnings * (1 + year_growth) ** year
            discounted_value = future_value / (1 + required_return) ** year
            future_values.append(discounted_value)

        # 计算永续价值
        terminal_growth = min(growth_rate * 0.4, 0.03)  # 永续增长率取增长率的40%或3%的较小值
        terminal_value = (
            future_values[-1] * (1 + terminal_growth)) / (required_return - terminal_growth)
        terminal_value_discounted = terminal_value / \
            (1 + required_return) ** num_years

        # 计算总价值并应用安全边际
        intrinsic_value = sum(future_values) + terminal_value_discounted
        value_with_safety_margin = intrinsic_value * (1 - margin_of_safety)

        return max(value_with_safety_margin, 0)  # 确保不返回负值

    except Exception as e:
        print(f"所有者收益计算错误: {e}")
        return 0


def calculate_intrinsic_value(
    free_cash_flow: float,
    growth_rate: float = 0.05,
    discount_rate: float = 0.10,
    terminal_growth_rate: float = 0.02,
    num_years: int = 5,
) -> float:
    """
    使用改进的DCF方法计算内在价值，考虑增长率和风险因素。

    Args:
        free_cash_flow: 自由现金流
        growth_rate: 预期增长率
        discount_rate: 基础折现率
        terminal_growth_rate: 永续增长率
        num_years: 预测年数

    Returns:
        float: 计算得到的内在价值
    """
    try:
        if not isinstance(free_cash_flow, (int, float)) or free_cash_flow <= 0:
            return 0

        # 调整增长率，确保合理性
        growth_rate = min(max(growth_rate, 0), 0.25)  # 限制在0-25%之间

        # 调整永续增长率，不能超过经济平均增长
        terminal_growth_rate = min(growth_rate * 0.4, 0.03)  # 取增长率的40%或3%的较小值

        # 计算预测期现金流现值
        present_values = []
        for year in range(1, num_years + 1):
            future_cf = free_cash_flow * (1 + growth_rate) ** year
            present_value = future_cf / (1 + discount_rate) ** year
            present_values.append(present_value)

        # 计算永续价值
        terminal_year_cf = free_cash_flow * (1 + growth_rate) ** num_years
        terminal_value = terminal_year_cf * \
            (1 + terminal_growth_rate) / (discount_rate - terminal_growth_rate)
        terminal_present_value = terminal_value / \
            (1 + discount_rate) ** num_years

        # 总价值
        total_value = sum(present_values) + terminal_present_value

        return max(total_value, 0)  # 确保不返回负值

    except Exception as e:
        print(f"DCF计算错误: {e}")
        return 0


def calculate_working_capital_change(
    current_working_capital: float,
    previous_working_capital: float,
) -> float:
    """
    Calculate the absolute change in working capital between two periods.
    A positive change means more capital is tied up in working capital (cash outflow).
    A negative change means less capital is tied up (cash inflow).

    Args:
        current_working_capital: Current period's working capital
        previous_working_capital: Previous period's working capital

    Returns:
        float: Change in working capital (current - previous)
    """
    return current_working_capital - previous_working_capital
