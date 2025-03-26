from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from src.tools.openrouter_config import get_chat_completion
import json
import re

from src.agents.state import AgentState, show_agent_reasoning


##### Portfolio Management Agent #####
def portfolio_management_agent(state: AgentState):
    """Makes final trading decisions and generates orders"""
    show_reasoning = state["metadata"]["show_reasoning"]
    portfolio = state["data"]["portfolio"]

    # 获取仓位占比和持仓成本
    position_ratio = portfolio.get("position_ratio", 30.0)  # 默认30%
    holding_cost = portfolio.get("holding_cost", 0.0)  # 默认0
    initial_position = portfolio.get("initial_position", 0)  # 默认0

    # Get the technical analyst, fundamentals agent, and risk management agent messages
    try:
        technical_message = next(
            msg for msg in state["messages"] if msg.name == "technical_analyst_agent")
    except StopIteration:
        # 如果没有找到技术分析消息，创建一个默认消息
        print("警告: 未找到技术分析消息，使用默认值")
        technical_message = HumanMessage(
            content="未提供技术分析数据。",
            name="technical_analyst_agent"
        )

    try:
        fundamentals_message = next(
            msg for msg in state["messages"] if msg.name == "fundamentals_agent")
    except StopIteration:
        # 如果没有找到基本面分析消息，创建一个默认消息
        print("警告: 未找到基本面分析消息，使用默认值")
        fundamentals_message = HumanMessage(
            content="未提供基本面分析数据。",
            name="fundamentals_agent"
        )

    try:
        sentiment_message = next(
            msg for msg in state["messages"] if msg.name == "sentiment_agent")
    except StopIteration:
        # 如果没有找到情绪分析消息，创建一个默认消息
        print("警告: 未找到情绪分析消息，使用默认值")
        sentiment_message = HumanMessage(
            content="未提供情绪分析数据。",
            name="sentiment_agent"
        )

    try:
        valuation_message = next(
            msg for msg in state["messages"] if msg.name == "valuation_agent")
    except StopIteration:
        # 如果没有找到估值分析消息，创建一个默认消息
        print("警告: 未找到估值分析消息，使用默认值")
        valuation_message = HumanMessage(
            content="未提供估值分析数据。",
            name="valuation_agent"
        )

    try:
        risk_message = next(
            msg for msg in state["messages"] if msg.name == "risk_management_agent")
    except StopIteration:
        # 如果没有找到风险管理消息，创建一个默认消息
        print("警告: 未找到风险管理消息，使用默认值")
        risk_message = HumanMessage(
            content="未提供风险管理数据。",
            name="risk_management_agent"
        )

    # Create the system message
    system_message = {
        "role": "system",
        "content": f"""您是一位负责做出最终交易决策的投资组合经理。
            您的工作是基于团队的分析做出交易决策，同时严格遵守风险管理约束。

            投资组合信息：
            - 仓位占比: {position_ratio}%（表示愿意投入总资金的百分比）
            - 持仓成本: {holding_cost}（如果已持有股票，这是每股的成本价）
            - 初始持仓: {initial_position}（当前持有的股票数量）

            风险管理约束：
            - 您必须不超过风险管理员指定的最大仓位规模(max_position_size)
            - 您必须遵循风险管理推荐的交易行动(买入/卖出/持有)
            - 这些是硬性约束，不能被其他信号覆盖

            在权衡不同信号的方向和时机时：
            1. 估值分析(35%权重)
               - 公允价值评估的主要驱动因素
               - 确定价格是否提供良好的进入/退出点

            2. 基本面分析(30%权重)
               - 业务质量和增长评估
               - 确定对长期潜力的信心

            3. 技术分析(25%权重)
               - 次要确认
               - 帮助确定进入/退出时机

            4. 情绪分析(10%权重)
               - 最终考虑因素
               - 可以在风险限制内影响仓位大小

            决策过程应该是：
            1. 首先检查风险管理约束
            2. 然后评估估值信号
            3. 然后评估基本面信号
            4. 使用技术分析确定时机
            5. 考虑情绪进行最终调整

            您必须使用提供的工具函数来返回您的决策，确保所有必要的信息都包含在内。
            """
    }

    # 定义决策工具
    tools = [
        {
            "type": "function",
            "function": {
                "name": "make_investment_decision",
                "description": "生成投资决策和详细分析报告",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["buy", "sell", "hold"],
                            "description": "交易行动：买入、卖出或持有"
                        },
                        "quantity": {
                            "type": "integer",
                            "description": "交易数量（股票数量）"
                        },
                        "confidence": {
                            "type": "number",
                            "description": "决策置信度（0-1之间的小数）"
                        },
                        "agent_signals": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "agent_name": {
                                        "type": "string",
                                        "description": "代理名称"
                                    },
                                    "signal": {
                                        "type": "string",
                                        "enum": ["bullish", "bearish", "neutral"],
                                        "description": "信号类型：看多、看空或中性"
                                    },
                                    "confidence": {
                                        "type": "number",
                                        "description": "信号置信度（0-1之间的小数）"
                                    }
                                }
                            },
                            "description": "各个代理的信号"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "决策理由的详细说明"
                        },
                        "fundamental_analysis": {
                            "type": "object",
                            "properties": {
                                "profitability": {
                                    "type": "string",
                                    "description": "盈利能力分析"
                                },
                                "growth": {
                                    "type": "string",
                                    "description": "增长情况分析"
                                },
                                "financial_health": {
                                    "type": "string",
                                    "description": "财务健康分析"
                                },
                                "valuation_level": {
                                    "type": "string",
                                    "description": "估值水平分析"
                                }
                            },
                            "description": "基本面分析详情"
                        },
                        "valuation_analysis": {
                            "type": "object",
                            "properties": {
                                "dcf_gap": {
                                    "type": "string",
                                    "description": "DCF估值差距"
                                },
                                "owner_earnings_gap": {
                                    "type": "string",
                                    "description": "所有者收益法差距"
                                },
                                "overall_assessment": {
                                    "type": "string",
                                    "description": "总体估值评估"
                                }
                            },
                            "description": "估值分析详情"
                        },
                        "technical_analysis": {
                            "type": "object",
                            "properties": {
                                "trend": {
                                    "type": "string",
                                    "description": "趋势分析"
                                },
                                "momentum": {
                                    "type": "string",
                                    "description": "动量指标"
                                },
                                "volatility": {
                                    "type": "string",
                                    "description": "波动性分析"
                                }
                            },
                            "description": "技术分析详情"
                        },
                        "sentiment_analysis": {
                            "type": "string",
                            "description": "情绪分析详情"
                        },
                        "risk_assessment": {
                            "type": "object",
                            "properties": {
                                "risk_score": {
                                    "type": "string",
                                    "description": "风险评分"
                                },
                                "risk_level": {
                                    "type": "string",
                                    "enum": ["高", "中", "低"],
                                    "description": "风险水平"
                                },
                                "risk_management_advice": {
                                    "type": "string",
                                    "description": "风险管理建议"
                                }
                            },
                            "description": "风险评估详情"
                        }
                    },
                    "required": ["action", "quantity", "confidence", "agent_signals", "reasoning"]
                }
            }
        }
    ]

    # Create the user message
    user_message = {
        "role": "user",
        "content": f"""
        请基于以下分析做出投资决策：

        投资组合信息：
        - 仓位占比: {position_ratio}%
        - 持仓成本: {holding_cost}
        - 初始持仓: {initial_position}

        技术分析：
        {technical_message.content}

        基本面分析：
        {fundamentals_message.content}

        情绪分析：
        {sentiment_message.content}

        估值分析：
        {valuation_message.content}

        风险管理：
        {risk_message.content}

        请使用make_investment_decision工具返回您的决策，包括交易行动、数量、置信度和详细分析。
        """
    }

    # Get the completion from OpenRouter with tool calling
    try:
        print("\n尝试使用工具调用获取决策...")
        # 这里假设get_chat_completion函数支持tools参数
        # 如果不支持，需要修改该函数或使用其他支持工具调用的API
        result = get_chat_completion([system_message, user_message], tools=tools, tool_choice={"type": "function", "function": {"name": "make_investment_decision"}})

        # 解析API返回的结果
        print("\n调试信息 - API返回的原始结果:")
        print(result)

        # 尝试提取工具调用结果
        if isinstance(result, dict) and "tool_calls" in result:
            tool_call = result["tool_calls"][0]
            if tool_call["function"]["name"] == "make_investment_decision":
                decision_data = json.loads(tool_call["function"]["arguments"])
                print("\n成功提取工具调用结果")
            else:
                print("\n警告: 未找到make_investment_decision工具调用")
                decision_data = json.loads(result)
        else:
            # 如果没有工具调用，尝试直接解析结果
            print("\n警告: API返回结果中没有tool_calls字段，尝试直接解析结果")
            if isinstance(result, str):
                decision_data = json.loads(result)
            else:
                decision_data = result
    except Exception as e:
        print(f"\n使用工具调用获取决策失败: {str(e)}")
        print("回退到标准方式获取决策...")
        # 回退到标准方式
        result = get_chat_completion([system_message, user_message])
        try:
            if isinstance(result, str):
                decision_data = json.loads(result)
            else:
                decision_data = result
        except Exception as e:
            print(f"解析决策数据时出错: {str(e)}")
            decision_data = {
                "action": "hold",
                "quantity": 0,
                "confidence": 0.5,
                "agent_signals": [],
                "reasoning": "解析决策数据失败，默认为持有策略。"
            }

    # 检查agent_signals字段
    if "agent_signals" not in decision_data or not decision_data["agent_signals"]:
        print("警告: 决策数据中缺少agent_signals字段，使用默认值")
        decision_data["agent_signals"] = [
            {
                "agent_name": "technical_analysis",
                "signal": "neutral",
                "confidence": 0.5
            },
            {
                "agent_name": "fundamental_analysis",
                "signal": "neutral",
                "confidence": 0.5
            },
            {
                "agent_name": "sentiment_analysis",
                "signal": "neutral",
                "confidence": 0.5
            },
            {
                "agent_name": "valuation_analysis",
                "signal": "neutral",
                "confidence": 0.5
            },
            {
                "agent_name": "risk_management",
                "signal": "neutral",
                "confidence": 0.5
            }
        ]

    # 格式化决策
    formatted_decision = format_decision(
        action=decision_data.get("action", "hold"),
        quantity=decision_data.get("quantity", 0),
        confidence=decision_data.get("confidence", 0.5),
        agent_signals=decision_data.get("agent_signals", []),
        reasoning=decision_data.get("reasoning", "无决策依据"),
        detailed_analysis=decision_data
    )

    # 将格式化后的决策转换为JSON字符串
    result = json.dumps(formatted_decision, ensure_ascii=False)

    # Create the portfolio management message
    message = HumanMessage(
        content=result,
        name="portfolio_management",
    )

    # Print the decision if the flag is set
    if show_reasoning:
        try:
            # 尝试解析JSON字符串
            parsed_result = json.loads(result)

            # 先显示基本决策信息
            basic_info = {
                "action": parsed_result.get("action"),
                "quantity": parsed_result.get("quantity"),
                "confidence": parsed_result.get("confidence"),
                "agent_signals": parsed_result.get("agent_signals"),
                "reasoning": parsed_result.get("reasoning")
            }
            show_agent_reasoning(basic_info, "Portfolio Management Agent")

            # 如果存在详细分析报告，单独打印出来
            if "分析报告" in parsed_result:
                print("\n" + "=" * 80)
                print("详细投资分析报告".center(80))
                print("=" * 80)
                print(parsed_result["分析报告"])
                print("=" * 80 + "\n")

            # 创建一个新的消息，只包含基本决策信息，不包含详细分析报告
            basic_result = json.dumps(basic_info, ensure_ascii=False)
            message = HumanMessage(
                content=basic_result,
                name="portfolio_management",
            )
        except Exception as e:
            print(f"显示决策信息时出错: {str(e)}")
            show_agent_reasoning(result, "Portfolio Management Agent")

    return {
        "messages": state["messages"] + [message],
        "data":state["data"],
        }


