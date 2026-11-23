# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
The motivation of this demo
- To show the data modules of Qlib is Serializable, users can dump processed data to disk
    to avoid duplicated data preprocessing
"""

# -----------------------------------------------------------------------------
# Risk report printed by the workflow
# -----------------------------------------------------------------------------
# Running the LightGBM workflow below prints a risk report (produced by
# qlib.contrib.evaluate.risk_analysis). Its "risk" column contains:
#
#   mean                Average daily return of the strategy.
#   std                 Standard deviation of daily returns (daily volatility),
#                       computed with ddof=1.
#   annualized_return   Annualized return = mean * N. For daily frequency Qlib
#                       uses N = 238 by convention.
#   information_ratio   Information ratio = mean / std * sqrt(N), i.e. the
#                       return earned per unit of risk.
#   max_drawdown        Max drawdown = (cumsum(r) - cummax(cumsum(r))).min(),
#                       i.e. the worst peak-to-trough drop of the cumulative
#                       sum of returns.
#
# 中文说明（工作流打印的风险指标）：
#   mean                策略的平均日收益率。
#   std                 日收益率的标准差（日波动率），使用 ddof=1 计算。
#   annualized_return   年化收益率 = mean * N；日频下 Qlib 约定 N = 238。
#   information_ratio   信息比率 = mean / std * sqrt(N)，即每单位风险带来的收益。
#   max_drawdown        最大回撤 = (cumsum(r) - cumsum(r) 累计最大值).min()，
#                       即累计收益曲线从峰值到谷底的最大跌幅。
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Trade-indicator analysis printed by the workflow
# -----------------------------------------------------------------------------
# The workflow also prints trade-indicator statistics (produced by
# qlib.contrib.evaluate.indicator_analysis), e.g.
# "The following are analysis results of indicators(1day)":
#
#   ffr   Full fill rate = fulfilled amount / target amount.
#         1.0 means the order was fully filled, 0.0 means it was not filled.
#   pa    Price advantage: how much the actual trade price differs from the
#         baseline price. Positive means a favorable execution price, 0.0 means
#         no price advantage (executed exactly at the baseline).
#   pos   Positive rate (win rate) = the fraction of orders whose pa > 0.
#
# 中文说明（工作流打印的交易指标统计）：
#   ffr   成交率/完成率 = 实际成交量 / 目标成交量。
#         1.0 表示订单全部成交，0.0 表示未成交。
#   pa    价格优势：实际成交价相对基准价的偏离程度。
#         为正值表示成交价有利，0.0 表示无价格优势（恰好以基准价成交）。
#   pos   正收益占比（胜率）= pa > 0 的订单占比。
# -----------------------------------------------------------------------------

import os
from copy import deepcopy
from pathlib import Path
import pickle
from pprint import pprint
from ruamel.yaml import YAML
import subprocess
import sys

# For general purpose, we use relative path
DIRNAME = Path(__file__).absolute().resolve().parent

# MLflow 3.12+ disables the local file-store backend by default.
# The workflows below use the default file-store tracking URI, so opt back in.
os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")

# Use local Qlib source code instead of the installed pyqlib package.
# `sys.path[0]` is this script's directory, so the repository root has to be added
# explicitly; PYTHONPATH is exported as well so that the child processes keep using
# the same source code. This makes the demo runnable with any interpreter from any
# working directory, e.g. `python examples/data_demo/data_cache_demo.py`.
ROOT = DIRNAME.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ["PYTHONPATH"] = os.pathsep.join([p for p in [str(ROOT), os.environ.get("PYTHONPATH")] if p])

from qlib.log import TimeInspector

from qlib import init
from qlib.data.dataset.handler import DataHandlerLP
from qlib.utils import init_instance_by_config


def run_workflow(config_path):
    """Run a workflow config with the current interpreter.

    Calling the ``qrun`` entry point would depend on whatever environment happens
    to be first on ``PATH``; that executable may belong to another environment
    with a different, installed pyqlib, so the child process would silently run
    different code than this script.
    """
    subprocess.run([sys.executable, "-m", "qlib.cli.run", str(config_path)], env=os.environ, shell=False)


if __name__ == "__main__":
    init()

    config_path = DIRNAME.parent / "benchmarks/LightGBM/workflow_config_lightgbm_Alpha158.yaml"

    # 1) show original time
    with TimeInspector.logt("The original time without handler cache:"):
        run_workflow(config_path)

    # 2) dump handler
    yaml = YAML(typ="safe", pure=True)
    task_config = yaml.load(config_path.open())
    hd_conf = task_config["task"]["dataset"]["kwargs"]["handler"]
    pprint(hd_conf)
    hd: DataHandlerLP = init_instance_by_config(hd_conf)
    hd_path = DIRNAME / "handler.pkl"
    hd.to_pickle(hd_path, dump_all=True)

    # 3) create new task with handler cache
    new_task_config = deepcopy(task_config)
    new_task_config["task"]["dataset"]["kwargs"]["handler"] = f"file://{hd_path}"
    new_task_config["sys"] = {"path": [str(config_path.parent.resolve())]}
    new_task_path = DIRNAME / "new_task.yaml"
    print("The location of the new task", new_task_path)

    # save new task
    # NOTE: `yaml` here is a ruamel.yaml `YAML` object, whose dumping method is
    # `dump` (`safe_dump`/`sort_keys` belong to the PyYAML API).
    yaml.indent(mapping=4, sequence=4, offset=2)
    with new_task_path.open("w") as f:
        yaml.dump(new_task_config, f)

    # 4) train model with new task
    with TimeInspector.logt("The time for task with handler cache:"):
        run_workflow(new_task_path)