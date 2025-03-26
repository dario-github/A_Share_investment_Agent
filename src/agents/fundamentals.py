from langchain_core.messages import HumanMessage

from src.agents.state import AgentState, show_agent_reasoning

import json

##### Fundamental Agent #####


def fundamentals_agent(state: AgentState):
    """Analyzes fundamental data and generates trading signals."""
    show_reasoning = state["metadata"]["show_reasoning"]
    data = state["data"]

    # 优先使用优化后的数据结构
    if "financials" in data and data["financials"]:
        compact_metrics = data["financials"]
        # 使用缩写键名
        return_on_equity = compact_metrics.get("roe", 0)
        net_margin = compact_metrics.get("nm", 0)
        operating_margin = compact_metrics.get("om", 0)

        # 获取其他指标用于后续分析
        revenue_growth = compact_metrics.get("rg", 0)
        earnings_growth = compact_metrics.get("eg", 0)
        book_value_growth = compact_metrics.get("bvg", 0)
        current_ratio = compact_metrics.get("cr", 0)
        debt_to_equity = compact_metrics.get("de", 0)
        free_cash_flow_per_share = compact_metrics.get("fcfps", 0)
        earnings_per_share = compact_metrics.get("eps", 0)
        pe_ratio = compact_metrics.get("pe", 0)
        price_to_book = compact_metrics.get("pb", 0)
        price_to_sales = compact_metrics.get("ps", 0)

        # 获取数据日期信息
        data_date = compact_metrics.get("date", "未知")
    else:
        # 兼容旧版数据结构
        metrics = data["financial_metrics"][0] if data["financial_metrics"] and len(data["financial_metrics"]) > 0 else {}

        return_on_equity = metrics.get("return_on_equity", 0)
        net_margin = metrics.get("net_margin", 0)
        operating_margin = metrics.get("operating_margin", 0)

        # 获取其他指标用于后续分析
        revenue_growth = metrics.get("revenue_growth", 0)
        earnings_growth = metrics.get("earnings_growth", 0)
        book_value_growth = metrics.get("book_value_growth", 0)
        current_ratio = metrics.get("current_ratio", 0)
        debt_to_equity = metrics.get("debt_to_equity", 0)
        free_cash_flow_per_share = metrics.get("free_cash_flow_per_share", 0)
        earnings_per_share = metrics.get("earnings_per_share", 0)
        pe_ratio = metrics.get("pe_ratio", 0)
        price_to_book = metrics.get("price_to_book", 0)
        price_to_sales = metrics.get("price_to_sales", 0)

        # 获取数据日期信息
        data_date = metrics.get("data_date", "未知")

    # Initialize signals list for different fundamental aspects
    signals = []
    reasoning = {}

    # 1. Profitability Analysis
    thresholds = [
        (return_on_equity, 0.15),  # Strong ROE above 15%
        (net_margin, 0.20),  # Healthy profit margins
        (operating_margin, 0.15)  # Strong operating efficiency
    ]
    profitability_score = sum(
        metric is not None and metric > threshold
        for metric, threshold in thresholds
    )

    signals.append('bullish' if profitability_score >=
                   2 else 'bearish' if profitability_score == 0 else 'neutral')
    reasoning["profitability_signal"] = {
        "signal": signals[0],
        "details": (
            f"ROE: {return_on_equity:.2%}" if return_on_equity is not None else "ROE: N/A"
        ) + ", " + (
            f"Net Margin: {net_margin:.2%}" if net_margin is not None else "Net Margin: N/A"
        ) + ", " + (
            f"Op Margin: {operating_margin:.2%}" if operating_margin is not None else "Op Margin: N/A"
        ) + f" (数据日期: {data_date})"
    }

    # 2. Growth Analysis
    thresholds = [
        (revenue_growth, 0.10),  # 10% revenue growth
        (earnings_growth, 0.10),  # 10% earnings growth
        (book_value_growth, 0.10)  # 10% book value growth
    ]
    growth_score = sum(
        metric is not None and metric > threshold
        for metric, threshold in thresholds
    )

    signals.append('bullish' if growth_score >=
                   2 else 'bearish' if growth_score == 0 else 'neutral')
    reasoning["growth_signal"] = {
        "signal": signals[1],
        "details": (
            f"Revenue Growth: {revenue_growth:.2%}" if revenue_growth is not None else "Revenue Growth: N/A"
        ) + ", " + (
            f"Earnings Growth: {earnings_growth:.2%}" if earnings_growth is not None else "Earnings Growth: N/A"
        )
    }

    # 3. Financial Health
    health_score = 0
    if current_ratio and current_ratio > 1.5:  # Strong liquidity
        health_score += 1
    if debt_to_equity and debt_to_equity < 0.5:  # Conservative debt levels
        health_score += 1
    if (free_cash_flow_per_share and earnings_per_share and
            free_cash_flow_per_share > earnings_per_share * 0.8):  # Strong FCF conversion
        health_score += 1

    signals.append('bullish' if health_score >=
                   2 else 'bearish' if health_score == 0 else 'neutral')
    reasoning["financial_health_signal"] = {
        "signal": signals[2],
        "details": (
            f"Current Ratio: {current_ratio:.2f}" if current_ratio is not None else "Current Ratio: N/A"
        ) + ", " + (
            f"D/E: {debt_to_equity:.2f}" if debt_to_equity is not None else "D/E: N/A"
        )
    }

    # 4. Price to X ratios
    thresholds = [
        (pe_ratio, 25),  # Reasonable P/E ratio
        (price_to_book, 3),  # Reasonable P/B ratio
        (price_to_sales, 5)  # Reasonable P/S ratio
    ]
    price_ratio_score = sum(
        metric is not None and metric < threshold
        for metric, threshold in thresholds
    )

    signals.append('bullish' if price_ratio_score >=
                   2 else 'bearish' if price_ratio_score == 0 else 'neutral')
    reasoning["price_ratios_signal"] = {
        "signal": signals[3],
        "details": (
            f"P/E: {pe_ratio:.2f}" if pe_ratio is not None else "P/E: N/A"
        ) + ", " + (
            f"P/B: {price_to_book:.2f}" if price_to_book is not None else "P/B: N/A"
        ) + ", " + (
            f"P/S: {price_to_sales:.2f}" if price_to_sales is not None else "P/S: N/A"
        )
    }

    # Determine overall signal
    bullish_signals = signals.count('bullish')
    bearish_signals = signals.count('bearish')

    if bullish_signals > bearish_signals:
        overall_signal = 'bullish'
    elif bearish_signals > bullish_signals:
        overall_signal = 'bearish'
    else:
        overall_signal = 'neutral'

    # Calculate confidence level
    total_signals = len(signals)
    confidence = max(bullish_signals, bearish_signals) / total_signals

    message_content = {
        "signal": overall_signal,
        "confidence": f"{round(confidence * 100)}%",
        "reasoning": reasoning
    }

    # Create the fundamental analysis message
    message = HumanMessage(
        content=json.dumps(message_content),
        name="fundamentals",
    )

    # Print the reasoning if the flag is set
    if show_reasoning:
        show_agent_reasoning(message_content, "Fundamental Analysis Agent")

    return {
        "messages": [message],
        "data": data,
    }
