# Qlib 项目长期备忘

## 环境
- **qlib 正式运行环境：`D:/ProgramData/miniconda3/envs/qlib/python.exe`（conda env，pyqlib 0.9.7 + 编译好的 _libs 扩展，能跑 qlib 工作流）。所有 qlib 脚本都用它跑。**
- 注意：仓库目录下 import qlib 会遮蔽已安装包（缺 _libs 报错），跑 qlib 须先 cd 出仓库目录（如 /tmp）。
- F 盘源码仓库缺 MSVC，`qlib/data/_libs` 无法本地编译，不要试图在系统默认 python 上跑 qlib。
- 系统默认 `python`（WorkBuddy 3.13.12）已恢复干净，不装任何 qlib 相关包。
- F 盘源码仓库缺 MSVC，`qlib/data/_libs` 无法本地编译；仓库目录下 import qlib 会遮蔽已安装包，跑 qlib 须 cd 出仓库目录用 miniconda python。

## 数据
- A股日线数据位于 `~/.qlib/qlib_data/cn_data`（chenditc/investment_data release），qlib 默认 provider_uri 即此路径。
- 数据更新 automation id: ebf87f57-504d-445b-95dc-03ef9921b44f（**已于 2026-10-25 由用户在 WorkBuddy app 手动禁用**），历史信息：每小时触发、每日去重，走 ghfast.top 镜像下载。
- 2026-10-25：Trae 侧定时任务 Schedule id `cd13e7f2`（cron `0 10-23 * * *`，Asia/Shanghai）为**当前唯一在跑的每日数据更新任务**，prompt 为 PowerShell 语法（curl.exe / tar / Remove-Item），去重标记 ~/.qlib/.last_update_date，更新后跑 `scripts/verify_qlib_data.py` 验证。
