# 已核实资产清单

最终更新时间UTC：2026-11-03T01:45:08.411553+00:00。inventory_initial.csv保留首次盘点；inventory.csv为完成状态，共108行。checkpoint列记录路径/身份入口，checkpoint_sha256列区分实测/收据绑定与未重新哈希的分类权重；epoch对分类为内部验证选中的best epoch，training_endpoint=200，不能将其误读成按test选权重。

已核实：W1 Full165、Clinical U-Net165、Swin200、TabularMLP165、TracerOnly165已有完整两折OOF；其原始汇总CSV与completion digest相符。Single四份165 checkpoint本次补齐2963幅OOF。FDG在此前用户要求保存165后结束训练，收据见code/single_endpoint_policy.json，故无需也没有恢复200轮训练。AV45训练完成200轮，仍按预定165主终点评价。

临床18和影像63项训练metadata均complete、200epochs、test一次，81份best_model.pth在远程存在，逐人test输出已核验/复用；没有重新训练分类器。E1评分移除全量2961幅推理先前已完成，本次补统计；与W1 Full权重分离。R3-11 masked8883行（3模型×2961）原样复用。

本地/NFS与远程原始资产均保留；6实例当前状态快照在remote/instanceN_probe.txt及assets_v2.json，实例1/2是无GPU模式，3–6可用GPU仅执行本次推理。未改变实例运行模式、训练状态或他人进程。
