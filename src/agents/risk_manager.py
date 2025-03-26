import math
import pandas as pd

from langchain_core.messages import HumanMessage

from src.agents.state import AgentState, show_agent_reasoning
from src.tools.api import prices_to_df

import json
import ast

##### Risk Management Agent #####


def risk_management_agent(state: AgentState):
    """Evaluates portfolio risk and sets position limits based on comprehensive risk analysis."""
    try:
        show_reasoning = state["metadata"]["show_reasoning"]
        portfolio = state["data"]["portfolio"]
        data = state["data"]

        # 检查价格数据是否存在
        if "prices" not in data or not data["prices"]:
            error_message = "错误: 价格数据不存在，无法进行风险评估"
            print(error_message)
            return create_error_response(state, error_message)

        prices_df = prices_to_df(data["prices"])

        # 检查价格数据是否有效
        if prices_df.empty:
            error_message = "错误: 价格数据为空，无法进行风险评估"
            print(error_message)
            return create_error_response(state, error_message)

        # 检查价格是否有效
        current_price = prices_df['close'].iloc[-1]
        if pd.isna(current_price) or current_price <= 0:
            error_message = f"错误: 当前价格无效 ({current_price})，无法进行风险评估"
            print(error_message)
            return create_error_response(state, error_message)

        # Fetch messages from other agents
        try:
            technical_message = next(
                msg for msg in state["messages"] if msg.name == "technicals")
            fundamentals_message = next(
                msg for msg in state["messages"] if msg.name == "fundamentals")
            sentiment_message = next(
                msg for msg in state["messages"] if msg.name == "sentiment")
            valuation_message = next(
                msg for msg in state["messages"] if msg.name == "valuation")
        except StopIteration as e:
            error_message = f"错误: 缺少必要的代理消息: {e}"
            print(error_message)
            return create_error_response(state, error_message)

        try:
            fundamental_signals = json.loads(fundamentals_message.content)
            technical_signals = json.loads(technical_message.content)
            sentiment_signals = json.loads(sentiment_message.content)
            valuation_signals = json.loads(valuation_message.content)
        except Exception as e:
            try:
                fundamental_signals = ast.literal_eval(fundamentals_message.content)
                technical_signals = ast.literal_eval(technical_message.content)
                sentiment_signals = ast.literal_eval(sentiment_message.content)
                valuation_signals = ast.literal_eval(valuation_message.content)
            except Exception as e2:
                error_message = f"错误: 无法解析代理消息: {e}, {e2}"
                print(error_message)
                return create_error_response(state, error_message)

        agent_signals = {
            "fundamental": fundamental_signals,
            "technical": technical_signals,
            "sentiment": sentiment_signals,
            "valuation": valuation_signals
        }

        # 1. Calculate Risk Metrics
        returns = prices_df['close'].pct_change().dropna()

        # 检查收益率数据是否足够
        if len(returns) < 20:  # 至少需要20个数据点才能计算有意义的风险指标
            error_message = f"错误: 收益率数据不足 (仅有{len(returns)}个数据点)，无法进行可靠的风险评估"
            print(error_message)
            return create_error_response(state, error_message)

        daily_vol = returns.std()
        if pd.isna(daily_vol):
            error_message = "错误: 无法计算波动率，数据可能存在问题"
            print(error_message)
            return create_error_response(state, error_message)

        # Annualized volatility approximation
        volatility = daily_vol * (252 ** 0.5)

        # 计算波动率的历史分布
        min_window = min(120, len(returns))
        rolling_std = returns.rolling(window=min_window, min_periods=min(20, min_window)).std() * (252 ** 0.5)
        volatility_mean = rolling_std.mean()
        volatility_std = rolling_std.std()

        # 检查波动率统计数据是否有效
        if pd.isna(volatility_mean) or pd.isna(volatility_std):
            error_message = "错误: 无法计算波动率统计数据，无法进行风险评估"
            print(error_message)
            return create_error_response(state, error_message)

        if volatility_std == 0:
            error_message = "错误: 波动率标准差为零，无法计算波动率百分位数"
            print(error_message)
            return create_error_response(state, error_message)

        volatility_percentile = (volatility - volatility_mean) / volatility_std

        # Simple historical VaR at 95% confidence
        try:
            var_95 = returns.quantile(0.05)
            if pd.isna(var_95):
                error_message = "错误: 无法计算风险价值(VaR)，数据可能存在问题"
                print(error_message)
                return create_error_response(state, error_message)
        except Exception as e:
            error_message = f"错误: 计算风险价值(VaR)时出错: {e}"
            print(error_message)
            return create_error_response(state, error_message)

        # 使用60天窗口计算最大回撤
        try:
            min_window = min(60, len(prices_df))
            rolling_max = prices_df['close'].rolling(window=min_window, min_periods=min(20, min_window)).max()
            drawdown = prices_df['close'] / rolling_max - 1
            max_drawdown = drawdown.min()

            if pd.isna(max_drawdown):
                error_message = "错误: 无法计算最大回撤，数据可能存在问题"
                print(error_message)
                return create_error_response(state, error_message)
        except Exception as e:
            error_message = f"错误: 计算最大回撤时出错: {e}"
            print(error_message)
            return create_error_response(state, error_message)

        # 2. Market Risk Assessment
        market_risk_score = 0

        # Volatility scoring based on percentile
        if volatility_percentile > 1.5:     # 高于1.5个标准差
            market_risk_score += 2
        elif volatility_percentile > 1.0:   # 高于1个标准差
            market_risk_score += 1

        # VaR scoring
        # Note: var_95 is typically negative. The more negative, the worse.
        if var_95 < -0.03:
            market_risk_score += 2
        elif var_95 < -0.02:
            market_risk_score += 1

        # Max Drawdown scoring
        if max_drawdown < -0.20:  # Severe drawdown
            market_risk_score += 2
        elif max_drawdown < -0.10:
            market_risk_score += 1

        # 3. Position Size Limits
        # 使用新的portfolio结构
        initial_position = portfolio.get('initial_position', 0)
        position_ratio = portfolio.get('position_ratio', 30.0) / 100.0  # 转换为小数

        # 假设总资金为100万，用于计算
        assumed_total_capital = 1000000

        # 计算当前股票价值和总投资组合价值
        current_stock_value = initial_position * current_price

        # 根据仓位占比计算可用于该股票的最大资金
        max_allowed_capital = assumed_total_capital * position_ratio

        # 总投资组合价值 = 当前股票价值 + 剩余可用资金
        total_portfolio_value = current_stock_value + (max_allowed_capital - current_stock_value)

        # 根据风险评分和用户设置的仓位占比计算最大仓位大小
        # 使用用户设置的仓位占比作为基础，而不是固定的25%
        base_position_size = max_allowed_capital

        if market_risk_score >= 4:
            # 高风险情况下减少仓位
            max_position_size = base_position_size * 0.5
        elif market_risk_score >= 2:
            # 中等风险情况下适度减少仓位
            max_position_size = base_position_size * 0.75
        else:
            # 低风险情况下使用完整仓位
            max_position_size = base_position_size

        # 计算最大可购买股数
        max_shares = int(max_position_size / current_price)

        # 4. Stress Testing
        stress_test_scenarios = {
            "market_crash": -0.20,
            "moderate_decline": -0.10,
            "slight_decline": -0.05
        }

        stress_test_results = {}
        current_position_value = current_stock_value

        for scenario, decline in stress_test_scenarios.items():
            potential_loss = current_position_value * decline
            # 使用总投资组合价值计算影响
            if total_portfolio_value == 0:
                error_message = "错误: 投资组合总价值为零，无法计算压力测试影响"
                print(error_message)
                return create_error_response(state, error_message)

            portfolio_impact = potential_loss / total_portfolio_value
            stress_test_results[scenario] = {
                "potential_loss": potential_loss,
                "portfolio_impact": portfolio_impact
            }

        # 5. Risk-Adjusted Signals Analysis
        # Convert all confidences to numeric for proper comparison
        def parse_confidence(conf_str):
            try:
                if isinstance(conf_str, str):
                    return float(conf_str.replace('%', '')) / 100.0
                return float(conf_str)
            except Exception as e:
                error_message = f"错误: 无法解析置信度值 '{conf_str}': {e}"
                print(error_message)
                raise ValueError(error_message)

        # 检查所有信号是否有效
        for agent_name, signal in agent_signals.items():
            if 'signal' not in signal or 'confidence' not in signal:
                error_message = f"错误: {agent_name}代理的信号格式无效，缺少必要字段"
                print(error_message)
                return create_error_response(state, error_message)

            try:
                parse_confidence(signal['confidence'])
            except ValueError as e:
                error_message = f"错误: {agent_name}代理的置信度值无效: {e}"
                print(error_message)
                return create_error_response(state, error_message)

        low_confidence = any(parse_confidence(
            signal['confidence']) < 0.30 for signal in agent_signals.values())

        # Check the diversity of signals. If all three differ, add to risk score
        # (signal divergence can be seen as increased uncertainty)
        unique_signals = set(signal['signal'] for signal in agent_signals.values())
        signal_divergence = (2 if len(unique_signals) == 3 else 0)

        # Market risk contributes up to ~6 points total when doubled
        risk_score = market_risk_score + (2 if low_confidence else 0)
        risk_score += signal_divergence

        # Cap risk score at 10
        risk_score = min(round(risk_score), 10)

        # 6. Generate Trading Action
        # If risk is very high, hold. If moderately high, consider reducing.
        # Else, follow valuation signal as a baseline.
        if risk_score >= 9:
            trading_action = "hold"
        elif risk_score >= 7:
            trading_action = "reduce"
        else:
            # Consider both valuation and price drop signals
            if agent_signals['technical']['signal'] == 'bullish' and parse_confidence(agent_signals['technical']['confidence']) > 0.5:
                trading_action = "buy"
            else:
                trading_action = agent_signals['valuation']['signal']

        message_content = {
            "max_position_size": float(max_position_size),
            "max_shares": int(max_shares),
            "risk_score": risk_score,
            "trading_action": trading_action,
            "current_price": float(current_price),
            "position_ratio": float(position_ratio * 100),  # 转回百分比
            "holding_cost": float(portfolio.get('holding_cost', 0.0)),
            "initial_position": int(initial_position),
            "risk_metrics": {
                "volatility": float(volatility),
                "value_at_risk_95": float(var_95),
                "max_drawdown": float(max_drawdown),
                "market_risk_score": market_risk_score,
                "stress_test_results": stress_test_results
            },
            "reasoning": f"Risk Score {risk_score}/10: Market Risk={market_risk_score}, "
                        f"Volatility={volatility:.2%}, VaR={var_95:.2%}, "
                        f"Max Drawdown={max_drawdown:.2%}"
        }

        # Create the risk management message
        message = HumanMessage(
            content=json.dumps(message_content),
            name="risk_management_agent",
        )

        if show_reasoning:
            show_agent_reasoning(message_content, "Risk Management Agent")

        return {
            "messages": state["messages"] + [message],
            "data": data,
            }
    except Exception as e:
        error_message = f"风险管理代理出错: {e}"
        print(error_message)
        return create_error_response(state, error_message)


def create_error_response(state, error_message):
    """创建错误响应，明确拒绝提供投资建议"""
    error_content = {
        "error": True,
        "message": error_message,
        "trading_action": "no_action",  # 明确表示不采取任何行动
        "reasoning": "由于数据问题，无法提供可靠的风险评估和投资建议。请检查数据源或尝试其他股票。"
    }

    message = HumanMessage(
        content=json.dumps(error_content),
        name="risk_management_agent",
    )

    return {
        "messages": state["messages"] + [message],
        "data": state["data"],
    }
