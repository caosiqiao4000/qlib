# Alpha158 vs Alpha360 — Why Tree Models Use Alpha158 & Sequence Models Use Alpha360

# Alpha158 与 Alpha360 — 为什么树模型用 Alpha158、序列模型用 Alpha360

> Session: 2026-11-09 | Author: AI Assistant (DeepSeek-V4-Pro)

---

## 1. Design Philosophy / 设计哲学

| Aspect / 方面 | Alpha158 | Alpha360 |
|------|------|------|
| 特征结构 / Feature Structure | 158 个横截面因子, 无时间维度 / 158 cross-sectional factors, no temporal dimension | 60 天 × 6 字段 = 360 维, 有时间序列结构 / 60 days × 6 fields = 360 dims, temporal structure |
| 特征来源 / Feature Source | 手工设计的领域因子 (K线形态、动量、波动率等) / Hand-crafted domain factors (candlestick patterns, momentum, volatility, etc.) | 原始 OHLCV 价格数据 / Raw OHLCV price data |
| 默认归一化 / Default Normalization | `[]` — 不做归一化 / No normalization | `ProcessInf + ZScoreNorm + Fillna` |
| 默认 process_type | `PTYPE_A` (显式指定 / explicit) | 默认 `PTYPE_A` (隐式 / implicit) |

---

## 2. Alpha360 — Designed for Sequence Models / 为序列模型而生

### 特征结构 / Feature Structure

