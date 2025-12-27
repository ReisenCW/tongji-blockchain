# 技术架构设计
## 整体技术架构
- 项目采用前后端分离的架构设计
  - 前端使用 **React**
  - 后端使用 **Python (FastAPI)**
  - 数据库使用 **PostgreSQL**

## 后端逻辑架构

### 总体概览与模块设计
- 后端由以下主要模块组成并设计如下：
  - **区块链核心**（`mABC/core/`）
    - 区块、交易、链管理、状态机与出块逻辑；定义 `Block`, `Transaction`, `Chain` 等数据结构
    - 负责打包交易、计算 Merkle Root、链接 Hash
    - 提供 `add_block()`, `get_block()`, `get_transactions()` 等方法，支持链的增量与回滚接口。
  - **虚拟机执行模块**（`mABC/core/vm.py`, `mABC/core/state.py`）
    - 在执行交易前做前置校验（签名、nonce、Gas 等）
    - 执行合约方法并生成事件/receipt，写回 World State，并支持事务回滚（交易执行失败时不改变状态）。
  - **合约库**（`mABC/contracts/`）
    - 有 `ops_contract.py`, `token_contract.py`, `governance_contract.py`
    - 用 **状态机** 管理 SOP 流程（Init → Data_Collected → Root_Cause_Proposed → Consensus → Solution）
    - 实现质押、投票、奖励与罚没逻辑
    - 定义事件与日志用于审计与前端可视化
  - **Agent 模块**（`mABC/agents/`）
    -  `profile.py` 中定义各类Agent的角色与行为
    -  `profile.py` 中为 Agent 分配地址/私钥并修改 Prompt，使 Agent 输出结构化交易数据；处理交易回执并把结果反馈给 Agent（成功/失败/证据链）
    -  `dao_run.py` 将 Agent 的输出封装成 `Transaction` 并签名

### 多智能体架构

- 项目中 定义了 7 个专业化智能体，各司其职：

| 智能体                   | 核心功能           | 输入                      | 输出                                     |
| ------------------------ | ------------------ | ------------------------- | ---------------------------------------- |
| Alert Receiver (A1)      | 告警优先级排序     | 原始告警流                | 最高优先级告警                           |
| Process Scheduler (A2)   | 任务调度与流程控制 | 告警、子任务结果          | 子任务分配、是否完成判断                 |
| Data Detective (A3)      | 性能数据采集       | 节点列表、时间窗口        | 结构化指标（延迟、错误率、资源使用率等） |
| Dependency Explorer (A4) | 服务依赖挖掘       | 节点、时间窗口            | 依赖关系图（直接/间接）                  |
| Probability Oracle (A5)  | 故障概率评估       | 节点指标、依赖关系        | 各节点/边的故障概率                      |
| Fault Mapper (A6)        | 故障网络构建       | 节点+概率                 | 可视化 Fault Web（图结构）               |
| Solution Engineer (A7)   | 修复方案生成       | 根因、Fault Web、历史案例 | 具体操作建议                             |

所有智能体平等协作，形成去中心化的 Agent Chain。

### 一次根因分析的完整流程

1. 告警接收与初始分配
   - **Alert Receiver (A1)** 接收告警并做优先级排序，生成高优先级告警事件。
   - 告警以结构化事件提交给 **Process Scheduler (A2)**，触发一次分析任务（并记录时间戳与告警哈希）。

2. 数据采集与证据上链
   - **Data Detective (A3)** 拉取相关端点的性能指标并生成 `DataCollected` 证据包，计算证据的哈希（evidence_hash）。
   - 证据及其元数据封装为一个 **交易 (Transaction)**，由 Agent 签名并通过 **Agent Middleware / DAOExecutor** 提交到链上（交易包含 evidence_hash、原始来源、时间戳、可选质押金额）。

3. 依赖挖掘与因果候选生成
   - **Dependency Explorer (A4)** 生成依赖图并上链（或上传并在链上记录其哈希）。
   - **Probability Oracle (A5)** 基于数据与依赖图计算每个节点的故障概率，提出**候选根因**并以 `RootCauseProposed` 交易提交，**提案者需质押 (stake)**。

4. 投票与共识治理
   - 提案进入投票期，其他 Agent（包括 A3、A4、A6 等）通过提交 `Vote` 交易参与投票，**投票需要锁定质押金**。
   - **治理合约**（`governance_contract.py`）在链上统计投票权重（可为 stake × reputation），达到阈值则提案通过；否则提案失败并可能触发罚没。

5. 方案生成与执行
   - 若根因提案通过，**Solution Engineer (A7)** 根据通过的提案和证据链生成修复方案，并以 `SolutionSubmitted` 交易上链。
   - 区块链虚拟机（VM）执行合约逻辑，产生事件（events）与回执（receipt），并触发奖励/罚没结算。

6. 奖惩结算与审计记录
   - **Token 合约** 根据合约规则分发奖励或执行罚没（`token_contract.py`），状态变化写入 World State，生成可验证的事件日志。
   - 每个区块计算 **Merkle Root**，证据哈希列入 Merkle Tree，前端可通过 Merkle Proof 验证任意证据未被篡改。

- 下图为根因分析的高层流程：

![根因分析流程图](../images/root_cause_flow.png)

### 架构图

![总体架构图](../images/arch.png)
