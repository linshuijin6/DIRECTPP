# 传输状态与恢复

主节点：vscode-3003。控制目录在共享NFS，数据落盘目录为 `/mnt/datas230/users/linshuijin/DIRECTPP_assets/20261016T164446+0800`。
前台归档与后台复制分开验收。只在资产全量校验通过后发布复制资产链接；local_link表示直接依赖3003可读的原始数据/模型，未宣称已复制。

## 状态

```powershell
ssh -T vscode-3003 'python3 /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP_transfers/20261016T164446+0800/transfer_worker.py --control /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP_transfers/20261016T164446+0800 status'
ssh -T vscode-3003 'tail -n 30 /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP_transfers/20261016T164446+0800/logs/receiver.log'
ssh -T vscode-3002 'tail -n 30 /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP_transfers/20261016T164446+0800/logs/producer-vscode-3002.log'
```

`status.json`每15秒更新；各资产状态在控制目录state/，源快照在relay/，完成校验回执在receipts/。
linked=源在3003可读，目录仅完成清单/stat/权限检查；verified=复制文件集及每个文件SHA-256均核实。
pending/hashing_source/exporting/receiving均未完成；failed须读错误，队列停止，不自动跳过。

## 安全停止及重试

先在各自节点停止worker，再重置失败标记；不删除已验证资产、回执或源文件。

```powershell
ssh -T vscode-3003 'python3 /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP_transfers/20261016T164446+0800/manage_transfer.py stop monitor'
ssh -T vscode-3003 'python3 /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP_transfers/20261016T164446+0800/manage_transfer.py stop receiver'
ssh -T vscode-3002 'python3 /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP_transfers/20261016T164446+0800/manage_transfer.py stop producer-vscode-3002'
ssh -T vscode-3014 'python3 /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP_transfers/20261016T164446+0800/manage_transfer.py stop producer-vscode-3014'
ssh -T vscode-3003 'python3 /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP_transfers/20261016T164446+0800/transfer_worker.py --control /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP_transfers/20261016T164446+0800 retry'
ssh -T vscode-3002 'python3 /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP_transfers/20261016T164446+0800/manage_transfer.py start producer-vscode-3002'
ssh -T vscode-3014 'python3 /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP_transfers/20261016T164446+0800/manage_transfer.py start producer-vscode-3014'
ssh -T vscode-3003 'python3 /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP_transfers/20261016T164446+0800/manage_transfer.py start receiver'
ssh -T vscode-3003 'python3 /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP_transfers/20261016T164446+0800/manage_transfer.py start monitor'
```

若错误为源发生变化，重试会继续拒绝不一致的源；应单独登记新版本，不可直接更改已捕获源快照来假装通过。
复制为独立session进程，关闭当前聊天/SSH不会结束传输；机器重启后可使用以上恢复流程。
默认单路50MiB/s、全局中转不超过32GiB。仅清理本批次已验证的中转payload，不删除原始研究数据。

## 完成校验

所有copy资产均为verified、没有failed/pending，且receipts逐文件回执齐全，才可称后台复制完成。
`receiver_finished.json`只表示receiver已退出，还需检查其中是否存在failed。
论文对应缺口与复制完成是两个条件：复制结束不等于实验复现或论文全部对应。
