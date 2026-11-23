# Understanding Expression / Dataset Cache in Qlib

# 理解 Qlib 的 expression / dataset 缓存

This document explains how Qlib caches processed data, based on the two demos
`data_cache_demo.py` and `data_mem_resuse_demo.py`.

本文档基于 `data_cache_demo.py` 与 `data_mem_resuse_demo.py` 两个示例，讲解 Qlib 是如何缓存处理好的数据的。

---

## 1. Overview / 概述

There are three layers of reuse, from high to low:

复用有三个层级，从高到低依次为：

1. **Handler reuse (handler 复用)** — reuse the whole processed `DataHandlerLP` object, either on disk or in memory.
   复用整个处理好的 `DataHandlerLP` 对象，可以是磁盘或内存。

2. **Dataset cache (dataset 缓存)** — cache the assembled DataFrame for a given set of instruments + fields.
   缓存一组 instruments + fields 组装好的 DataFrame。

3. **Expression cache (expression 缓存)** — cache the result of a single expression for a single instrument.
   缓存单个表达式在单只股票上的计算结果。

```
Handler reuse  →  Dataset cache  →  Expression cache
(handler 复用)    (dataset 缓存)    (expression 缓存)
```

---

## 2. The two demo files / 两个示例文件

| | `data_cache_demo.py` | `data_mem_resuse_demo.py` |
|---|---|---|
| Reuse medium / 复用介质 | Disk (pickle file) / 磁盘(pickle 文件) | Memory (handler object) / 内存(handler 对象) |
| Key action / 核心动作 | `hd.to_pickle(hd_path, dump_all=True)` → `handler = "file://...handler.pkl"` | `hd = init_instance_by_config(hd_conf)` → `handler = hd` |
| Across processes / 跨进程 | Yes / 可以 | No / 不可以 |
| Benefit / 收益 | Skips data loading + feature computation / 跳过数据加载与特征计算 | Skips repeated `setup_data()` / loader / 跳过重复的数据加载 |

### 2.1 `data_cache_demo.py`

- Step 1 runs the workflow without cache to get a baseline time.
  第一步不带缓存跑一遍 workflow 作为耗时基线。
- Step 2 instantiates the same `DataHandlerLP` and serializes it to `handler.pkl` with `dump_all=True`.
  第二步用相同的 handler 配置实例化 `DataHandlerLP`，并以 `dump_all=True` 序列化到 `handler.pkl`。
- Step 3/4 builds a new task whose `handler` points to `file://...handler.pkl`, then runs the workflow again.
  第三/四步构造新 task，把 `handler` 指向 `file://...handler.pkl`，再次运行 workflow。

### 2.2 `data_mem_resuse_demo.py`

- Step 1 calls `task_train` `repeat` times, reloading data each time.
  第一步循环 `repeat` 次调用 `task_train`，每次都重新加载数据。
- Step 2 instantiates the handler once into memory.
  第二步把 handler 实例化一次，放进内存。
- Step 3 reuses the in-memory handler across multiple `task_train` calls.
  第三步在多次 `task_train` 调用中复用内存里的 handler。
- Step 4 shows that `segments.train` can be changed while reusing the same handler (via `config`).
  第四步演示即使修改 `segments.train` 时间区间，仍可复用同一个 handler（通过 `config` 覆盖）。

---

## 3. Two-level cache / 两级缓存

Definitions live in `qlib/data/cache.py`.
相关定义位于 `qlib/data/cache.py`。

### 3.1 Expression cache / expression 缓存

`ExpressionCache` → `DiskExpressionCache`

- Granularity / 粒度: one expression × one instrument (e.g. `$close/Ref($close,1)-1`).
  单个表达式 × 单只股票。
- Cache key: `hash_args(instrument, field, freq)`.
- Location / 位置: `<provider_uri>/features_cache/<instrument>/<hash>` (binary data + `.meta`).
- Note / 注意: only non-raw expressions are cached; raw features such as `$close` bypass the cache.
  只有非原始表达式才会被缓存；`$close` 这类 raw feature 会直接走 provider，不缓存。

### 3.2 Dataset cache / dataset 缓存

`DatasetCache` → `DiskDatasetCache`

- Granularity / 粒度: the assembled DataFrame for a set of instruments + fields.
  一组 instruments + fields 组装好的完整 DataFrame。
- Cache key: `hash_args(normalized instruments, fields, freq, disk_cache, inst_processors)`.
- Location / 位置: `<provider_uri>/dataset_cache/<hash>` (stored as HDF5, `HDF_KEY = "df"`).
- `disk_cache` semantics / 参数语义:
  - `0` — skip cache / 跳过缓存
  - `1` — use if present, generate if missing (default) / 命中就用，未命中就生成（默认）
  - `2` — force rebuild / 强制重建

---

## 4. Data flow / 数据流

