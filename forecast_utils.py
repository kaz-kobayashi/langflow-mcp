"""
需要予測ユーティリティ関数

軽量な時系列予測手法を提供:
- 移動平均法 (Moving Average)
- 指数平滑法 (Exponential Smoothing)
- 線形トレンド法 (Linear Trend)
"""

import numpy as np
from scipy import stats
from typing import Tuple, Dict, List


def moving_average_forecast(
    demand: np.ndarray,
    forecast_periods: int,
    window: int = None
) -> Tuple[np.ndarray, float]:
    """
    移動平均法による需要予測

    Parameters
    ----------
    demand : np.ndarray
        過去の需要データ
    forecast_periods : int
        予測期間数
    window : int, optional
        移動平均のウィンドウサイズ（Noneの場合は全データの平均）

    Returns
    -------
    forecast : np.ndarray
        予測値
    error_std : float
        予測誤差の標準偏差
    """
    if window is None:
        window = min(len(demand), 12)  # デフォルト: 最大12期間

    # 移動平均の計算
    if len(demand) >= window:
        ma = np.mean(demand[-window:])
    else:
        ma = np.mean(demand)

    # 全期間同じ値で予測
    forecast = np.full(forecast_periods, ma)

    # 予測誤差の推定（過去データの標準偏差）
    error_std = np.std(demand)

    return forecast, error_std


def exponential_smoothing_forecast(
    demand: np.ndarray,
    forecast_periods: int,
    alpha: float = 0.3
) -> Tuple[np.ndarray, float]:
    """
    指数平滑法による需要予測

    Parameters
    ----------
    demand : np.ndarray
        過去の需要データ
    forecast_periods : int
        予測期間数
    alpha : float
        平滑化パラメータ（0-1）。大きいほど最近のデータを重視

    Returns
    -------
    forecast : np.ndarray
        予測値
    error_std : float
        予測誤差の標準偏差
    """
    # 指数平滑化
    smoothed = np.zeros(len(demand))
    smoothed[0] = demand[0]

    for t in range(1, len(demand)):
        smoothed[t] = alpha * demand[t] + (1 - alpha) * smoothed[t-1]

    # 最後の平滑化値を予測値として使用
    last_value = smoothed[-1]
    forecast = np.full(forecast_periods, last_value)

    # 誤差の計算
    errors = demand[1:] - smoothed[:-1]
    error_std = np.std(errors)

    return forecast, error_std


def linear_trend_forecast(
    demand: np.ndarray,
    forecast_periods: int
) -> Tuple[np.ndarray, float, float, float]:
    """
    線形トレンド法による需要予測

    Parameters
    ----------
    demand : np.ndarray
        過去の需要データ
    forecast_periods : int
        予測期間数

    Returns
    -------
    forecast : np.ndarray
        予測値
    error_std : float
        予測誤差の標準偏差
    trend : float
        トレンド係数
    intercept : float
        切片
    """
    n = len(demand)
    x = np.arange(n)

    # 線形回帰
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, demand)

    # 予測
    future_x = np.arange(n, n + forecast_periods)
    forecast = slope * future_x + intercept

    # 残差の標準偏差
    fitted = slope * x + intercept
    residuals = demand - fitted
    error_std = np.std(residuals)

    return forecast, error_std, slope, intercept


def calculate_confidence_interval(
    forecast: np.ndarray,
    error_std: float,
    confidence_level: float = 0.95
) -> Tuple[np.ndarray, np.ndarray]:
    """
    予測値の信頼区間を計算

    Parameters
    ----------
    forecast : np.ndarray
        予測値
    error_std : float
        予測誤差の標準偏差
    confidence_level : float
        信頼水準（0-1）

    Returns
    -------
    lower_bound : np.ndarray
        下限値
    upper_bound : np.ndarray
        上限値
    """
    # z値の計算
    z = stats.norm.ppf((1 + confidence_level) / 2)

    # 予測期間が進むほど信頼区間が広がる
    periods = np.arange(1, len(forecast) + 1)
    margin = z * error_std * np.sqrt(periods)

    lower_bound = forecast - margin
    upper_bound = forecast + margin

    # 需要は非負
    lower_bound = np.maximum(lower_bound, 0)

    return lower_bound, upper_bound


def forecast_demand(
    demand_history: List[float],
    forecast_periods: int = 7,
    method: str = "exponential_smoothing",
    confidence_level: float = 0.95,
    **kwargs
) -> Dict:
    """
    需要予測のメイン関数

    Parameters
    ----------
    demand_history : List[float]
        過去の需要データ
    forecast_periods : int
        予測期間数
    method : str
        予測手法 ("moving_average", "exponential_smoothing", "linear_trend")
    confidence_level : float
        信頼水準
    **kwargs : dict
        各手法固有のパラメータ
        - moving_average: window
        - exponential_smoothing: alpha

    Returns
    -------
    result : Dict
        予測結果
    """
    demand = np.array(demand_history)

    if len(demand) < 2:
        raise ValueError("需要データが不足しています（最低2期間必要）")

    # 予測手法の選択
    if method == "moving_average":
        window = kwargs.get("window", None)
        forecast, error_std = moving_average_forecast(demand, forecast_periods, window)
        method_info = {"method": "移動平均法", "window": window or min(len(demand), 12)}

    elif method == "exponential_smoothing":
        alpha = kwargs.get("alpha", 0.3)
        forecast, error_std = exponential_smoothing_forecast(demand, forecast_periods, alpha)
        method_info = {"method": "指数平滑法", "alpha": alpha}

    elif method == "linear_trend":
        forecast, error_std, slope, intercept = linear_trend_forecast(demand, forecast_periods)
        method_info = {
            "method": "線形トレンド法",
            "trend": float(slope),
            "intercept": float(intercept)
        }
    else:
        raise ValueError(f"未知の予測手法: {method}")

    # 信頼区間の計算
    lower_bound, upper_bound = calculate_confidence_interval(
        forecast, error_std, confidence_level
    )

    # 統計情報
    historical_stats = {
        "mean": float(np.mean(demand)),
        "std": float(np.std(demand)),
        "min": float(np.min(demand)),
        "max": float(np.max(demand)),
        "last_value": float(demand[-1]),
        "data_points": len(demand)
    }

    return {
        "forecast": forecast.tolist(),
        "lower_bound": lower_bound.tolist(),
        "upper_bound": upper_bound.tolist(),
        "error_std": float(error_std),
        "confidence_level": confidence_level,
        "method_info": method_info,
        "historical_stats": historical_stats
    }
