# Gemini：E1只读监控交接

先读取同目录 `launch_receipt.json`，以其中的节点、GPU UUID、PID、启动时间和路径为准。
该收据不存在或标明pending时，不得推断首发任务已经完成5次更新。

正式条件仅Full/No-Scores，两折共四次训练，固定165 epochs；每折Full成功退出后再运行No-Scores。
队列只训练，不自动执行OOF、评价、Clinical-only、No-Patient或E2。

只读检查：
1. 用完整PID身份、启动时间、命令行及GPU UUID核对进程；使用 `nvidia-smi` 检查对应设备。
2. 日志每epoch前5步、每100步及epoch结束输出；optimizer_step为实际完成更新。
3. 对照每项任务资产目录下start.json与startup_5_updates.json；后者只证明首次5次更新。
4. recovery.pt每10个epoch及最终epoch写入，前10个epoch尚无恢复点是预期行为。
5. 当前任务成功后，队列应启动同折No-Scores；检查其start.json初始化SHA与同折Full一致。
6. `.exit` 文件存在才代表该进程退出；不存在时不能判定成功。状态0是成功，非0应立即报告。
7. 出现OOM、非有限loss、版本/哈希错误、进程退出或已完成启动后的日志长时间停滞，
   报告节点、任务、PID、日志和错误原文。不要修改配置、调参、自动重启或停止其他进程。
8. 训练结束后报告四个任务及最终checkpoint状态，等待作者安排后续分析。

邮件：CLI使用真实 `@email_on_error()`；正式队列未启用DRY_RUN。dry-run流程已验证，
实际SMTP投递未独立验证；系统强杀、主机掉线等不能依靠该异常装饰器报警。

只读命令（路径固定，均在本仓库）：

```sh
cd /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP
cat reports/e1_stage2_launch_20261017/launch_receipt.json
tail -n 12 reports/e1_stage2_launch_20261017/logs/3003_fold2_Full.log
tail -n 12 reports/e1_stage2_launch_20261017/logs/3002_fold1_Full.log
cat reports/e1_stage2_launch_20261017/queues/3003_fold2/*.pid
cat reports/e1_stage2_launch_20261017/queues/3002_fold1/*.pid
nvidia-smi --query-compute-apps=gpu_uuid,pid,used_memory --format=csv
ssh -F /home/data/linshuijin/.ssh/config 3002 'nvidia-smi --query-compute-apps=gpu_uuid,pid,used_memory --format=csv'
```

3003资产根：`/mnt/datas230/users/linshuijin/DIRECTPP_E1/stage01_20261017/`
3002资产根：`/home/linshuijin/DIRECTPP_E1/stage01_20261017/`
任务子目录：`formal/fold2_Full`、`formal/fold2_No-Scores`（3003），
`formal/fold1_Full`、`formal/fold1_No-Scores`（3002）。