`Alpha360DL.get_feature_config()` in [loader.py](file:///f:/treaWorkSpace/Qlib/qlib/contrib/data/loader.py#L78-L130):

```python
for i in range(59, 0, -1):
    fields += ["Ref($close, %d)/$close" % i]
    names += ["CLOSE%d" % i]
fields += ["$close/$close"]
names += ["CLOSE0"]
# ... same for OPEN, HIGH, LOW, VWAP, VOLUME — each gets 60 days
```

**360 = 60 days × 6 fields:**

| Field / 字段 | Features / 特征名 | Meaning / 含义 |
|------|------|------|
| `CLOSE59` … `CLOSE0` | 60 | 历史收盘价 / Historical close price |
| `OPEN59` … `OPEN0` | 60 | 历史开盘价 / Historical open price |
| `HIGH59` … `HIGH0` | 60 | 历史最高价 / Historical high price |
| `LOW59` … `LOW0` | 60 | 历史最低价 / Historical low price |
| `VWAP59` … `VWAP0` | 60 | 历史均价 / Historical VWAP |
| `VOLUME59` … `VOLUME0` | 60 | 历史成交量 / Historical volume |

> All normalized by dividing by the latest close price (or volume for volume features).
> 所有特征都除以当日收盘价（或成交量）做归一化, 消除量纲。

### 默认预处理器 / Default Preprocessors

From [handler.py](file:///f:/treaWorkSpace/Qlib/qlib/contrib/data/handler.py#L38-L44):

```python
_DEFAULT_INFER_PROCESSORS = [
    {"class": "ProcessInf"},   # handle infinity values / 处理无穷值
    {"class": "ZScoreNorm"},   # Z-Score normalization / Z-Score 标准化
    {"class": "Fillna"},       # fill NaN / 填充缺失值
]
```

这三个处理器是**神经网络训练的必需品** / These three processors are **essential for neural network training**:
- Neural networks are sensitive to input scale → `ZScoreNorm`
- Missing/infinite values cause NaN gradients → `ProcessInf` + `Fillna`

---

## 3. Alpha158 — Designed for Tree Models / 为树模型而生

### 特征结构 / Feature Structure

`Alpha158DL.get_feature_config()` in [loader.py](file:///f:/treaWorkSpace/Qlib/qlib/contrib/data/loader.py#L133-L300):

| Category / 类别 | Count / 数量 | Examples / 示例 |
|------|------|------|
| **K 线形态因子 / K-bar factors** | 9 | `KMID`, `KLEN`, `KMID2`, `KUP`, `KUP2`, `KLOW`, `KLOW2`, `KSFT`, `KSFT2` |
| **原始价格因子 / Raw price factors** | 4 (default window=[0]) | `OPEN0`, `HIGH0`, `LOW0`, `VWAP0` |
| **滚动统计因子 / Rolling statistics** | ~145 | `ROC5/10/20/30/60`, `MA5/10/20/30/60`, `STD5/10/20/30/60`, `RANK5/...`, `RSV5/...`, `CORR`, `CORD`, `CNTP`, `CNTN`, `CNTD`, `SUMP`, `SUMN`, `SUMD`, `VMA`, `VSTD`, `WVMA`, `VSUMP`, `VSUMN`, `VSUMD`, `IMAX`, `IMIN`, `IMXD`, `RESI`, `RSQR`, `BETA`, `QTLU`, `QTLD`, `MAX`, `MIN` |

### 默认预处理器 / Default Preprocessors

From [handler.py](file:///f:/treaWorkSpace/Qlib/qlib/contrib/data/handler.py#L103-L109):

```python
class Alpha158(DataHandlerLP):
    def __init__(self, ..., infer_processors=[], ...):
```

- **空列表** / **Empty list** — 树模型基于分裂点做决策, 对特征的绝对尺度不敏感。
- Tree models make split-point decisions → insensitive to feature scale → no normalization needed.

### 默认处理模式 / Default process_type

```python
process_type=DataHandlerLP.PTYPE_A  # "append" mode
```

From [handler.py](file:///f:/treaWorkSpace/Qlib/qlib/data/dataset/handler.py#L430):

```
PTYPE_A = "append":
  (data) → [shared] → [infer] → (infer_df)
                               → [learn] → (learn_df)
```

`learn_df` is built on top of `infer_df`, appending learn-only processors. This ensures inference data never sees label-dependent transformations like `CSRankNorm`.

---

## 4. Why This Division? / 为什么这样分工?

### Tree Models → Alpha158 / 树模型 → Alpha158

| Reason / 原因 | Detail / 详情 |
|------|------|
| **擅长表格型横截面特征** / Excel at tabular, cross-sectional features | LightGBM/XGBoost/CatBoost 天然支持特征交互和非线性关系挖掘。158 个手工因子各代表不同的市场含义 (动量、反转、波动、流动性等), 树模型可以自动发现哪些因子组合最有效。 |
| **不擅长建模时序依赖** / Not good at modeling temporal dependencies | 树模型没有循环连接或注意力机制, 无法自动从原始价格序列中提取时间模式。因此 **把时序信息"手工编码"成横截面因子** (如 `ROC60` 编码了 60 天动量, `MA20` 编码了 20 日均线偏离), 让树模型能直接使用这些"浓缩后的时间信息"。 |
| **无需归一化** / No normalization needed | 树模型基于特征值排序找分裂点, `$close=100` 和 `$close=1` 对树模型等价 — 只要相对大小关系不变。所以 `infer_processors=[]` 是正确的。 |

### Sequence Models → Alpha360 / 序列模型 → Alpha360

| Reason / 原因 | Detail / 详情 |
|------|------|
| **擅长从原始序列中自动学习** / Excel at learning from raw sequences | LSTM 的循环门控机制、Transformer 的自注意力机制天然就是为了捕捉时序依赖而设计的。给它们 60 天的原始价格数据, 它们能自己学到: 哪些历史模式预示涨跌、价格与成交量的交互关系如何演化。 |
| **手工因子反而限制表达能力** / Hand-crafted factors limit expressiveness | 如果你把 `MA20`、`ROC60` 等手工因子喂给 LSTM, 这相当于 **剥夺了模型自己学习表示的能力**。序列模型的优势就是端到端的表示学习 (representation learning), 手工特征工程反而成了信息瓶颈。 |
| **需要归一化** / Normalization required | 神经网络对输入尺度敏感, 不做 Z-Score 标准化会导致梯度爆炸或消失。所以 `infer_processors` 默认包含 `ZScoreNorm`。 |

---

## 5. Real Configurations / 真实配置举例

### LightGBM (Tree Model) with Alpha158

From [workflow_config_lightgbm_Alpha158.yaml](file:///f:/treaWorkSpace/Qlib/examples/benchmarks/LightGBM/workflow_config_lightgbm_Alpha158.yaml):

```yaml
task:
    model:
        class: LGBModel           # Tree model / 树模型
    dataset:
        kwargs:
            handler:
                class: Alpha158    # 158 engineered factors / 158 个手工因子
```

### LSTM (Sequence Model) with Alpha360

From [workflow_config_lstm_Alpha360.yaml](file:///f:/treaWorkSpace/Qlib/examples/benchmarks/LSTM/workflow_config_lstm_Alpha360.yaml):

```yaml
task:
    model:
        class: LSTM
        kwargs:
            d_feat: 6             # 6 fields: CLOSE, OPEN, HIGH, LOW, VWAP, VOLUME
    dataset:
        kwargs:
            handler:
                class: Alpha360   # 360 raw time-series features / 360 维原始时序特征
```

### Cross-Validation Evidence / 交叉验证证据

The benchmarks directory also contains "cross" configs (e.g., `workflow_config_lightgbm_Alpha360.yaml`, `workflow_config_lstm_Alpha158.yaml`) for comparison. These serve as **ablation studies** to verify that:

- LightGBM + Alpha360 performs worse than LightGBM + Alpha158 (tree models can't leverage raw sequences)
- LSTM + Alpha158 performs worse than LSTM + Alpha360 (sequence models benefit from raw temporal data)

---

## 6. One-Liner Summary / 一句话总结

> **树模型是"特征处理器"** — 需要把时间信息手工编码成横截面因子 (Alpha158);
> **序列模型是"时间处理器"** — 给它原始时间序列 (Alpha360) 让它自己学。
> 各取所长, 互不僭越。

> **Tree models are "feature processors"** — they need time information encoded as cross-sectional factors (Alpha158);
> **Sequence models are "time processors"** — give them raw time series (Alpha360) and let them learn.
> Each plays to its own strength; neither oversteps the other.