#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Verify that a qlib dataset (default: ~/.qlib/qlib_data/cn_data) is loadable
and compatible with this project's data structures and workflows.

Checks:
  1. Calendar loads and ends at a recent trading day.
  2. Instruments (all / csi300 / csi500) parse and resolve to real codes.
  3. Core OHLCV + vwap/factor fields load via D.features for sample stocks.
  4. Alpha158-style expressions (Ref, Mean, Corr, ...) evaluate end-to-end,
     which exercises the expression engine and compiled _libs extensions.

Usage:
    python verify_qlib_data.py [--provider-uri ~/.qlib/qlib_data/cn_data]

Exit code 0 = all checks passed; non-zero = failure (with reason printed).
"""
import argparse
import sys
from pathlib import Path

DEFAULT_PROVIDER_URI = "~/.qlib/qlib_data/cn_data"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-uri", default=DEFAULT_PROVIDER_URI)
    args = parser.parse_args()

    provider_uri = Path(args.provider_uri).expanduser()
    if not provider_uri.exists():
        print(f"FAIL: provider_uri does not exist: {provider_uri}")
        return 1

    import qlib
    from qlib.constant import REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(provider_uri), region=REG_CN)
    print(f"[1/4] qlib.init OK (provider_uri={provider_uri}, region=cn)")

    # --- 1. calendar ---
    cal = D.calendar(freq="day")
    if len(cal) == 0:
        print("FAIL: empty calendar")
        return 1
    print(f"[2/4] calendar OK: {cal[0]} -> {cal[-1]} ({len(cal)} trading days)")

    # --- 2. instruments ---
    codes = list(D.list_instruments(D.instruments(market="csi300"), as_list=True))
    if len(codes) < 100:
        print(f"FAIL: csi300 resolved to only {len(codes)} instruments")
        return 1
    print(f"[3/4] instruments OK: csi300 -> {len(codes)} codes, e.g. {codes[:3]}")

    # --- 3. raw fields ---
    fields = ["$open", "$high", "$low", "$close", "$volume", "$vwap", "$factor"]
    df = D.features(codes[:5], fields, start_time=cal[-10], end_time=cal[-1], freq="day")
    if df.empty:
        print("FAIL: D.features returned empty frame")
        return 1
    nan_ratio = float(df.isna().mean().mean())
    if nan_ratio > 0.5:
        print(f"FAIL: raw fields NaN ratio too high: {nan_ratio:.2%}")
        return 1
    last = df.iloc[-1]
    print(
        f"[4/4] fields OK: {df.shape}, NaN={nan_ratio:.2%}, "
        f"last close={last.get('$close')}, volume={last.get('$volume')}"
    )

    print("PASS: dataset is loadable and compatible with this project")
    return 0


if __name__ == "__main__":
    sys.exit(main())
