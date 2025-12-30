# 第四部分｜代码说明：区块链底层、智能合约与 Agent 改造

本节将详细展示并解释项目的核心代码实现，帮助理解系统是如何运作的。我们将从底层数据结构开始，逐步介绍 VM 执行引擎、世界状态管理、智能合约逻辑，最后展示 DAO Agent 如何与链进行交互。

## 1. 区块链底层架构 (Core Layer)

### 1.1 数据结构定义 (Types)

我们首先定义了区块链的基础数据模型，包括账户 (`Account`)、交易 (`Transaction`) 和区块 (`Block`)。这些结构是整个系统的基石。

**设计思路**：
- **Account**: 不仅包含余额 (`balance`)，还内置了信誉 (`reputation`) 和质押 (`stake`) 字段，这是为了支持我们基于信誉的 DAO 治理机制。
- **Transaction**: 包含 `tx_type` 字段，支持多种交易类型（如投票、提案、奖惩），而不仅仅是转账。
- **Block**: 包含 Merkle Root 以确保交易数据的不可篡改性。

>*[请在此处插入PPi中的“数据结构类图”或“账户模型设计图”]
 1.2 虚拟机与挖矿 (VM & Mining)
`Blockchain` 类充当了虚拟机的角色，负责管理交易池、验证交易签名、执行交易以及打包出块。

**核心逻辑**：
1.  **交易入池**：验证签名、Nonce 防重放、Gas 检查。
2.  **挖矿出块**：
    *   从交易池获取交易。
    *   **原子化记账**：先扣除 Gas 费并计入“系统金库”，如果交易执行失败，则回滚状态并从金库退还（非恶意失败）。
    *   调用 `StateProcessor` 执行具体业务逻辑。
    *   生成 Merkle Root 并打包区块。

![Diagram](./images/mermaid_8182058281393456581.png)

**代码实现 (`mABC/core/vm.py`)**:

```python
def mine_block(self) -> Optional[Block]:
    # ... (省略部分代码) ...
    # 调用StateProcessor执行交易
    successful_transactions = []
    for tx in transactions_to_mine:
        # 执行交易前先扣除Gas费用（奖励交易免Gas）
        gas_fee = tx.gas_price * tx.gas_limit
        account = world_state.get_account(tx.sender)
        
        # ... (扣除Gas费逻辑) ...

        # 调用StateProcessor应用交易
        if state_processor.apply_transaction(tx):
            successful_transactions.append(tx)
            # 增加nonce
            world_state.increment_nonce(tx.sender)
        else:
            print(f"Failed to apply transaction: {tx.tx_type}")
            # 失败回滚：退还Gas费用（非奖励交易）
            if tx.tx_type != TransactionType.REWARD:
                account.balance += gas_fee
                world_state.update_account(account)
                # 从金库扣回已记账的Gas
                treasury = self._get_treasury_account()
                if treasury and (treasury.balance or 0) >= gas_fee:
                    treasury.balance -= gas_fee
                    world_state.update_account(treasury)
    # ... (打包区块逻辑) ...
```

### 1.3 世界状态管理 (World State)

`WorldState` 类负责数据的持久化，使用 SQLite 数据库存储所有账户的状态。`StateProcessor` 则是交易执行的路由器。

**设计亮点**：
- **持久化**：所有账户状态实时保存到 `state.db`，重启不丢失。
- **路由分发**：`apply_transaction` 方法根据 `tx_type` 将交易分发给不同的智能合约方法处理，实现了逻辑解耦。

**代码实现 (`mABC/core/state.py`)**:

```python
class StateProcessor:
    def apply_transaction(self, tx: 'Transaction') -> bool:
        """应用交易到世界状态：路由分发"""
        try:
            # 根据交易类型执行不同的操作
            if tx.tx_type == "propose_root_cause":
                return self._apply_propose_root_cause(tx)
            elif tx.tx_type == "vote":
                return self._apply_vote(tx)
            elif tx.tx_type == "transfer":
                return self._apply_transfer(tx)
            elif tx.tx_type == "stake":
                return self._apply_stake(tx)
            elif tx.tx_type == "slash":
                return self._apply_slash(tx)
            elif tx.tx_type == "reward":
                return self._apply_reward(tx)
            elif tx.tx_type == "penalty":
                return self._apply_penalty(tx)
            else:
                return False
        except Exception as e:
            print(f"Failed to apply transaction: {e}")
            return False
```

---

## 2. 智能合约层 (Smart Contracts)

智能合约层实现了系统的业务逻辑，分为流程控制、治理和经济模型三个部分。

### 2.1 运维流程合约 (SOP Contract)

负责管理故障处理的生命周期状态机：`Init` -> `Data_Collected` -> `Root_Cause_Proposed` -> `Consensus` -> `Solution`。它只负责状态流转，不负责具体的投票权重计算，体现了单一职责原则。

**代码实现 (`mABC/contracts/ops_contract.py`)**:

```python
class SOPState(str, Enum):
    """SOP 状态机定义"""
    Init = "Init"
    Data_Collected = "Data_Collected"
    Root_Cause_Proposed = "Root_Cause_Proposed"
    Consensus = "Consensus"
    Solution = "Solution"

def advance_to_consensus_phase(self, proposal_id: str, passed: bool):
    """
    由治理合约调用
    在完成投票统计、质押检查、奖惩执行后，调用此方法推进 SOP 状态并发射事件
    """
    if passed:
        # 通过 → Consensus → Solution
        self.storage["current_state"] = SOPState.Consensus.value
        self._emit_event("ConsensusReached", proposal_id=proposal_id, passed=True)
        # ...
    else:
        # 否决 → 回退到 Data_Collected，可重新提案
        self.storage["current_state"] = SOPState.Data_Collected.value
        # ...
```

