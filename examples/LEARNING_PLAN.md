# Qlib examples 8 周学习计划

> 节奏假设：每周 5~6 小时（工作日 30~40 分钟 + 周末一次整块时间）。
> 全程纪律：用 `D:/ProgramData/miniconda3/envs/qlib` 的 python、从非仓库目录运行；跑新配置前确认数据日历覆盖配置时间段。

## 第 1 周 · 跑通主干
- [ ] 读 [workflow_by_code.py](workflow_by_code.py)，与已注释的 [workflow_by_code.ipynb](workflow_by_code.ipynb) 逐段对照
- [ ] 用 `qrun` 跑 [LightGBM/workflow_config_lightgbm_Alpha158.yaml](benchmarks/LightGBM/workflow_config_lightgbm_Alpha158.yaml)，理解 task 字典 ↔ YAML 同构
- [ ] 读 [benchmarks/README.md](benchmarks/README.md) 结果表，建立 IC 基准感（~0.04-0.05 正常）
- [ ] **验收**：能默写 handler→dataset→model→recorder→backtest 链路

## 第 2 周 · 特征体系
- [ ] 换 [workflow_config_lightgbm_Alpha360.yaml](benchmarks/LightGBM/workflow_config_lightgbm_Alpha360.yaml) 跑一遍，对比输入形状
- [ ] 读 expression engine 文档，手写 2~3 个自定义因子表达式
- [ ] **验收**：能解释树模型用 Alpha158、序列模型用 Alpha360 的原因

## 第 3 周 · 模型巡礼（CPU）
- [ ] 跑 [Linear](benchmarks/Linear/workflow_config_linear_Alpha158.yaml)
- [ ] 跑 [CatBoost](benchmarks/CatBoost/workflow_config_catboost_Alpha158.yaml)
- [ ] 跑 [XGBoost](benchmarks/XGBoost/workflow_config_xgboost_Alpha158.yaml)
- [ ] 用 [model_interpreter/feature.py](model_interpreter/feature.py) 分析 LightGBM 因子依赖
- [ ] **验收**：整理出自己的 IC/回测对比表

## 第 4 周 · 序列模型（只跑一个）
- [ ] 读 GRU/LSTM/Transformer 三个配置的差异
- [ ] 跑 [GRU + Alpha360](benchmarks/GRU/workflow_config_gru_Alpha360.yaml)；无 GPU 则加载仓库自带 `model_gru_csi300.pkl` 看结构
- [ ] TFT/TRA/HIST 只读 README
- [ ] **验收**：能说出序列模型 DataLoader 与 DatasetH 的差别

## 第 5 周 · 数据层深入
- [ ] 精读 [tutorial/detailed_workflow.ipynb](tutorial/detailed_workflow.ipynb)
- [ ] 跑 [data_cache_demo.py](data_demo/data_cache_demo.py) 与 [data_mem_resuse_demo.py](data_demo/data_mem_resuse_demo.py)，理解 expression/dataset 缓存
- [ ] **验收**：写一个精简版自定义 handler（~20 因子）跑通训练

## 第 6 周 · 滚动训练
- [ ] 跑 [benchmarks_dynamic/baseline/rolling_benchmark.py](benchmarks_dynamic/baseline/rolling_benchmark.py)
- [ ] 读 [model_rolling/task_manager_rolling.py](model_rolling/task_manager_rolling.py)
- [ ] DDG-DA 只读 [README](benchmarks_dynamic/DDG-DA/README.md)
- [ ] **验收**：能画出 rolling 的 train/valid/test 窗口滑动图

## 第 7 周 · 组合构建
- [ ] 跑 [portfolio/prepare_riskdata.py](portfolio/prepare_riskdata.py) 生成风险数据
- [ ] 跑 [config_enhanced_indexing.yaml](portfolio/config_enhanced_indexing.yaml)
- [ ] **验收**：能解释 enhanced indexing 目标函数在优化什么

## 第 8 周 · 收尾 + 选题
- [ ] 复盘前 7 周的 recorder 结果，整理笔记
- [ ] 从 highfreq / nested_decision_execution / rl_order_execution / online_srv 选一个方向深入（不相关则跳过）
