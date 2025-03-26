import math
from typing import Dict

from langchain_core.messages import HumanMessage

from src.agents.state import AgentState, show_agent_reasoning

import json
import pandas as pd
import numpy as np

from src.tools.api import prices_to_df


##### Technical Analyst #####
def technical_analyst_agent(state: AgentState):
    """
    Technical analysis agent that analyzes price patterns and indicators
    to generate trading signals.
    """
    show_reasoning = state["metadata"]["show_reasoning"]
    data = state["data"]

    # 尝试获取价格数据，兼容不同的键名
    if "price_history" in data:
        prices_df = data["price_history"]
    elif "prices" in data:
        prices = data["prices"]
        prices_df = prices_to_df(prices)
    else:
        # 如果找不到价格数据，返回中性信号
        message_content = {
            "signal": "neutral",
            "confidence": "0%",
            "reasoning": {"error": "No price data found in state"}
        }
        message = HumanMessage(
            content=json.dumps(message_content),
            name="technicals",
        )
        return {
            "messages": [message],
            "data": data,
        }

    # 确保 prices_df 不为空
    if prices_df is None or len(prices_df) < 20:  # 至少需要20个数据点
        message_content = {
            "signal": "neutral",
            "confidence": "0%",
            "reasoning": {"error": "Insufficient price data for technical analysis"}
        }
        message = HumanMessage(
            content=json.dumps(message_content),
            name="technicals",
        )
        return {
            "messages": [message],
            "data": data,
        }

    # 计算各种技术分析策略的信号
    try:
        trend_signals = calculate_trend_signals(prices_df)
        mean_reversion_signals = calculate_mean_reversion_signals(prices_df)
        momentum_signals = calculate_momentum_signals(prices_df)
        volatility_signals = calculate_volatility_signals(prices_df)
        stat_arb_signals = calculate_stat_arb_signals(prices_df)

        # 安全检查：确保所有信号的 confidence 值不是 NaN
        for signal_dict in [trend_signals, mean_reversion_signals, momentum_signals, volatility_signals, stat_arb_signals]:
            if pd.isna(signal_dict['confidence']):
                signal_dict['confidence'] = 0.5  # 使用默认值0.5替代NaN

        # 组合不同策略的信号
        combined_signal = weighted_signal_combination(
            [
                trend_signals,
                mean_reversion_signals,
                momentum_signals,
                volatility_signals,
                stat_arb_signals
            ],
            [0.3, 0.2, 0.25, 0.15, 0.1]  # 权重
        )

        # 构建分析报告
        analysis_report = {
            "signal": combined_signal['signal'],
            "confidence": f"{round(float(combined_signal['confidence']) * 100)}%",
            "strategy_signals": {
                "trend_following": {
                    "signal": trend_signals['signal'],
                    "confidence": f"{round(float(trend_signals['confidence']) * 100)}%",
                    "metrics": normalize_pandas(trend_signals['metrics'])
                },
                "mean_reversion": {
                    "signal": mean_reversion_signals['signal'],
                    "confidence": f"{round(float(mean_reversion_signals['confidence']) * 100)}%",
                    "metrics": normalize_pandas(mean_reversion_signals['metrics'])
                },
                "momentum": {
                    "signal": momentum_signals['signal'],
                    "confidence": f"{round(float(momentum_signals['confidence']) * 100)}%",
                    "metrics": normalize_pandas(momentum_signals['metrics'])
                },
                "volatility": {
                    "signal": volatility_signals['signal'],
                    "confidence": f"{round(float(volatility_signals['confidence']) * 100)}%",
                    "metrics": normalize_pandas(volatility_signals['metrics'])
                },
                "statistical_arbitrage": {
                    "signal": stat_arb_signals['signal'],
                    "confidence": f"{round(float(stat_arb_signals['confidence']) * 100)}%",
                    "metrics": normalize_pandas(stat_arb_signals['metrics'])
                }
            }
        }
    except Exception as e:
        # 捕获所有异常，返回中性信号
        print(f"Technical analysis error: {str(e)}")
        message_content = {
            "signal": "neutral",
            "confidence": "0%",
            "reasoning": {"error": f"Error in technical analysis: {str(e)}"}
        }
        message = HumanMessage(
            content=json.dumps(message_content),
            name="technicals",
        )
        return {
            "messages": [message],
            "data": data,
        }

    message_content = {
        "signal": analysis_report["signal"],
        "confidence": analysis_report["confidence"],
        "reasoning": analysis_report["strategy_signals"]
    }

    message = HumanMessage(
        content=json.dumps(message_content),
        name="technicals",
    )

    if show_reasoning:
        show_agent_reasoning(message_content, "Technical Analysis Agent")

    return {
        "messages": [message],
        "data": data,
    }


