# Qlib Expression Engine — Custom Factors & Rolling Operators Summary

# Qlib 表达式引擎 — 自定义因子与滚动算子总结

> Session: 2026-11-09 | Author: AI Assistant (DeepSeek-V4-Pro)

---

## 1. Expression Engine 文档阅读 / Reading the Expression Engine Docs

### 关键文档来源 / Key Documentation Sources

| 文档 | 路径 |
|------|------|
| Data Layer Overview | `docs/component/data.rst` |
| Building Formulaic Alphas | `docs/advanced/alpha.rst` |
| Expression Parser | `qlib/data/expression_parser.py` |
| All Operators | `qlib/data/ops.py` |
| Alpha158/Alpha360 Definitions | `qlib/contrib/data/loader.py` |

### 核心语法 / Core Syntax

| Category / 类别 | Syntax / 语法 | Example / 示例 |
|------|------|------|
| 字段引用 / Field Reference | `$field` / `$$field` | `$close`, `$volume` |
| 位移 / Shift | `Ref(feature, N)` | `Ref($close, 5)` |
| 四则运算 / Arithmetic | `+ - * /` | `$close / $open` |
| 条件 / Conditional | `If(cond, a, b)` | `If(Gt($close, $open), $close, $open)` |
| 比较 / Comparison | `Gt/Ge/Lt/Le/Eq/Ne` | `Gt($close, $open)` |
| 元素比较 / Element Compare | `> < >= <= == !=` | `($close > $open) & ($volume > 0)` |
| 逻辑 / Logic | `&` `|` | `($a > 0) & ($b < 10)` |
| 位置参数展开 / Unpack | `*` / `**` | `Ref(*[$close, 1])` / `Mean($close, **{'N': 5})` |

### 安全语法限制 / Safe Syntax Restrictions

- 不支持: lambda, comprehension, `__import__`, `getattr`, attribute access on expressions
- 常量整数限制 4096 位, 容器限制 4096 项
- Python `and`/`or`/`not` 仅限纯字面量条件；表达式级逻辑用 `&`/`|`/`If`
- 自定义算子需要在 `qlib.init(custom_ops=[...])` 中注册

---

## 2. 三个自定义因子 / Three Custom Factor Expressions

### Factor 1: Bollinger %B / 布林带位置百分比

```
($close - Mean($close, 20) + 2 * Std($close, 20)) / (4 * Std($close, 20) + 1e-12)
```

**逻辑 / Logic:** 计算收盘价在 Bollinger Bands (MA ± 2σ) 中的相对位置。
- \> 1: 突破上轨 (超买 / overbought)
- < 0: 跌破下轨 (超卖 / oversold)
- \~0.5: 在中轨附近 (near middle band)

**用到算子:** `Mean`, `Std` + 四则运算

---

### Factor 2: ATR Ratio / 平均真实波幅比率

```
Mean(Greater(Greater(Abs($high-$low), Abs($high-Ref($close,1))), Abs($low-Ref($close,1))), 14) / ($close + 1e-12)
```

**逻辑 / Logic:** True Range = max(high-low, |high-prev_close|, |low-prev_close|), 然后取 14 日均值 (ATR), 最后除以当前收盘价做归一化, 使跨股票可比。

**用到算子:** `Mean`, `Greater` (np.maximum), `Abs`, `Ref` + 嵌套调用

---

### Factor 3: Volume-Price Trend Ratio / 量价趋势比率

```
Sum(($close/Ref($close,1)-1) * $volume, 20) / (Sum($volume, 20) + 1e-12)
```

**逻辑 / Logic:** 过去 20 日每日涨跌幅按其成交量加权累加, 再除以总成交量归一化。上涨日放量 > 下跌日放量 → 正值 (净流入倾向), 反之为负值 (净流出倾向)。

**用到算子:** `Sum`, `Ref` + 乘除混合运算

### 使用示例 / Usage Example

```python
from qlib.data.dataset.loader import QlibDataLoader

my_factors = [
    "($close - Mean($close, 20) + 2 * Std($close, 20)) / (4 * Std($close, 20) + 1e-12)",
    "Mean(Greater(Greater(Abs($high-$low), Abs($high-Ref($close,1))), Abs($low-Ref($close,1))), 14) / ($close + 1e-12)",
    "Sum(($close/Ref($close,1)-1) * $volume, 20) / (Sum($volume, 20) + 1e-12)",
]
names = ["BB_PCT", "ATR_RATIO", "VPT_RATIO"]

loader = QlibDataLoader(config={"feature": (my_factors, names)})
df = loader.load(instruments='csi300', start_time='2020-01-01', end_time='2024-01-01')
print(df.head())
```

### 与 Alpha158 的关系 / Relationship with Alpha158