def format_decision(action: str, quantity: int, confidence: float, agent_signals: list, reasoning: str, detailed_analysis=None) -> dict:
    """
    格式化决策数据，生成详细的分析报告

    Args:
        action: 交易行动（买入/卖出/持有）
        quantity: 交易数量
        confidence: 决策置信度
        agent_signals: 各代理的信号列表
        reasoning: 决策理由
        detailed_analysis: 详细分析数据（如果通过工具调用获取）

    Returns:
        dict: 格式化后的决策数据，包含详细分析报告
    """
    print("\n调试信息 - 格式化决策数据:")
    print(f"行动: {action}")
    print(f"数量: {quantity}")
    print(f"置信度: {confidence}")
    print(f"代理信号: {agent_signals}")
    print(f"详细分析: {detailed_analysis}")

    # 转换信号类型为中文
    def signal_to_chinese(signal):
        signal_map = {
            "bullish": "看多",
            "bearish": "看空",
            "neutral": "中性",
            "buy": "买入",
            "sell": "卖出",
            "hold": "持有"
        }
        return signal_map.get(signal, signal)

    # 安全获取置信度
    def safe_confidence(signal):
        try:
            if isinstance(signal, dict) and "confidence" in signal:
                return signal["confidence"]
            return 0.5
        except:
            return 0.5

    # 初始化格式化后的决策
    formatted_decision = {
        "action": action,
        "quantity": quantity,
        "confidence": confidence,
        "agent_signals": agent_signals,
        "reasoning": reasoning
    }

    try:
        # 如果有详细分析数据（通过工具调用获取），直接使用
        if detailed_analysis:
            # 构建详细分析报告
            analysis_report = "# 投资决策详细分析报告\n\n"

            # 基本面分析部分
            if "fundamental_analysis" in detailed_analysis:
                fundamental = detailed_analysis["fundamental_analysis"]
                analysis_report += "## 基本面分析\n\n"
                if isinstance(fundamental, dict):
                    if "profitability" in fundamental:
                        analysis_report += f"- **盈利能力**: {fundamental['profitability']}\n"
                    if "growth" in fundamental:
                        analysis_report += f"- **增长情况**: {fundamental['growth']}\n"
                    if "financial_health" in fundamental:
                        analysis_report += f"- **财务健康**: {fundamental['financial_health']}\n"
                    if "valuation_level" in fundamental:
                        analysis_report += f"- **估值水平**: {fundamental['valuation_level']}\n"
                else:
                    analysis_report += f"- {fundamental}\n"
                analysis_report += "\n"

            # 估值分析部分
            if "valuation_analysis" in detailed_analysis:
                valuation = detailed_analysis["valuation_analysis"]
                analysis_report += "## 估值分析\n\n"
                if isinstance(valuation, dict):
                    if "dcf_gap" in valuation:
                        analysis_report += f"- **DCF估值差距**: {valuation['dcf_gap']}\n"
                    if "owner_earnings_gap" in valuation:
                        analysis_report += f"- **所有者收益法差距**: {valuation['owner_earnings_gap']}\n"
                    if "overall_assessment" in valuation:
                        analysis_report += f"- **总体估值评估**: {valuation['overall_assessment']}\n"
                else:
                    analysis_report += f"- {valuation}\n"
                analysis_report += "\n"

            # 技术分析部分
            if "technical_analysis" in detailed_analysis:
                technical = detailed_analysis["technical_analysis"]
                analysis_report += "## 技术分析\n\n"
                if isinstance(technical, dict):
                    if "trend" in technical:
                        analysis_report += f"- **趋势分析**: {technical['trend']}\n"
                    if "momentum" in technical:
                        analysis_report += f"- **动量指标**: {technical['momentum']}\n"
                    if "volatility" in technical:
                        analysis_report += f"- **波动性分析**: {technical['volatility']}\n"
                else:
                    analysis_report += f"- {technical}\n"
                analysis_report += "\n"

            # 情绪分析部分
            if "sentiment_analysis" in detailed_analysis:
                sentiment = detailed_analysis["sentiment_analysis"]
                analysis_report += "## 情绪分析\n\n"
                analysis_report += f"- **市场情绪**: {sentiment}\n\n"

            # 风险评估部分
            if "risk_assessment" in detailed_analysis:
                risk = detailed_analysis["risk_assessment"]
                analysis_report += "## 风险评估\n\n"
                if isinstance(risk, dict):
                    if "risk_score" in risk:
                        analysis_report += f"- **风险评分**: {risk['risk_score']}\n"
                    if "risk_level" in risk:
                        analysis_report += f"- **风险水平**: {risk['risk_level']}\n"
                    if "risk_management_advice" in risk:
                        analysis_report += f"- **风险管理建议**: {risk['risk_management_advice']}\n"
                else:
                    analysis_report += f"- {risk}\n"
                analysis_report += "\n"

            # 决策总结
            analysis_report += "## 决策总结\n\n"
            analysis_report += f"- **交易行动**: {signal_to_chinese(action)}\n"
            analysis_report += f"- **交易数量**: {quantity}\n"
            analysis_report += f"- **置信度**: {confidence:.2f}\n\n"
            analysis_report += f"### 决策理由\n\n{reasoning}\n"

            # 添加到格式化决策中
            formatted_decision["分析报告"] = analysis_report

        else:
            # 如果没有详细分析数据，使用原有的方式生成报告
            # 尝试从agent_signals中提取信号
            try:
                # 打印调试信息
                print("\n调试信息 - 代理信号列表:")
                for signal in agent_signals:
                    print(signal)

                # 提取各类信号
                fundamental_signal = next((s for s in agent_signals if s.get("agent_name") == "fundamental_analysis"), {"signal": "neutral", "confidence": 0.5})
                valuation_signal = next((s for s in agent_signals if s.get("agent_name") == "valuation_analysis"), {"signal": "neutral", "confidence": 0.5})
                technical_signal = next((s for s in agent_signals if s.get("agent_name") == "technical_analysis"), {"signal": "neutral", "confidence": 0.5})
                sentiment_signal = next((s for s in agent_signals if s.get("agent_name") == "sentiment_analysis"), {"signal": "neutral", "confidence": 0.5})
                risk_signal = next((s for s in agent_signals if s.get("agent_name") == "risk_management"), {"signal": "neutral", "confidence": 0.5})

                # 构建详细分析报告
                analysis_report = "# 投资决策详细分析报告\n\n"

                # 基本面分析部分
                analysis_report += "## 基本面分析\n\n"
                analysis_report += f"- **信号**: {signal_to_chinese(fundamental_signal.get('signal', 'neutral'))}\n"
                analysis_report += f"- **置信度**: {safe_confidence(fundamental_signal):.2f}\n"
                analysis_report += "- **盈利能力**: 无详细数据\n"
                analysis_report += "- **增长情况**: 无详细数据\n"
                analysis_report += "- **财务健康**: 无详细数据\n\n"

                # 估值分析部分
                analysis_report += "## 估值分析\n\n"
                analysis_report += f"- **信号**: {signal_to_chinese(valuation_signal.get('signal', 'neutral'))}\n"
                analysis_report += f"- **置信度**: {safe_confidence(valuation_signal):.2f}\n"
                analysis_report += "- **DCF估值差距**: 无详细数据\n"
                analysis_report += "- **所有者收益法差距**: 无详细数据\n\n"

                # 技术分析部分
                analysis_report += "## 技术分析\n\n"
                analysis_report += f"- **信号**: {signal_to_chinese(technical_signal.get('signal', 'neutral'))}\n"
                analysis_report += f"- **置信度**: {safe_confidence(technical_signal):.2f}\n"
                analysis_report += "- **趋势分析**: 无详细数据\n"
                analysis_report += "- **动量指标**: 无详细数据\n"
                analysis_report += "- **波动性分析**: 无详细数据\n\n"

                # 情绪分析部分
                analysis_report += "## 情绪分析\n\n"
                analysis_report += f"- **信号**: {signal_to_chinese(sentiment_signal.get('signal', 'neutral'))}\n"
                analysis_report += f"- **置信度**: {safe_confidence(sentiment_signal):.2f}\n"
                analysis_report += "- **市场情绪**: 无详细数据\n\n"

                # 风险评估部分
                analysis_report += "## 风险评估\n\n"
                analysis_report += f"- **信号**: {signal_to_chinese(risk_signal.get('signal', 'neutral'))}\n"
                analysis_report += f"- **置信度**: {safe_confidence(risk_signal):.2f}\n"
                analysis_report += "- **风险评分**: 无详细数据\n"
                analysis_report += "- **风险管理建议**: 无详细数据\n\n"

                # 决策总结
                analysis_report += "## 决策总结\n\n"
                analysis_report += f"- **交易行动**: {signal_to_chinese(action)}\n"
                analysis_report += f"- **交易数量**: {quantity}\n"
                analysis_report += f"- **置信度**: {confidence:.2f}\n\n"
                analysis_report += f"### 决策理由\n\n{reasoning}\n"

                # 添加到格式化决策中
                formatted_decision["分析报告"] = analysis_report

            except Exception as e:
                print(f"生成详细分析报告时出错: {str(e)}")
                # 如果出错，添加简化版分析报告
                formatted_decision["分析报告"] = f"""# 投资决策简要报告

## 决策总结
- **交易行动**: {signal_to_chinese(action)}
- **交易数量**: {quantity}
- **置信度**: {confidence:.2f}

### 决策理由
{reasoning}
"""
    except Exception as e:
        print(f"格式化决策数据时出错: {str(e)}")
        # 如果出错，保持原始格式

    return formatted_decision
