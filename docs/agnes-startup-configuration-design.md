# Agnes启动配置优化设计

> 历史资料说明（2026-10-13补注）：下文设计、数量、失败与未验收结论属于原记录日期，不代表当前版本；保留原始证据，不将当时未执行的测试改写为通过。 当前技术栈、视频播放证据和各数据口径统一见[答辩当前状态说明](defense-current-state.md)；本次仅修订文档，没有重新验收或运行Spark。

2026-10-05。仅修改安全启动工具，适配层与调用逻辑保持不变。

启动优先读取AGNES_MODEL_ID和AGNES_API_KEY；缺失、空字符串或纯空白按未配置处理。缺模型时使用原input，缺Key时使用原getpass隐藏输入。两项独立处理，避免重复输入已有项。模型ID映射到现有适配层AGNES_MODEL变量。AGNES_MODEL旧变量不替代用户指定的新入口变量。

配置只在进程环境存在，不写入数据库、文件、日志或凭据库；不回显Key。固定Base URL及AISettings验证不变。已有诊断启动工具通过runpy复用同一入口，保持兼容。等待端口释放及原后端启动方式不变。

在同一Ubuntu终端export AGNES_MODEL_ID=agnes-3.0-flash后，可以用read -r -s安全读取Key，再export AGNES_API_KEY；不将真实Key写入命令历史。关闭终端后的持久保存不属于本轮范围。