```
DataHandlerLP.setup_data()              # qlib/data/dataset/handler.py
  └─ QlibDataLoader.load()               # qlib/data/dataset/loader.py
       └─ D.features(instruments, exprs) # loader.load_group_df
            └─ DatasetCache.dataset()    # dataset-level cache
                 └─ provider.dataset()   # compute expressions one by one
                      └─ ExpressionCache.expression()  # expression-level cache
```

1. First check whether the dataset cache already has the finished product for
   these `(instruments, fields)`.
   先看 dataset 缓存里是否已有这批 `(instruments, fields)` 的成品。
2. If not, compute each expression; each expression is accelerated by the
   expression cache.
   若没有，则逐条计算表达式；每条表达式又会由 expression 缓存加速。

---

## 5. `to_pickle(dump_all=True)` and `Serializable`

## `to_pickle(dump_all=True)` 与 `Serializable`

The keep/drop rule in `qlib/utils/serial.py` (`Serializable.__getstate__`):
保留/丢弃规则见 `qlib/utils/serial.py`：

- In the config attribute list → always dropped / 在 config 列表中 → 丢弃
- In the include list → kept / 在 include 中 → 保留
- In the exclude list → dropped / 在 exclude 中 → 丢弃
- Name not starting with `_` → kept / 不以 `_` 开头 → 保留
- Name starting with `_` → kept only if `dump_all=True` / 以 `_` 开头 → 仅当 `dump_all=True` 时保留

`DataHandlerLP` stores processed data in `self._data` (leading underscore), so
`dump_all=True` is required to persist the data; otherwise only the config is
saved and the data must be recomputed on reload.

`DataHandlerLP` 把处理好的数据放在 `self._data`（下划线开头），因此必须 `dump_all=True`
才能把数据一起存下来；否则只会保存配置，重新加载时还需重新计算。

---

## 6. Cache directory config / 缓存目录配置

In `qlib/config.py`:

```python
"dataset_cache_dir_name": "dataset_cache",
"features_cache_dir_name": "features_cache",
```

Both live under `provider_uri`, e.g.:
两者都挂在 `provider_uri` 下，例如：

```
~/.qlib/qlib_data/cn_data/features_cache/...
~/.qlib/qlib_data/cn_data/dataset_cache/...
```

---

## 7. Summary / 总结

- `data_cache_demo.py` and `data_mem_resuse_demo.py` demonstrate the top-level
  **handler reuse** (disk pickle vs in-memory object).
  两个示例演示的是最上层的 **handler 复用**（磁盘 pickle vs 内存对象）。
- Under the hood, `D.features` provides two more levels of acceleration:
  **dataset cache** and **expression cache**.
  而其内部依赖的 `D.features` 还自带 **dataset 缓存** 与 **expression 缓存** 两级加速。

---

## 8. Appendix: workflow output metrics / 附录：工作流输出指标

The demos run the LightGBM workflow, which prints two reports: a **risk report**
and a **trade-indicator report**.
这些示例会运行 LightGBM 工作流，打印两类报告：**风险报告** 与 **交易指标报告**。

### 8.1 Risk analysis / 风险分析

Source: `qlib/contrib/evaluate.py` (`risk_analysis`).
来源：`qlib/contrib/evaluate.py`（`risk_analysis`）。

```
                       risk
mean               0.000477
std                0.012295
annualized_return  0.113561
information_ratio  0.598699
max_drawdown      -0.370479
```

| Metric / 指标 | Meaning / 含义 | Formula / 公式 |
|---|---|---|
| `mean` | Average daily return / 平均日收益率 | `r.mean()` |
| `std` | Daily volatility / 日波动率 | `r.std(ddof=1)` |
| `annualized_return` | Annualized return / 年化收益率 | `mean * N`（daily: `N = 238`） |
| `information_ratio` | Return per unit of risk / 信息比率 | `mean / std * sqrt(N)` |
| `max_drawdown` | Max peak-to-trough drop / 最大回撤 | `(r.cumsum() - r.cumsum().cummax()).min()` |

> Note: Qlib uses `N = 238` for daily frequency (not the common 252).
> 注意：日频下 Qlib 约定 `N = 238`（而非常见的 252）。

### 8.2 Trade indicators / 交易指标

Source: `qlib/contrib/evaluate.py` (`indicator_analysis`) and
`qlib/backtest/report.py`.
来源：`qlib/contrib/evaluate.py`（`indicator_analysis`）与 `qlib/backtest/report.py`。

```
The following are analysis results of indicators(1day).
     value
ffr    1.0
pa     0.0
```

| Metric / 指标 | Meaning / 含义 | Definition / 定义 |
|---|---|---|
| `ffr` | Full fill rate / 成交率（完成率） | `fulfilled amount / target amount`；`1.0` = fully filled（全部成交），`0.0` = not filled（未成交） |
| `pa` | Price advantage / 价格优势 | `sign * (trade_price / base_price - 1)`，`sign = 1 - trade_dir * 2`；positive = favorable execution price（正值表示成交价有利），`0.0` = no advantage（无优势） |
| `pos` | Win rate / 胜率（正收益占比） | fraction of orders with `pa > 0`（`pa > 0` 的订单占比） |