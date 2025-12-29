# 第四部分｜代码说明：区块链底层、智能合约与 Agent 改造

本节以“设计解释”为主，聚焦类职责、关键成员与方法、设计动机与权衡。

## 设计总览
- 分层结构
  - 数据与执行层：Account/Transaction/Block、WorldState/StateProcessor、Blockchain(VM)、ChainClient。
  - 合约层：OpsSOPContract（流程控制）、GovernanceContract（投票与阈值）、TokenContract（经济模型）。
  - Agent 层：DAOExecutor（链上化投票与奖惩分发）。
- 统一原则
  - 单点持久化：WorldState 负责账户与合约状态的持久化与原子更新，其他层不直接写库。
  - 合约松耦合：治理合约只统计与判定，共识推进通过调用 SOP 合约，SOP 不嵌入投票细节。
  - 经济可审计：VM 在出块时统一扣/记 Gas，失败路径回滚并从金库扣回，保证账目一致。

## 数据与执行层
- Account
  - 关键成员：balance、stake、reputation、nonce、root_cause_proposals、votes（见 [types.py:Account](../../mABC/core/types.py#L49-L59)）
  - 设计动机：把“行为记录”与“权重依据”内聚到账户，便于计算投票权重与链上审计；reputation 作为软权重，stake 作为硬抵押。
- Transaction / Block / BlockHeader
  - 要点：交易携带 gas_price/gas_limit/signature；区块持有 merkle_root 以支持校验与浏览器展示（见 [types.py](../../mABC/core/types.py#L21-L46)）
  - 设计动机：把成本与签名放在交易层，VM 只做统一校验与记账，便于扩展与替换。
- WorldState / StateProcessor
  - WorldState：SQLite 持久化账户映射与合约状态，提供 get/update/increment_nonce 等原语（见 [state.py](../../mABC/core/state.py#L31-L147)）
  - StateProcessor：按 tx_type 路由到合约方法，形成“一个入口”的扩展点（见 [state.py:apply_transaction](../../mABC/core/state.py#L157-L182)）
  - 取舍：路由器保证扩展性；持久化与逻辑分离，降低耦合。
- Blockchain（VM）
  - 关键成员：pending_transactions、chain、gas_price、min_gas_limit、_treasury_address（见 [vm.py](../../mABC/core/vm.py#L31-L40)）
  - 关键方法：add_transaction（签名/Nonce/Gas 校验入池）、mine_block（扣费→记金库→执行→失败回滚→入链）、_verify_transaction_signature（注册表查公钥验签）
  - 设计动机：把经济记账与执行原子化在 VM 层完成，确保账户与金库账目与区块内容的一致性。
- ChainClient
  - 角色：封装 Agent 与链的交互（发送、出块、查询），降低 Agent 对 VM 的耦合（见 [client.py](../../mABC/core/client.py#L31-L76)）

## 智能合约层
- OpsSOPContract
  - 类级存储 storage：current_state、incident_data、proposals、events（见 [ops_contract.py](../../mABC/contracts/ops_contract.py#L40-L55)）
  - 方法：submit_data_collection、propose_root_cause、advance_to_consensus_phase（见 [ops_contract.py](../../mABC/contracts/ops_contract.py#L57-L146)）
  - 设计动机：SOP 专注流程与事件，不绑定投票细节，便于未来替换治理策略。
- GovernanceContract
  - 权重：weight = 1.0 + rep_bonus + stake_bonus（软硬结合，避免“全 1”）（见 [governance_contract.py](../../mABC/contracts/governance_contract.py#L61-L71)）
  - 阈值：仅统计“对该提案有投票记录的账户”，避免非参与与金库干扰（见 [governance_contract.py](../../mABC/contracts/governance_contract.py#L93-L114)）
  - 设计动机：避免共识卡死与虚高门槛；通过 SOP 回调推进阶段，保持解耦。
- TokenContract
  - 方法族：transfer/stake/slash/reward/penalty（见 [token_contract.py](../../mABC/contracts/token_contract.py#L13-L162)）
  - 特殊设计：reward 从金库扣款且信誉限制范围；penalty 罚没不超过余额且统一入金库
  - 设计动机：经济后果原子化执行，保证金库的单一资金流入口，方便审计。

## Agent 改造
- 关键成员
  - alpha/beta：支持率与参与率阈值，便于策略调参与 A/B。
  - proposal_counter：提案 ID 生成器，避免冲突。
  - TreasuryAccount：缓存金库地址/私钥，避免重复创建实例（见 [dao_run.py](../../mABC/agents/base/dao_run.py#L311-L334)）
  - weight：随信誉/质押动态调整，体现“风险即影响力”（见 [dao_run.py](../../mABC/agents/base/dao_run.py#L79-L101)）
- 关键方法与动机
  - run：统一流程（同步状态→自动质押→投票→统计→判定→奖惩），替代递归式思考，防止死循环。
  - _stake_tokens：分档质押与上限保护，避免余额快速耗尽。
  - _create_and_submit_vote_transaction：强制所有决策链上化，保证可审计/可回放。
  - distribute_rewards / distribute_penalties：将经济后果绑定到行为结果，形成“有亏有赚”的博弈闭环。

## 经济系统
- 参数与约束
  - gas_price=1、min_gas_limit=200：降低基础成本，保持经济盈利窗口（见 [vm.py](../../mABC/core/vm.py#L34-L36)）
  - treasury：单例金库；Gas 与罚没统一入账，奖励与返还从金库支出（见 [vm.py](../../mABC/core/vm.py#L153-L169)、[dao_run.py](../../mABC/agents/base/dao_run.py#L311-L334)）
- 奖惩闭环
  - 通过：提案人 +800/+5、支持者 +300/+1、支持者 Gas 返还 70%、提案人赏金 +1000；反对者小额罚没（-50/-1）。
  - 否决：提案人 -300/-5、支持者 -100/-1。
  - 设计动机：鼓励“高置信度参与”，确保系统长期可盈利并与真实链记账一致。
- 记账与回滚
  - VM 在执行前扣 Gas，失败交易回滚并从金库扣回，保证链/账/前端一致（见 [vm.py](../../mABC/core/vm.py#L179-L188)）

## 设计取舍与替代方案
- 仅统计“已投票者权重”：避免未参与者稀释门槛，减少流程卡死；与治理论文的参与度权重一致。
- 轻量 VM vs EVM 兼容：教学与可审计优先，轻量 VM 足够；未来可替换为真实链调用。
- SQLite 选择：部署与审计友好，后续可替换为键值库；结构清晰，课堂演示友好。
- 金库单例：降低复杂度与审计成本；未来可扩展到多资产/多金库分区。


## 区块链底层实现
- 数据结构设计
  - 账户、交易、区块与区块头承担最小必要的职责，交易包含成本与签名，区块包含 Merkle 根用于校验与前端展示，参见 [types.py](../../mABC/core/types.py#L21-L59)、[types.py](../../mABC/core/types.py#L61-L74)。
- 主链维护
  - 公钥注册表、区块哈希计算与区块合法性校验分层实现，保证扩展与可审计性，参见 [blockchain.py](../../mABC/core/blockchain.py#L20-L171)。
- VM 执行与记账
  - Gas 参数与金库缓存：统一参数入口与金库地址缓存，避免重复扫描，参见 [vm.py](../../mABC/core/vm.py#L31-L40)。
  - 入池校验：验签、Nonce 与 Gas 基线/余额检查，确保进入交易池前就近失败，参见 [vm.py](../../mABC/core/vm.py#L95-L120)。
  - 出块原子记账：先扣 Gas 并记入金库，执行失败则从金库原路扣回，实现账户/金库/链三者账目一致，参见 [vm.py](../../mABC/core/vm.py#L125-L181)。
  - 验签流程：ECDSA + 注册表取公钥，签名对交易摘要进行校验，参见 [vm.py](../../mABC/core/vm.py#L207-L236)。
- 世界状态与路由
  - SQLite 持久化与加载：结构化账户表 + JSON 字段，课堂与审计友好，参见 [state.py](../../mABC/core/state.py#L31-L147)。
  - 原子更新：update_account 将内存与数据库一次性同步，避免部分更新，参见 [state.py](../../mABC/core/state.py#L348-L351)。
  - Nonce 管理：increment_nonce 只增不减，保障重放保护，参见 [state.py](../../mABC/core/state.py#L352-L356)。
  - 交易路由：apply_transaction 统一入口，按 tx_type 分发到合约方法，参见 [state.py](../../mABC/core/state.py#L358-L376)。

## 智能合约设计
- SOP 合约（流程控制）
  - storage 仅维护当前状态、事件与活跃提案 ID，保持与治理逻辑解耦，参见 [ops_contract.py](../../mABC/contracts/ops_contract.py#L40-L55)。
  - submit/propose/advance 方法围绕状态机推进并发射事件，参见 [ops_contract.py](../../mABC/contracts/ops_contract.py#L57-L146)。
- 治理合约（投票与阈值）
  - 动态权重：基础 1.0 + 信誉加成 + 质押加成，降低低质量投票影响，参见 [governance_contract.py](../../mABC/contracts/governance_contract.py#L61-L77)。
  - 阈值统计：仅统计“已投票账户”总权重，避免非参与者干扰，通过/否决回调 SOP，参见 [governance_contract.py](../../mABC/contracts/governance_contract.py#L93-L124)。
- Token 合约（经济模型）
  - transfer/stake/slash/reward/penalty 保持原子记账与信誉边界，罚没金额不超过余额且统一路由金库，参见 [token_contract.py](../../mABC/contracts/token_contract.py#L13-L162)。

## Agent 改造（DAO 执行器）
- 流程与策略
  - 权重计算：链上账户信誉与质押映射为 Agent 权重，参见 [dao_run.py](../../mABC/agents/base/dao_run.py#L79-L101)。
  - 自动质押：按信誉分档设置目标质押并做余额上限保护，参见 [dao_run.py](../../mABC/agents/base/dao_run.py#L128-L146)。
  - 投票交易：统一通过 ChainClient 创建、签名、上链与出块，参见 [dao_run.py](../../mABC/agents/base/dao_run.py#L336-L362)。
- 激励与罚没分发
  - 通过：提案人/支持者奖励与支持者 Gas 返还；否决：提案人/支持者惩罚，参见 [dao_run.py](../../mABC/agents/base/dao_run.py#L233-L291)、[dao_run.py](../../mABC/agents/base/dao_run.py#L370-L377)。
- 系统金库
  - 金库账户创建与缓存：初始化余额与信誉，并缓存地址与私钥，参见 [dao_run.py](../../mABC/agents/base/dao_run.py#L311-L334)。
  - VM 记账与回滚：非奖励交易的 Gas 计入金库，失败原路扣回，参见 [vm.py](../../mABC/core/vm.py#L153-L165)、[vm.py](../../mABC/core/vm.py#L179-L185)。

## 设计要点与创新
- “有亏有赚”的经济模型
  - 通过智能合约实现正向激励与逆向罚没并存，使投票行为与结果绑定真实经济后果，提高谨慎度与参与度，见奖励/罚没具体实现与分发引用。
- 参与者权重的动态化
  - 将信誉与质押整合到投票权重中，降低低质量 Agent 干扰，提升可靠性，见 `mABC/contracts/governance_contract.py:61`、`mABC/agents/base/dao_run.py:92`。
- 金库与 Gas 的真实化记账
  - 所有 Gas 按交易执行过程计入金库；失败交易进行原子回滚，提升经济系统审计一致性，见 `mABC/core/vm.py:153`、`mABC/core/vm.py:179`。
- SOP 与治理合约解耦
  - SOP 负责流程与事件，治理合约负责投票与阈值，使用合约回调推进阶段，结构清晰、可替换，见 `mABC/contracts/ops_contract.py:112`、`mABC/contracts/governance_contract.py:116`。

## 运行与交互要点
- 交易生命周期
  - Agent 通过 `ChainClient` 创建交易并签名，上链后由 VM 执行并更新状态，见 `mABC/core/client.py:31`、`mABC/core/client.py:43`、`mABC/core/client.py:55`、`mABC/core/client.py:76`。
- 日志与前端
  - 合约事件与奖励日志为前端经济看板提供数据源；奖励日志已净化为单条完整信息，便于展示与审计，见 `mABC/agents/base/dao_run.py:284`。