def calculate_trend_signals(prices_df):
    """
    Advanced trend following strategy using multiple timeframes and indicators
    """
    # Calculate EMAs for multiple timeframes
    ema_8 = calculate_ema(prices_df, 8)
    ema_21 = calculate_ema(prices_df, 21)
    ema_55 = calculate_ema(prices_df, 55)

    # Calculate ADX for trend strength
    adx = calculate_adx(prices_df, 14)

    # Calculate Ichimoku Cloud
    ichimoku = calculate_ichimoku(prices_df)

    # Determine trend direction and strength
    short_trend = ema_8 > ema_21
    medium_trend = ema_21 > ema_55

    # 安全检查：确保 ADX 值不是 NaN
    adx_value = adx['adx'].iloc[-1]
    if pd.isna(adx_value):
        adx_value = 25.0  # 使用中等强度的默认值

    # Combine signals with confidence weighting
    trend_strength = adx_value / 100.0

    if short_trend.iloc[-1] and medium_trend.iloc[-1]:
        signal = 'bullish'
        confidence = trend_strength
    elif not short_trend.iloc[-1] and not medium_trend.iloc[-1]:
        signal = 'bearish'
        confidence = trend_strength
    else:
        signal = 'neutral'
        confidence = 0.5

    return {
        'signal': signal,
        'confidence': confidence,
        'metrics': {
            'adx': float(adx_value),
            'trend_strength': float(trend_strength),
            # 'ichimoku': ichimoku
            'short_trend': bool(short_trend.iloc[-1]),
            'medium_trend': bool(medium_trend.iloc[-1])
        }
    }


def calculate_mean_reversion_signals(prices_df):
    """
    Mean reversion strategy using statistical measures and Bollinger Bands
    """
    # Calculate z-score of price relative to moving average
    ma_50 = prices_df['close'].rolling(window=50).mean()
    std_50 = prices_df['close'].rolling(window=50).std()
    z_score = (prices_df['close'] - ma_50) / std_50

    # Calculate Bollinger Bands
    bb_upper, bb_lower = calculate_bollinger_bands(prices_df)

    # Calculate RSI with multiple timeframes
    rsi_14 = calculate_rsi(prices_df, 14)
    rsi_28 = calculate_rsi(prices_df, 28)

    # Mean reversion signals
    extreme_z_score = abs(z_score.iloc[-1]) > 2

    # 安全计算 price_vs_bb
    bb_range = bb_upper.iloc[-1] - bb_lower.iloc[-1]
    if pd.isna(bb_range) or bb_range == 0:
        price_vs_bb = 0.5  # 如果分母为零或NaN，则设置为中间值0.5
    else:
        price_vs_bb = (prices_df['close'].iloc[-1] - bb_lower.iloc[-1]) / bb_range

    # Combine signals
    if z_score.iloc[-1] < -2 and price_vs_bb < 0.2:
        signal = 'bullish'
        confidence = min(abs(z_score.iloc[-1]) / 4, 1.0)
    elif z_score.iloc[-1] > 2 and price_vs_bb > 0.8:
        signal = 'bearish'
        confidence = min(abs(z_score.iloc[-1]) / 4, 1.0)
    else:
        signal = 'neutral'
        confidence = 0.5

    return {
        'signal': signal,
        'confidence': confidence,
        'metrics': {
            'z_score': float(z_score.iloc[-1]),
            'price_vs_bb': float(price_vs_bb),
            'rsi_14': float(rsi_14.iloc[-1]),
            'rsi_28': float(rsi_28.iloc[-1])
        }
    }


