import pandas as pd

from ngmi.config import AttentionConfig
from ngmi.models import Signal
from ngmi.rules.base import classify_high_is_bad, state_since, tail_days

BASELINE_DAYS = 365


def evaluate(views: pd.Series, cfg: AttentionConfig, article: str) -> Signal:
    if len(views) < BASELINE_DAYS:
        raise ValueError(f"need {BASELINE_DAYS} days of pageviews, got {len(views)}")
    ratio = (views.rolling(cfg.avg_days).mean() / views.rolling(BASELINE_DAYS).median()).dropna()
    statuses = ratio.map(lambda v: classify_high_is_bad(v, cfg.amber, cfg.red))
    value, status = float(ratio.iloc[-1]), statuses.iloc[-1]

    if status == "red":
        rule = f"Retail is piling in: {value:.1f}x normal interest. Past tops saw 3-10x. Consider trimming."
    elif status == "amber":
        rule = f"Interest is heating up ({value:.1f}x normal). Red at {cfg.red:g}x."
    else:
        rule = f"Retail isn't paying attention ({value:.1f}x normal). Amber at {cfg.amber:g}x."

    return Signal(
        id=f"attention:{article}",
        name=f"{article.replace('_', ' ')} · attention",
        unit="x normal",
        value=round(value, 2),
        status=status,
        rule=rule,
        state_since=state_since(statuses),
        spark=tail_days(ratio, 365),
        spark_days=365,
        source_url=f"https://pageviews.wmcloud.org/?project=en.wikipedia.org&platform=all-access&agent=user&range=all-time&pages={article}",
    )
