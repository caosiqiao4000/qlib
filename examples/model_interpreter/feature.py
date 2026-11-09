#  Copyright (c) Microsoft Corporation.
#  Licensed under the MIT License.


import copy

import qlib
from qlib.constant import REG_CN

from qlib.utils import init_instance_by_config
from qlib.tests.data import GetData
from qlib.tests.config import CSI300_GBDT_TASK

if __name__ == "__main__":
    # use default data
    provider_uri = "~/.qlib/qlib_data/cn_data"  # target_dir
    GetData().qlib_data(target_dir=provider_uri, region=REG_CN, exists_skip=True)

    qlib.init(provider_uri=provider_uri, region=REG_CN)

    ###################################
    # train model
    ###################################
    # model initialization
    model = init_instance_by_config(CSI300_GBDT_TASK["model"])
    # handler 的 fit_start_time/fit_end_time 是占位符，只有 qrun 模板渲染器才会替换。
    # 这里直接实例化 dataset，需要手动替换为真实的 train 区间日期。
    dataset_config = copy.deepcopy(CSI300_GBDT_TASK["dataset"])
    train_segment = dataset_config["kwargs"]["segments"]["train"]
    handler_kwargs = dataset_config["kwargs"]["handler"]["kwargs"]
    handler_kwargs["fit_start_time"] = train_segment[0]
    handler_kwargs["fit_end_time"] = train_segment[1]
    dataset = init_instance_by_config(dataset_config)
    model.fit(dataset)

    # get model feature importance
    feature_importance = model.get_feature_importance()
    print("feature importance:")
    print(feature_importance)