def calculate_momentum_signals(prices_df):
    """
    Multi-factor momentum strategy with conservative settings
    """
    # Price momentum with adjusted min_periods
    returns = prices_df['close'].pct_change()
    mom_1m = returns.rolling(21, min_periods=5).sum()  # 短期动量允许较少数据点
    mom_3m = returns.rolling(63, min_periods=42).sum()  # 中期动量要求更多数据点
    mom_6m = returns.rolling(126, min_periods=63).sum()  # 长期动量保持严格要求

    # Volume momentum
    volume_ma = prices_df['volume'].rolling(21, min_periods=10).mean()
    volume_momentum = prices_df['volume'] / volume_ma

    # 处理NaN值
    mom_1m = mom_1m.fillna(0)  # 短期动量可以用0填充
    mom_3m = mom_3m.fillna(mom_1m)  # 中期动量可以用短期动量填充
    mom_6m = mom_6m.fillna(mom_3m)  # 长期动量可以用中期动量填充

    # Calculate momentum score with more weight on longer timeframes
    momentum_score = (
        0.2 * mom_1m +  # 降低短期权重
        0.3 * mom_3m +
        0.5 * mom_6m    # 增加长期权重
    ).iloc[-1]

    # Volume confirmation
    volume_confirmation = volume_momentum.iloc[-1] > 1.0

    if momentum_score > 0.05 and volume_confirmation:
        signal = 'bullish'
        confidence = min(abs(momentum_score) * 5, 1.0)
    elif momentum_score < -0.05 and volume_confirmation:
        signal = 'bearish'
        confidence = min(abs(momentum_score) * 5, 1.0)
    else:
        signal = 'neutral'
        confidence = 0.5

    return {
        'signal': signal,
        'confidence': confidence,
        'metrics': {
            'momentum_1m': float(mom_1m.iloc[-1]),
            'momentum_3m': float(mom_3m.iloc[-1]),
            'momentum_6m': float(mom_6m.iloc[-1]),
            'volume_momentum': float(volume_momentum.iloc[-1])
        }
    }


def calculate_volatility_signals(prices_df):
    """
    Optimized volatility calculation with shorter lookback periods
    """
    returns = prices_df['close'].pct_change()

    # 使用更短的周期和最小周期要求计算历史波动率
    hist_vol = returns.rolling(21, min_periods=10).std() * math.sqrt(252)

    # 使用更短的周期计算波动率均值，并允许更少的数据点
    vol_ma = hist_vol.rolling(42, min_periods=21).mean()
    vol_regime = hist_vol / vol_ma

    # 使用更灵活的标准差计算
    vol_std = hist_vol.rolling(42, min_periods=21).std()
    vol_z_score = (hist_vol - vol_ma) / vol_std.replace(0, np.nan)

    # ATR计算优化
    atr = calculate_atr(prices_df, period=14, min_periods=7)
    atr_ratio = atr / prices_df['close']

    # 如果关键指标为NaN，使用替代值而不是直接返回中性信号
    if pd.isna(vol_regime.iloc[-1]):
        vol_regime.iloc[-1] = 1.0  # 假设处于正常波动率区间
    if pd.isna(vol_z_score.iloc[-1]):
        vol_z_score.iloc[-1] = 0.0  # 假设处于均值位置

    # Generate signal based on volatility regime
    current_vol_regime = vol_regime.iloc[-1]
    vol_z = vol_z_score.iloc[-1]

    if current_vol_regime < 0.8 and vol_z < -1:
        signal = 'bullish'  # Low vol regime, potential for expansion
        confidence = min(abs(vol_z) / 3, 1.0)
    elif current_vol_regime > 1.2 and vol_z > 1:
        signal = 'bearish'  # High vol regime, potential for contraction
        confidence = min(abs(vol_z) / 3, 1.0)
    else:
        signal = 'neutral'
        confidence = 0.5

    return {
        'signal': signal,
        'confidence': confidence,
        'metrics': {
            'historical_volatility': float(hist_vol.iloc[-1]),
            'volatility_regime': float(current_vol_regime),
            'volatility_z_score': float(vol_z),
            'atr_ratio': float(atr_ratio.iloc[-1])
        }
    }


def calculate_stat_arb_signals(prices_df):
    """
    Optimized statistical arbitrage signals with shorter lookback periods
    """
    # Calculate price distribution statistics
    returns = prices_df['close'].pct_change()

    # 使用更短的周期计算偏度和峰度
    skew = returns.rolling(42, min_periods=21).skew()
    kurt = returns.rolling(42, min_periods=21).kurt()

    # 优化Hurst指数计算
    hurst = calculate_hurst_exponent(prices_df['close'], max_lag=10)

    # 处理NaN值
    if pd.isna(skew.iloc[-1]):
        skew.iloc[-1] = 0.0  # 假设正态分布
    if pd.isna(kurt.iloc[-1]):
        kurt.iloc[-1] = 3.0  # 假设正态分布

    # Generate signal based on statistical properties
    if hurst < 0.4 and skew.iloc[-1] > 1:
        signal = 'bullish'
        confidence = (0.5 - hurst) * 2
    elif hurst < 0.4 and skew.iloc[-1] < -1:
        signal = 'bearish'
        confidence = (0.5 - hurst) * 2
    else:
        signal = 'neutral'
        confidence = 0.5

    return {
        'signal': signal,
        'confidence': confidence,
        'metrics': {
            'hurst_exponent': float(hurst),
            'skewness': float(skew.iloc[-1]),
            'kurtosis': float(kurt.iloc[-1])
        }
    }