- Alpha158 是 Qlib 预定义的 158 个**固定因子集合**, 不是"任意 158 个因子"
- 这三个因子**不在** Alpha158 中 (经搜索确认), 是**新增补充**而非等价替代
- "Alpha161" 不是官方概念, 仅是非正式地 = Alpha158 (158) + 3 custom = 161 维

---

## 3. 滚动算子完整参考 / Complete Rolling Operator Reference

### 窗口参数 N 的通用规则 / Window Parameter N Rules

| N Value / N 取值 | Behavior / 行为 | Pandas Equivalent |
|----------|------|------|
| `N = 0` | 从序列起点累积 (expanding) | `series.expanding(min_periods=1)` |
| `0 < N < 1` (float) | 指数加权 (EWM), alpha = N | `series.ewm(alpha=N)` |
| `N >= 1` (int) | 固定窗口滚动 (rolling) | `series.rolling(N, min_periods=1)` |

---

### 单因子滚动 / Single-Feature Rolling: `Operator(feature, N)`

| # | Operator | 中文 | 底层实现 | Alpha158 对应 | Notes |
|---|----------|------|----------|--------------|-------|
| 1 | `Ref` | 位移引用 | `series.shift(N)` | — | N=0 返回首值; N<0 取未来值 |
| 2 | `Mean` | 滚动均值 | `rolling.mean()` | MA | — |
| 3 | `Sum` | 滚动求和 | `rolling.sum()` | — | — |
| 4 | `Std` | 滚动标准差 | `rolling.std()` | STD | 波动率指标 |
| 5 | `Var` | 滚动方差 | `rolling.var()` | — | Std² |
| 6 | `Skew` | 滚动偏度 | `rolling.skew()` | — | N ≥ 3; 衡量分布不对称性 |
| 7 | `Kurt` | 滚动峰度 | `rolling.kurt()` | — | N ≥ 4; 衡量肥尾程度 |
| 8 | `Max` | 滚动最大值 | `rolling.max()` | MAX | — |
| 9 | `Min` | 滚动最小值 | `rolling.min()` | MIN | — |
| 10 | `Med` | 滚动中位数 | `rolling.median()` | — | 比 Mean 更抗异常值 |
| 11 | `Mad` | 平均绝对偏差 | `apply(mad)` | — | mean(\|x - mean(x)\|) |
| 12 | `Rank` | 滚动百分位 | `rolling.rank(pct=True)` | RANK | 返回值 0~1 |
| 13 | `Quantile` | 滚动分位数 | `rolling.quantile(q)` | QTLU/QTLD | ⚠️ 三参数: `Quantile(f, N, q)` |
| 14 | `Count` | 非空计数 | `rolling.count()` | — | — |
| 15 | `Delta` | 滚动差值 | `series - series.shift(N)` | — | 当前值 - N 天前 |
| 16 | `Slope` | 线性回归斜率 | Cython `rolling_slope` | BETA | 趋势强度 |
| 17 | `Rsquare` | 线性回归 R² | Cython `rolling_rsquare` | RSQR | 趋势线性程度 |
| 18 | `Resi` | 回归残差 | Cython `rolling_resi` | RESI | 偏离趋势线程度 |
| 19 | `WMA` | 加权移动平均 | `apply(weighted_mean)` | — | 权重线性递增 |
| 20 | `EMA` | 指数加权平均 | `ewm(span=N)` | — | MACD 基础算子 |
| 21 | `IdxMax` | 最大值距今位置 | `rolling.idxmax()` | IMAX | Aroon 指标 |
| 22 | `IdxMin` | 最小值距今位置 | `rolling.idxmin()` | IMIN | Aroon 指标 |

---

### 双因子滚动 / Pair-Feature Rolling: `Operator(left, right, N)`

| # | Operator | 中文 | 底层实现 | Alpha158 对应 | Notes |
|---|----------|------|----------|--------------|-------|
| 23 | `Corr` | 滚动相关系数 | `rolling.corr()` | CORR / CORD | -1~1; 标准差≈0 时返回 NaN |
| 24 | `Cov` | 滚动协方差 | `rolling.cov()` | — | 未归一化, 保留量纲 |

---

### 典型使用模式 / Typical Usage Patterns

```python
# 1. 日收益率 / Daily Return
"Ref($close, 1) / $close - 1"

# 2. 20 日归一化波动率 / 20-day Normalized Volatility
"Std($close, 20) / $close"

# 3. RSV (Williams %R 基础) / RSV (Raw Stochastic Value)
"($close - Min($low, 20)) / (Max($high, 20) - Min($low, 20) + 1e-12)"

# 4. 20 日趋势斜率 / 20-day Trend Slope
"Slope($close, 20) / $close"

# 5. 60 日收益偏度 / 60-day Return Skewness
"Skew($close / Ref($close, 1) - 1, 60)"

# 6. 价格-成交量相关性 / Price-Volume Correlation
"Corr($close, Log($volume+1), 20)"

# 7. EMA 差值 (DIF) / EMA Difference (DIF)
"EMA($close, 12) - EMA($close, 26)"

# 8. 60 日价格百分位 / 60-day Price Percentile
"Rank($close, 60)"

# 9. 成交量加权涨跌比 / Volume-Weighted Up/Down Ratio
"Sum(($close/Ref($close,1)-1) * $volume, 20) / (Sum($volume, 20) + 1e-12)"

# 10. 布林带位置百分比 / Bollinger %B
"($close - Mean($close, 20) + 2 * Std($close, 20)) / (4 * Std($close, 20) + 1e-12)"
```

