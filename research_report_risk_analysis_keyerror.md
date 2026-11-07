# Research Report: `KeyError: 'annualized_return'` in `risk_analysis_graph`

## Executive Summary
The error in `workflow_by_code.ipynb` Cell In[10] is caused by a pandas 3.x breaking change, not by the notebook or your data. In pandas 3.x, `GroupBy.get_group()` requires a tuple key when `groupby()` was given a list of columns. Qlib's `_get_monthly_analysis_with_feature` in `qlib/contrib/report/analysis_position/risk_analysis.py` groups by `["level_1"]` but looks up the group with a plain string, so every lookup — including `'annualized_return'` — raises a spurious `KeyError`. A one-word fix (group by the string `"level_1"` instead of the list) was verified to make `risk_analysis_graph` produce all 5 figures from your actual recorder artifacts.

## Root Cause (verified by reproduction)
Reproduced against your real data (`mlruns/745563634060855266/.../report_normal_1day.pkl`, 871 rows) in the `qlib` conda env (pandas 3.1.0, installed pyqlib at `D:\ProgramData\miniconda3\envs\qlib`). Findings:

1. The monthly risk analysis is built correctly — the MultiIndex second level does contain `annualized_return` (plus `mean`, `std`, `information_ratio`, `max_drawdown`), and `groupby(["level_1"]).size()` lists the group.
2. Yet `GroupBy.get_group("annualized_return")` raises `KeyError`. Minimal repro:

```python
r = pd.DataFrame({"level_1": ["mean", "annualized_return", "mean"], "risk": [1, 2, 3]})
r.groupby(["level_1"]).get_group("annualized_return")        # KeyError in pandas 3.1
r.groupby(["level_1"]).get_group(("annualized_return",))     # works
r.groupby("level_1").get_group("annualized_return")          # works
```

This is a pandas 3.x API change: list-column group keys are normalized to tuples in `get_group`.

## Fix
In `qlib/contrib/report/analysis_position/risk_analysis.py` (line ~102), change:

```python
_monthly_df_gp = monthly_df.reset_index().groupby(["level_1"], group_keys=False)
```

to:

```python
_monthly_df_gp = monthly_df.reset_index().groupby("level_1", group_keys=False)
```

The repo copy (`f:\treaWorkSpace\Qlib\qlib\contrib\report\analysis_position\risk_analysis.py`) has already been patched with an explanatory comment.

The error comes from the **installed** package (`D:\ProgramData\miniconda3\envs\qlib\Lib\site-packages\qlib\...`), which the IDE sandbox cannot write to. Run this once in your own PowerShell to patch it:

```powershell
$f = 'D:\ProgramData\miniconda3\envs\qlib\Lib\site-packages\qlib\contrib\report\analysis_position\risk_analysis.py'
(Get-Content $f -Raw).Replace('monthly_df.reset_index().groupby(["level_1"], group_keys=False)', 'monthly_df.reset_index().groupby("level_1", group_keys=False)') | Set-Content $f -Encoding utf8
```

(If PowerShell writes a BOM that the notebook dislikes, delete the first three bytes or re-save the file as UTF-8 without BOM in an editor.)

## Verification
With the fix applied in memory, `risk_analysis_graph(analysis_df, report_normal_df, show_notebook=False)` was run against your actual `port_analysis_1day.pkl` and `report_normal_1day.pkl` artifacts: **5 figures generated** (1 risk-analysis bar subplot figure + 4 monthly scatter figures), no errors.

## Limitations
- Alternative: downgrading to pandas < 3 (e.g., `pip install "pandas<3"`) also avoids the issue, but your env's other packages may expect pandas 3.
- Other pandas-3 incompatibilities may surface elsewhere in qlib's contrib/report code; the same tuple-key rule applies.

## References
1. Qlib source patched: `qlib/contrib/report/analysis_position/risk_analysis.py` (`_get_monthly_analysis_with_feature`)
2. Reproduction data: `mlruns/745563634060855266/3169c92fad4447a8b0b7fafef63d47d1/artifacts/portfolio_analysis/*.pkl`