def weighted_signal_combination(signals, weights):
    """
    Combines multiple trading signals using a weighted approach

    Args:
        signals: 列表形式的信号字典，每个字典包含 'signal' 和 'confidence' 键
        weights: 列表形式的权重，与 signals 列表长度相同

    Returns:
        包含 'signal' 和 'confidence' 键的字典
    """
    # Convert signals to numeric values
    signal_values = {
        'bullish': 1,
        'neutral': 0,
        'bearish': -1
    }

    weighted_sum = 0
    total_confidence = 0

    # 检查参数类型，支持两种调用方式
    if isinstance(signals, dict) and isinstance(weights, dict):
        # 原始调用方式：signals 和 weights 都是字典
        for strategy, signal in signals.items():
            numeric_signal = signal_values[signal['signal']]
            weight = weights[strategy]
            confidence = signal['confidence']

            weighted_sum += numeric_signal * weight * confidence
            total_confidence += weight * confidence
    elif isinstance(signals, list) and isinstance(weights, list):
        # 新的调用方式：signals 和 weights 都是列表
        if len(signals) != len(weights):
            print(f"警告：信号列表长度 ({len(signals)}) 与权重列表长度 ({len(weights)}) 不匹配")
            # 使用较短的长度
            length = min(len(signals), len(weights))
            signals = signals[:length]
            weights = weights[:length]

        for i, signal in enumerate(signals):
            numeric_signal = signal_values[signal['signal']]
            weight = weights[i]
            confidence = signal['confidence']

            weighted_sum += numeric_signal * weight * confidence
            total_confidence += weight * confidence
    else:
        print(f"警告：不支持的参数类型 - signals: {type(signals)}, weights: {type(weights)}")
        return {'signal': 'neutral', 'confidence': 0.5}

    # Normalize the weighted sum
    if total_confidence > 0:
        final_score = weighted_sum / total_confidence
    else:
        final_score = 0

    # Convert back to signal
    if final_score > 0.2:
        signal = 'bullish'
    elif final_score < -0.2:
        signal = 'bearish'
    else:
        signal = 'neutral'

    return {
        'signal': signal,
        'confidence': abs(final_score)
    }