---

### Alpha158 滚动类因子一览 / Alpha158 Rolling Factor Composition

| 因子名 | 算子 | 窗口 | 说明 |
|--------|------|------|------|
| ROC | `Ref($close, d) / $close` | 5,10,20,30,60 | Rate of Change / 涨跌幅 |
| MA | `Mean($close, d) / $close` | 5,10,20,30,60 | Moving Average / 均线 |
| STD | `Std($close, d) / $close` | 5,10,20,30,60 | 标准差 / 波动率 |
| BETA | `Slope($close, d) / $close` | 5,10,20,30,60 | 线性斜率 / 趋势 |
| RSQR | `Rsquare($close, d)` | 5,10,20,30,60 | R² / 线性度 |
| RESI | `Resi($close, d) / $close` | 5,10,20,30,60 | 残差 |
| MAX | `Max($high, d) / $close` | 5,10,20,30,60 | 最高价 |
| MIN | `Min($low, d) / $close` | 5,10,20,30,60 | 最低价 |
| QTLU | `Quantile($close, d, 0.8) / $close` | 5,10,20,30,60 | 上 80% 分位 |
| QTLD | `Quantile($close, d, 0.2) / $close` | 5,10,20,30,60 | 下 20% 分位 |
| RANK | `Rank($close, d)` | 5,10,20,30,60 | 百分位 |
| RSV | 组合公式 | 5,10,20,30,60 | Raw Stochastic Value |
| IMAX | `IdxMax($high, d) / d` | 5,10,20,30,60 | 新高距今 |
| IMIN | `IdxMin($low, d) / d` | 5,10,20,30,60 | 新低距今 |
| IMXD | 组合公式 | 5,10,20,30,60 | IMAX - IMIN |
| CORR | `Corr($close, Log($volume+1), d)` | 5,10,20,30,60 | 价格-量相关性 |
| CORD | `Corr(r1, r2, d)` | 5,10,20,30,60 | 涨跌幅-量比相关性 |
| CNTP | `Mean($close > Ref($close,1), d)` | 5,10,20,30,60 | 上涨天数占比 |
| CNTN | `Mean($close < Ref($close,1), d)` | 5,10,20,30,60 | 下跌天数占比 |
| CNTD | CNTP - CNTN | 5,10,20,30,60 | 涨跌天数差 |
| SUMP | 组合公式 | 5,10,20,30,60 | 总涨幅占比 (RSI-like) |
| SUMN | 组合公式 | 5,10,20,30,60 | 总跌幅占比 |
| SUMD | SUMP - SUMN | 5,10,20,30,60 | 涨跌幅差 |
| VMA | `Mean($volume, d) / ($volume+1e-12)` | 5,10,20,30,60 | 量均线 |
| VSTD | `Std($volume, d) / ($volume+1e-12)` | 5,10,20,30,60 | 量波动率 |
| WVMA | 组合公式 | 5,10,20,30,60 | 成交量加权价格波动 |
| VSUMP | 组合公式 | 5,10,20,30,60 | 量增占比 |
| VSUMN | 组合公式 | 5,10,20,30,60 | 量减占比 |
| VSUMD | VSUMP - VSUMN | 5,10,20,30,60 | 量增减差 |

---

### 相关源码文件 / Related Source Files

| 文件 / File | 作用 / Purpose |
|------|------|
| [ops.py](file:///f:/treaWorkSpace/Qlib/qlib/data/ops.py) | 所有算子的定义 / All operator definitions |
| [expression_parser.py](file:///f:/treaWorkSpace/Qlib/qlib/data/expression_parser.py) | 表达式语法解析器 / Expression syntax parser |
| [loader.py](file:///f:/treaWorkSpace/Qlib/qlib/contrib/data/loader.py) | Alpha158/Alpha360 因子定义 / Alpha158/360 factor definitions |
| [handler.py](file:///f:/treaWorkSpace/Qlib/qlib/contrib/data/handler.py) | DataHandler 配置 / DataHandler configurations |
| [data.rst](file:///f:/treaWorkSpace/Qlib/docs/component/data.rst) | Data Layer 文档 / Data Layer documentation |
| [alpha.rst](file:///f:/treaWorkSpace/Qlib/docs/advanced/alpha.rst) | Formulaic Alphas 文档 / Custom alpha documentation |