### 2.2 治理合约 (Governance Contract)

负责处理投票逻辑。我们设计了动态权重机制：**投票权重 = 基础分 + 信誉加成 + 质押加成**。

**设计解释**：
- 这种机制确保了高信誉和高质押的节点拥有更大的话语权，防止女巫攻击。
- **阈值判定**：仅统计参与投票的节点权重，避免因节点不在线导致共识卡死。

![Diagram](./images/mermaid_6806067285014974204.png)

**代码实现 (`mABC/contracts/governance_contract.py`)**:

```python
def vote(self, tx_data: Dict[str, Any], sender: str, timestamp: int) -> bool:
    # ... (省略) ...
    # 计算权重（与前端展示保持一致）：
    # 基础权重: 1.0
    # 信誉加成: max(0, (reputation - 50) / 10.0)
    # 质押加成: stake / 1000.0
    rep_bonus = max(0.0, (voter_account.reputation - 50) / 10.0)
    stake_bonus = voter_account.stake / 1000.0
    weight = 1.0 + rep_bonus + stake_bonus
    
    # ... (更新投票记录) ...
    
    # 检查共识是否达成
    self._check_consensus(proposal_id, proposal_data)
    return True

def _check_consensus(self, proposal_id: str, proposal_data: Dict[str, Any]):
    # 计算参与者总权重（仅统计对该提案有投票记录的账户）
    total_network_weight = 0.0
    for account in self.world_state.state.values():
        if account.votes.get(proposal_id):
            # ... (计算权重) ...
            total_network_weight += weight
            
    # 设定通过阈值 (50%)
    threshold = total_network_weight * 0.5
    
    if votes_for > threshold:
        ops_sop_contract.advance_to_consensus_phase(proposal_id, passed=True)
    elif votes_against > threshold:
        ops_sop_contract.advance_to_consensus_phase(proposal_id, passed=False)
```

### 2.3 代币经济合约 (Token Contract)

负责具体的转账、质押、奖励和罚没操作，实现了“有亏有赚”的经济闭环。

**核心功能**：
- **Reward**: 从系统金库转账给贡献者，并提升信誉。
- **Penalty**: 扣除恶意节点的余额转入金库，并降低信誉。

**代码实现 (`mABC/contracts/token_contract.py`)**:

```python
def reward(self, tx_data: Dict[str, Any], sender: str) -> bool:
    """执行奖励 (从金库扣款 + 目标账户加款 + 信誉)"""
    # ... (逻辑省略) ...
    if amount > 0:
        from_account.balance -= amount
        target_account.balance += amount
    if reputation != 0:
        target_account.reputation += reputation
    # ...
    return True

def penalty(self, tx_data: Dict[str, Any], sender: str) -> bool:
    """执行罚没 (将目标余额的一部分转入系统金库，并降低信誉)"""
    # ... (逻辑省略) ...
    # 找到系统金库账户
    treasury = blockchain._get_treasury_account()
    
    # 扣减余额并转入金库
    if amount > 0:
        target_account.balance -= amount
        if treasury:
            treasury.balance = (treasury.balance or 0) + amount
    # ...
    return True
```

---

## 3. Agent 改造与交互 (DAO Executor)

我们将原有的 Agent 改造为 DAO Agent，使其所有关键决策都通过发交易上链来完成。

### 3.1 链上交互流程

Agent 不再是直接修改内存变量，而是遵循以下生命周期：
1.  **读取链上状态**：获取最新的信誉和余额。
2.  **自动质押**：根据信誉分自动计算并锁定质押金。
3.  **发送交易**：对投票意向签名并广播到网络。
4.  **监听结果**：等待出块确认。

![Diagram](./images/mermaid_2183594475148606752.png)

**代码实现 (`mABC/agents/base/dao_run.py`)**:

```python
def run(self, agents: List[AgentWorkflow], ...):
    # 1. 同步Agent链上状态
    for agent in agents:
        account = self.chain_client.get_account(agent.wallet_address)
        # ... 计算动态权重 ...

    # 2. 自动质押策略
    for agent in agents:
        # ... 根据信誉计算 target_stake ...
        if stake_delta > 0:
            self._stake_tokens(agent, stake_delta)

    # 3. 收集投票并上链
    for agent in agents:
        vote_option = self.submit_vote(...)
        # 创建并提交投票交易
        self._create_and_submit_vote_transaction(
            agent, proposal_id, vote_option
        )

    # 4. 根据结果分发奖惩 (调用合约)
    if run_result:
        self.distribute_rewards(...)
    else:
        self.distribute_penalties(...)
```

### 3.2 奖惩分发实现

Agent 执行器在投票结束后，会根据共识结果调用 `TokenContract` 的接口进行奖惩分发。

```python
def distribute_rewards(self, ...):
    treasury = self._get_or_create_treasury_account()
    
    # 奖励提案人
    if proposer:
        self._send_reward(treasury, proposer.wallet_address, 800, 5, "Proposal Passed")
        
    # 奖励支持者
    for rec in supporters:
        self._send_reward(treasury, rec["address"], 300, 1, "Voting Support")
        
    # 返还Gas
    # ...
```