def normalize_pandas(obj):
    """Convert pandas Series/DataFrames to primitive Python types"""
    if isinstance(obj, pd.Series):
        return obj.tolist()
    elif isinstance(obj, pd.DataFrame):
        return obj.to_dict('records')
    elif isinstance(obj, dict):
        return {k: normalize_pandas(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [normalize_pandas(item) for item in obj]
    return obj


def calculate_macd(prices_df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    ema_12 = prices_df['close'].ewm(span=12, adjust=False).mean()
    ema_26 = prices_df['close'].ewm(span=26, adjust=False).mean()
    macd_line = ema_12 - ema_26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    return macd_line, signal_line


def calculate_rsi(prices_df: pd.DataFrame, period: int = 14) -> pd.Series:
    delta = prices_df['close'].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_bollinger_bands(
    prices_df: pd.DataFrame,
    window: int = 20
) -> tuple[pd.Series, pd.Series]:
    sma = prices_df['close'].rolling(window).mean()
    std_dev = prices_df['close'].rolling(window).std()
    upper_band = sma + (std_dev * 2)
    lower_band = sma - (std_dev * 2)
    return upper_band, lower_band


def calculate_ema(df: pd.DataFrame, window: int) -> pd.Series:
    """
    Calculate Exponential Moving Average

    Args:
        df: DataFrame with price data
        window: EMA period

    Returns:
        pd.Series: EMA values
    """
    return df['close'].ewm(span=window, adjust=False).mean()


def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Calculate Average Directional Index (ADX)

    Args:
        df: DataFrame with OHLC data
        period: Period for calculations

    Returns:
        DataFrame with ADX values
    """
    # Calculate True Range
    df['high_low'] = df['high'] - df['low']
    df['high_close'] = abs(df['high'] - df['close'].shift())
    df['low_close'] = abs(df['low'] - df['close'].shift())
    df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)

    # Calculate Directional Movement
    df['up_move'] = df['high'] - df['high'].shift()
    df['down_move'] = df['low'].shift() - df['low']

    df['plus_dm'] = np.where(
        (df['up_move'] > df['down_move']) & (df['up_move'] > 0),
        df['up_move'],
        0
    )
    df['minus_dm'] = np.where(
        (df['down_move'] > df['up_move']) & (df['down_move'] > 0),
        df['down_move'],
        0
    )

    # Calculate ADX
    df['+di'] = 100 * (df['plus_dm'].ewm(span=period).mean() /
                       df['tr'].ewm(span=period).mean())
    df['-di'] = 100 * (df['minus_dm'].ewm(span=period).mean() /
                       df['tr'].ewm(span=period).mean())
    df['dx'] = 100 * abs(df['+di'] - df['-di']) / (df['+di'] + df['-di'])
    df['adx'] = df['dx'].ewm(span=period).mean()

    return df[['adx', '+di', '-di']]


def calculate_ichimoku(df: pd.DataFrame) -> Dict[str, pd.Series]:
    """
    Calculate Ichimoku Cloud indicators

    Args:
        df: DataFrame with OHLC data

    Returns:
        Dictionary containing Ichimoku components
    """
    # Tenkan-sen (Conversion Line): (9-period high + 9-period low)/2
    period9_high = df['high'].rolling(window=9).max()
    period9_low = df['low'].rolling(window=9).min()
    tenkan_sen = (period9_high + period9_low) / 2

    # Kijun-sen (Base Line): (26-period high + 26-period low)/2
    period26_high = df['high'].rolling(window=26).max()
    period26_low = df['low'].rolling(window=26).min()
    kijun_sen = (period26_high + period26_low) / 2

    # Senkou Span A (Leading Span A): (Conversion Line + Base Line)/2
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(26)

    # Senkou Span B (Leading Span B): (52-period high + 52-period low)/2
    period52_high = df['high'].rolling(window=52).max()
    period52_low = df['low'].rolling(window=52).min()
    senkou_span_b = ((period52_high + period52_low) / 2).shift(26)

    # Chikou Span (Lagging Span): Close shifted back 26 periods
    chikou_span = df['close'].shift(-26)

    return {
        'tenkan_sen': tenkan_sen,
        'kijun_sen': kijun_sen,
        'senkou_span_a': senkou_span_a,
        'senkou_span_b': senkou_span_b,
        'chikou_span': chikou_span
    }


def calculate_atr(df: pd.DataFrame, period: int = 14, min_periods: int = 7) -> pd.Series:
    """
    Optimized ATR calculation with minimum periods parameter

    Args:
        df: DataFrame with OHLC data
        period: Period for ATR calculation
        min_periods: Minimum number of periods required

    Returns:
        pd.Series: ATR values
    """
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())

    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)

    return true_range.rolling(period, min_periods=min_periods).mean()


def calculate_hurst_exponent(price_series: pd.Series, max_lag: int = 10) -> float:
    """
    Optimized Hurst exponent calculation with shorter lookback and better error handling

    Args:
        price_series: Array-like price data
        max_lag: Maximum lag for R/S calculation (reduced from 20 to 10)

    Returns:
        float: Hurst exponent
    """
    try:
        # 使用对数收益率而不是价格
        returns = np.log(price_series / price_series.shift(1)).dropna()

        # 如果数据不足，返回0.5（随机游走）
        if len(returns) < max_lag * 2:
            return 0.5

        lags = range(2, max_lag)
        # 使用更稳定的计算方法
        tau = [np.sqrt(np.std(np.subtract(returns[lag:], returns[:-lag])))
               for lag in lags]

        # 添加小的常数避免log(0)
        tau = [max(1e-8, t) for t in tau]

        # 使用对数回归计算Hurst指数
        reg = np.polyfit(np.log(lags), np.log(tau), 1)
        h = reg[0]

        # 限制Hurst指数在合理范围内
        return max(0.0, min(1.0, h))

    except (ValueError, RuntimeWarning, np.linalg.LinAlgError):
        # 如果计算失败，返回0.5表示随机游走
        return 0.5


def calculate_obv(prices_df: pd.DataFrame) -> pd.Series:
    obv = [0]
    for i in range(1, len(prices_df)):
        if prices_df['close'].iloc[i] > prices_df['close'].iloc[i - 1]:
            obv.append(obv[-1] + prices_df['volume'].iloc[i])
        elif prices_df['close'].iloc[i] < prices_df['close'].iloc[i - 1]:
            obv.append(obv[-1] - prices_df['volume'].iloc[i])
        else:
            obv.append(obv[-1])
    prices_df['OBV'] = obv
    return prices_df['OBV']
