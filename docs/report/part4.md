# 第四部分｜代码说明：区块链底层、智能合约与 Agent 改造

## 区块链底层实现
- 数据结构
  - 账户模型 `Account` 定义余额、质押、信誉与投票/提案映射，支撑链上行为记录与权重计算，见 `mABC/core/types.py:49`。
  - 交易模型 `Transaction` 包含 `tx_type/sender/nonce/gas_price/gas_limit/data/signature/timestamp`，见 `mABC/core/types.py:21`。
  - 区块头与区块 `BlockHeader/Block`，含 `merkle_root` 与哈希，见 `mABC/core/types.py:33` 与 `mABC/core/types.py:42`。
  - Merkle 根计算 `get_merkle_root` 与哈希函数 `calculate_hash`，见 `mABC/core/types.py:74`、`mABC/core/types.py:61`。
```python
# mABC/core/types.py:21
class Transaction(BaseModel):
    tx_type: str
    sender: str
    nonce: int
    gas_price: int
    gas_limit: int
    data: Dict[str, Any]
    signature: Optional[str] = None
    timestamp: int = Field(default_factory=lambda: int(time.time()))

# mABC/core/types.py:33,42
class BlockHeader(BaseModel):
    index: int
    timestamp: int
    previous_hash: str
    merkle_root: str
    nonce: int = 0

class Block(BaseModel):
    header: BlockHeader
    transactions: List[Transaction]
    hash: Optional[str] = None

# mABC/core/types.py:49
class Account(BaseModel):
    address: str
    name: str = ''
    balance: int = 0
    stake: int = 0
    reputation: int = 100
    nonce: int = 0
    root_cause_proposals: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    votes: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

# mABC/core/types.py:61,74
def calculate_hash(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()

def get_merkle_root(transactions: List[Transaction]) -> str:
    if not transactions:
        return calculate_hash("")
    transaction_hashes = []
    for tx in transactions:
        tx_dict = tx.model_dump()
        tx_json = str(sorted(tx_dict.items()))
        transaction_hashes.append(calculate_hash(tx_json))
    merkle_tree = transaction_hashes[:]
    while len(merkle_tree) > 1:
        if len(merkle_tree) % 2 == 1:
            merkle_tree.append(merkle_tree[-1])
        new_level = []
        for i in range(0, len(merkle_tree), 2):
            combined = merkle_tree[i] + merkle_tree[i + 1]
            new_level.append(calculate_hash(combined))
        merkle_tree = new_level
    return merkle_tree[0]
```
- 主链维护
  - 创世区块创建、区块哈希计算与合法性验证，见 `mABC/core/blockchain.py:20`、`mABC/core/blockchain.py:70`、`mABC/core/blockchain.py:85`、`mABC/core/blockchain.py:116`。
```python
# mABC/core/blockchain.py:20
@classmethod
def register_public_key(cls, address: str, public_key: str) -> None:
    cls._registry[address] = public_key

# mABC/core/blockchain.py:70
def _calculate_block_hash(self, block: Block) -> str:
    header_dict = block.header.model_dump()
    header_json = json.dumps(header_dict, sort_keys=True, separators=(',', ':'))
    return calculate_hash(header_json)

# mABC/core/blockchain.py:85
def add_block(self, block: Block) -> bool:
    previous_block = self.chain[-1]
    if block.header.previous_hash != previous_block.hash:
        return False
    if block.hash != self._calculate_block_hash(block):
        return False
    calculated_merkle_root = get_merkle_root(block.transactions)
    if block.header.merkle_root != calculated_merkle_root:
        return False
    self.chain.append(block)
    return True

# mABC/core/blockchain.py:116
def get_latest_block(self) -> Block:
    return self.chain[-1]
```
- 状态与执行（VM）
  - 区块链执行层 `Blockchain` 管理交易池、Gas 参数、系统金库缓存，见 `mABC/core/vm.py:31`、`mABC/core/vm.py:34`、`mABC/core/vm.py:35`、`mABC/core/vm.py:65`。
```python
# mABC/core/vm.py:31,34,35
def __init__(self):
    self.pending_transactions: List[Transaction] = []
    self.chain: List[Block] = []
    self.gas_price = 1
    self.min_gas_limit = 200
    self._treasury_address: Optional[str] = None
    self._treasury_private_key: Optional[SigningKey] = None
    self.agent_addresses = set()

# mABC/core/vm.py:65
def _get_treasury_account(self):
    if not world_state.state:
        return None
    if self._treasury_address and self._treasury_address in world_state.state:
        if self._treasury_address not in self.agent_addresses:
            return world_state.get_account(self._treasury_address)
        else:
            self._treasury_address = None
    max_acc = None
    for acc in world_state.state.values():
        if acc.address in self.agent_addresses:
            continue
        if max_acc is None or (acc.balance or 0) > (max_acc.balance or 0):
            max_acc = acc
    if max_acc:
        self._treasury_address = max_acc.address
    return max_acc
```
  - 交易入池校验（签名、Nonce、Gas 基线与余额），见 `mABC/core/vm.py:95`、`mABC/core/vm.py:99`、`mABC/core/vm.py:105`、`mABC/core/vm.py:111`、`mABC/core/vm.py:120`。
```python
# mABC/core/vm.py:95,99,105,111,120
def add_transaction(self, tx: Transaction) -> bool:
    if not self._verify_transaction_signature(tx):
        return False
    account = world_state.get_account(tx.sender)
    if account and tx.nonce != account.nonce:
        return False
    if tx.tx_type != TransactionType.REWARD:
        if tx.gas_limit < self.min_gas_limit:
            return False
    if tx.tx_type != TransactionType.REWARD:
        required_gas = tx.gas_price * tx.gas_limit
        if account and account.balance < required_gas:
            return False
    self.pending_transactions.append(tx)
    return True
```
  - 出块流程与 Gas 记账：扣费→记入金库→执行→失败回滚（含金库回退），见 `mABC/core/vm.py:125`、`mABC/core/vm.py:150`、`mABC/core/vm.py:153`、`mABC/core/vm.py:165`、`mABC/core/vm.py:173`、`mABC/core/vm.py:179`、`mABC/core/vm.py:181`。
```python
# mABC/core/vm.py:125,150,153,165,173,179,181
def mine_block(self) -> Optional[Block]:
    if not self.pending_transactions:
        return None
    transactions_to_mine = self.pending_transactions.copy()
    self.pending_transactions.clear()
    previous_block = self.chain[-1]
    new_header = BlockHeader(
        index=previous_block.header.index + 1,
        timestamp=int(time.time()),
        previous_hash=previous_block.hash or "",
        merkle_root=get_merkle_root(transactions_to_mine),
    )
    new_block = Block(header=new_header, transactions=transactions_to_mine)
    successful_transactions = []
    for tx in transactions_to_mine:
        gas_fee = tx.gas_price * tx.gas_limit
        account = world_state.get_account(tx.sender) or world_state.create_account(tx.sender)
        if tx.tx_type == TransactionType.REWARD:
            pass
        elif account.balance >= gas_fee:
            account.balance -= gas_fee
            world_state.update_account(account)
            treasury = self._get_treasury_account()
            if treasury:
                treasury.balance = (treasury.balance or 0) + gas_fee
                world_state.update_account(treasury)
        else:
            print(f"Insufficient balance for gas fee: {tx.sender}")
        if state_processor.apply_transaction(tx):
            successful_transactions.append(tx)
            world_state.increment_nonce(tx.sender)
        else:
            if tx.tx_type != TransactionType.REWARD:
                account.balance += gas_fee
                world_state.update_account(account)
                treasury = self._get_treasury_account()
                if treasury and (treasury.balance or 0) >= gas_fee:
                    treasury.balance -= gas_fee
                    world_state.update_account(treasury)
    new_block.transactions = successful_transactions
    new_block.header.merkle_root = get_merkle_root(successful_transactions)
    new_block.hash = self._calculate_block_hash(new_block)
    self.chain.append(new_block)
    return new_block
```
  - 交易签名验签（ECDSA + 注册表查公钥），见 `mABC/core/vm.py:207`、`mABC/core/vm.py:214`、`mABC/core/vm.py:224`、`mABC/core/vm.py:236`。
```python
# mABC/core/vm.py:207,214,224,236
def _verify_transaction_signature(self, tx: Transaction) -> bool:
    if not tx.signature:
        return False
    from .blockchain import PublicKeyRegistry
    public_key_hex = PublicKeyRegistry.get_public_key(tx.sender)
    if not public_key_hex:
        return False
    vk = VerifyingKey.from_string(bytes.fromhex(public_key_hex), curve=SECP256k1)
    tx_dict = tx.model_dump(exclude={"signature"})
    tx_json = json.dumps(tx_dict, sort_keys=True, separators=(",", ":"))
    from .types import calculate_hash
    tx_hash = calculate_hash(tx_json)
    try:
        result = vk.verify_digest(bytes.fromhex(tx.signature), bytes.fromhex(tx_hash), sigdecode=sigdecode_der)
        return result
    except Exception:
        return False
```
- 世界状态 `WorldState`
  - SQLite 持久化、账户读写、Nonce 自增，见 `mABC/core/state.py:31`、`mABC/core/state.py:65`、`mABC/core/state.py:118`、`mABC/core/state.py:122`、`mABC/core/state.py:130`、`mABC/core/state.py:140`。
  - 状态处理器 `StateProcessor` 按 `tx_type` 路由到合约方法（提案/投票/转账/质押/惩罚/奖励/罚没），见 `mABC/core/state.py:157`、`mABC/core/state.py:184`、`mABC/core/state.py:216`、`mABC/core/state.py:227`、`mABC/core/state.py:238`、`mABC/core/state.py:248`、`mABC/core/state.py:258`、`mABC/core/state.py:268`。
```python
# mABC/core/state.py:31,65
def _init_db(self):
    conn = self._get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            address TEXT PRIMARY KEY,
            balance INTEGER,
            stake INTEGER,
            reputation INTEGER,
            nonce INTEGER,
            root_cause_proposals TEXT,
            votes TEXT
        )
    ''')
    conn.commit()
    conn.close()

def _load_state(self):
    conn = self._get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT address, balance, stake, reputation, nonce, root_cause_proposals, votes FROM accounts')
    rows = cursor.fetchall()
    for row in rows:
        address, balance, stake, reputation, nonce, proposals_json, votes_json = row
        proposals = json.loads(proposals_json) if proposals_json else {}
        votes = json.loads(votes_json) if votes_json else {}
        account = Account(
            address=address,
            balance=balance or 0,
            stake=stake or 0,
            reputation=reputation if reputation is not None else 100,
            nonce=nonce or 0,
            root_cause_proposals=proposals,
            votes=votes
        )
        self.state[address] = account
    conn.close()

# mABC/core/state.py:118,122,130,140
def get_account(self, address: str) -> Optional[Account]:
    return self.state.get(address)

def create_account(self, address: str) -> Account:
    if address not in self.state:
        new_account = Account(address=address)
        self.state[address] = new_account
        self._save_state([new_account])
    return self.state[address]

def update_account(self, account: Account):
    self.state[account.address] = account
    self._save_state([account])

def increment_nonce(self, address: str) -> int:
    account = self.get_account(address) or self.create_account(address)
    account.nonce += 1
    self.update_account(account)
    return account.nonce

# mABC/core/state.py:157,184,216,227,238,248,258,268
def apply_transaction(self, tx: 'Transaction') -> bool:
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
```

## 智能合约设计
- 运维流程合约（SOP）
  - 状态机与事件：`Init → Data_Collected → Root_Cause_Proposed → Consensus → Solution`，见 `mABC/contracts/ops_contract.py:14`、`mABC/contracts/ops_contract.py:40`。
  - 数据采集提交与根因提案（含事件发射与当前提案 ID 维护），见 `mABC/contracts/ops_contract.py:57`、`mABC/contracts/ops_contract.py:80`。
  - 共识推进：根据投票结果调用 `advance_to_consensus_phase` 推进到 `Consensus/Solution` 或回退，见 `mABC/contracts/ops_contract.py:112`。
```python
# mABC/contracts/ops_contract.py:14,40
class SOPState(str, Enum):
    Init = "Init"
    Data_Collected = "Data_Collected"
    Root_Cause_Proposed = "Root_Cause_Proposed"
    Consensus = "Consensus"
    Solution = "Solution"

_storage: Dict[str, Any] = {
    "current_state": SOPState.Init.value,
    "incident_data": {},
    "proposals": {},
    "current_proposal_id": None,
    "events": []
}

# mABC/contracts/ops_contract.py:57,80,112
def submit_data_collection(self, agent_id: str, data_summary: str, raw_data: Optional[Dict] = None):
    if self.storage["current_state"] != SOPState.Init.value:
        raise ValueError("Data collection can only be submitted in Init state")
    self.storage["current_state"] = SOPState.Data_Collected.value
    self.storage["incident_data"] = {
        "submitter": agent_id,
        "summary": data_summary,
        "raw_data": raw_data or {},
        "timestamp": datetime.now().isoformat()
    }
    self._emit_event("DataCollected", agent_id=agent_id, summary=data_summary)

def propose_root_cause(self, agent_id: str, content: str):
    if self.storage["current_state"] != SOPState.Data_Collected.value:
        raise ValueError("Root cause can only be proposed after data collection")
    proposal_id = hashlib.sha256(f"{agent_id}{content}{datetime.now().isoformat()}".encode()).hexdigest()
    proposal = {
        "proposal_id": proposal_id,
        "proposer": agent_id,
        "content": content,
        "timestamp": datetime.now().isoformat(),
        "status": "pending"
    }
    self.storage["proposals"][proposal_id] = proposal
    self.storage["current_proposal_id"] = proposal_id
    self.storage["current_state"] = SOPState.Root_Cause_Proposed.value
    self._emit_event("RootCauseProposed", proposal_id=proposal_id, proposer=agent_id, content=content)

def advance_to_consensus_phase(self, proposal_id: str, passed: bool):
    if self.storage["current_state"] != SOPState.Root_Cause_Proposed.value:
        raise ValueError("Can only advance consensus from Root_Cause_Proposed state")
    if proposal_id != self.storage["current_proposal_id"]:
        raise ValueError("Proposal ID does not match current active proposal")
    if passed:
        self.storage["current_state"] = SOPState.Consensus.value
        self._emit_event("ConsensusReached", proposal_id=proposal_id, passed=True)
        self.storage["current_state"] = SOPState.Solution.value
        proposal = self.storage["proposals"][proposal_id]
        self._emit_event("SolutionPhaseEntered", proposal_id=proposal_id, root_cause=proposal["content"])
    else:
        self.storage["current_state"] = SOPState.Data_Collected.value
        self.storage["current_proposal_id"] = None
        self._emit_event("ConsensusReached", proposal_id=proposal_id, passed=False)
        self._emit_event("ProposalRejected", proposal_id=proposal_id, proposer=self.storage["proposals"][proposal_id]["proposer"])
```
- 治理合约（投票与共识）
  - 投票入账与权重计算（基础 1.0 + 信誉加成 + 质押加成），见 `mABC/contracts/governance_contract.py:61`、`mABC/contracts/governance_contract.py:77`。
  - 共识判定采用“仅计已投票账户权重”的阈值统计（避免非参与账户影响），见 `mABC/contracts/governance_contract.py:93`、`mABC/contracts/governance_contract.py:103`、`mABC/contracts/governance_contract.py:113`。
  - 通过/否决时回调 SOP 合约事件并打印审计日志，见 `mABC/contracts/governance_contract.py:116`、`mABC/contracts/governance_contract.py:124`。
```python
# mABC/contracts/governance_contract.py:61,77
rep_bonus = max(0.0, (voter_account.reputation - 50) / 10.0)
stake_bonus = voter_account.stake / 1000.0
weight = 1.0 + rep_bonus + stake_bonus
vote_data = {
    "proposal_id": proposal_id,
    "vote_option": vote_option,
    "weight": weight,
    "timestamp": timestamp
}
voter_account.votes[proposal_id] = vote_data

# mABC/contracts/governance_contract.py:93,103,113,116,124
def _check_consensus(self, proposal_id: str, proposal_data: Dict[str, Any]):
    from contracts.ops_contract import ops_sop_contract
    votes_for = proposal_data["votes"]["for"]
    votes_against = proposal_data["votes"]["against"]
    total_network_weight = 0.0
    for account in self.world_state.state.values():
        if account.votes.get(proposal_id):
            rep_bonus = max(0.0, (account.reputation - 50) / 10.0)
            stake_bonus = account.stake / 1000.0
            weight = 1.0 + rep_bonus + stake_bonus
            total_network_weight += weight
    PASS_THRESHOLD_RATIO = 0.5
    threshold = total_network_weight * PASS_THRESHOLD_RATIO
    if votes_for > threshold:
        ops_sop_contract.advance_to_consensus_phase(proposal_id, passed=True)
    elif votes_against > threshold:
        ops_sop_contract.advance_to_consensus_phase(proposal_id, passed=False)
```
- Token 合约（经济模型）
  - 转账/质押/惩罚（扣质押），见 `mABC/contracts/token_contract.py:13`、`mABC/contracts/token_contract.py:40`、`mABC/contracts/token_contract.py:61`。
  - 奖励：从金库扣款，目标账户加款与信誉变更，见 `mABC/contracts/token_contract.py:87`、`mABC/contracts/token_contract.py:108`、`mABC/contracts/token_contract.py:118`。
  - 罚没：从目标账户扣减、信誉下降，并把罚没金额计入系统金库，见 `mABC/contracts/token_contract.py:122`、`mABC/contracts/token_contract.py:139`、`mABC/contracts/token_contract.py:149`、`mABC/contracts/token_contract.py:156`。
```python
# mABC/contracts/token_contract.py:13,40,61
def transfer(self, tx_data: Dict[str, Any], sender: str) -> bool:
    to_address = tx_data.get("to")
    amount = tx_data.get("amount")
    from_account = self.world_state.get_account(sender)
    if not to_address or amount is None or amount < 0:
        return False
    if not from_account or from_account.balance < amount:
        return False
    to_account = self.world_state.get_account(to_address) or self.world_state.create_account(to_address)
    from_account.balance -= amount
    to_account.balance += amount
    self.world_state.update_account(from_account)
    self.world_state.update_account(to_account)
    return True

def stake(self, tx_data: Dict[str, Any], sender: str) -> bool:
    amount = tx_data.get("amount")
    account = self.world_state.get_account(sender)
    if amount is None or amount < 0:
        return False
    if not account or account.balance < amount:
        return False
    account.balance -= amount
    account.stake += amount
    self.world_state.update_account(account)
    return True

def slash(self, tx_data: Dict[str, Any], sender: str) -> bool:
    target_address = tx_data.get("target")
    amount = tx_data.get("amount")
    target_account = self.world_state.get_account(target_address)
    if not target_address or amount is None or amount < 0:
        return False
    if not target_account:
        return False
    if target_account.stake < amount:
        amount = target_account.stake
    target_account.stake -= amount
    self.world_state.update_account(target_account)
    return True

# mABC/contracts/token_contract.py:87,108,118
def reward(self, tx_data: Dict[str, Any], sender: str) -> bool:
    target_address = tx_data.get("target")
    amount = tx_data.get("amount", 0)
    reputation = tx_data.get("reputation", 0)
    if not target_address:
        return False
    from_account = self.world_state.get_account(sender) or self.world_state.create_account(sender)
    target_account = self.world_state.get_account(target_address) or self.world_state.create_account(target_address)
    if amount > 0:
        if from_account.balance < amount:
            return False
        from_account.balance -= amount
        target_account.balance += amount
    if reputation != 0:
        target_account.reputation += reputation
        target_account.reputation = max(0, min(100, target_account.reputation))
    self.world_state.update_account(from_account)
    self.world_state.update_account(target_account)
    return True

# mABC/contracts/token_contract.py:122,139,149,156
def penalty(self, tx_data: Dict[str, Any], sender: str) -> bool:
    target_address = tx_data.get("target")
    amount = tx_data.get("amount", 0)
    reputation = tx_data.get("reputation", 0)
    if not target_address or amount < 0:
        return False
    target_account = self.world_state.get_account(target_address)
    if not target_account:
        return False
    amount = min(amount, max(0, target_account.balance))
    try:
        from core.vm import blockchain
        treasury = blockchain._get_treasury_account()
    except Exception:
        treasury = None
    if amount > 0:
        target_account.balance -= amount
        if treasury:
            treasury.balance = (treasury.balance or 0) + amount
            self.world_state.update_account(treasury)
    if reputation != 0:
        target_account.reputation += reputation
        target_account.reputation = max(0, min(100, target_account.reputation))
    self.world_state.update_account(target_account)
    return True
```

## Agent 改造（DAO 执行器）
- DAOExecutor 流程
  - 同步链上账户状态、根据信誉/质押计算动态权重，见 `mABC/agents/base/dao_run.py:79`、`mABC/agents/base/dao_run.py:92`。
  - 自动质押策略：按信誉分分档目标质押、上限保护余额，见 `mABC/agents/base/dao_run.py:128`、`mABC/agents/base/dao_run.py:139`、`mABC/agents/base/dao_run.py:146`。
  - 构造投票交易并上链，见 `mABC/agents/base/dao_run.py:336`、`mABC/agents/base/dao_run.py:349`、`mABC/agents/base/dao_run.py:362`。
  - 共识统计与阈值判断（支持率/参与率），见 `mABC/agents/base/dao_run.py:195`、`mABC/agents/base/dao_run.py:203`、`mABC/agents/base/dao_run.py:206`。
```python
# mABC/agents/base/dao_run.py:79,92
account = self.chain_client.get_account(agent.wallet_address)
reputation_bonus = max(0, (account.reputation - 50) / 10.0)
stake_bonus = account.stake / 1000.0
agent.weight = 1.0 + reputation_bonus + stake_bonus

# mABC/agents/base/dao_run.py:128,139,146
confidence = max(0.0, min(1.0, (account.reputation or 0) / 100.0))
if confidence >= 0.8:
    target_stake = min(200, int(account.balance * 0.05))
elif confidence >= 0.6:
    target_stake = min(100, int(account.balance * 0.02))
else:
    target_stake = 0
stake_delta = max(0, target_stake - (account.stake or 0))
if stake_delta > 0:
    st_ok = self._stake_tokens(agent, stake_delta)

# mABC/agents/base/dao_run.py:336,349,362
tx = self.chain_client.create_transaction(
    tx_type="vote",
    sender=agent.wallet_address,
    data={"proposal_id": proposal_id, "vote_option": vote_option},
    private_key=agent.private_key,
    gas_limit=200
)
return self.chain_client.send_and_mine(tx)

# mABC/agents/base/dao_run.py:195,203,206
support_rate = vote_weights["For"] / total_weight
participation_rate = (vote_weights["For"] + vote_weights["Against"]) / total_weight
run_result = support_rate >= self.alpha and participation_rate >= self.beta
```
- 激励与罚没分发
  - 奖励规则：提案人 +800 Token/+5 信誉，支持者 +300 Token/+1 信誉；通过后支持者返还 70% 投票 Gas；提案人获 1000 赏金，见 `mABC/agents/base/dao_run.py:233`、`mABC/agents/base/dao_run.py:239`、`mABC/agents/base/dao_run.py:245`、`mABC/agents/base/dao_run.py:248`、`mABC/agents/base/dao_run.py:259`、`mABC/agents/base/dao_run.py:261`。
  - 通过时惩罚反对者（罚没 + 信誉下降），见 `mABC/agents/base/dao_run.py:264`、`mABC/agents/base/dao_run.py:267`。
  - 否决时惩罚提案人与支持者，见 `mABC/agents/base/dao_run.py:370`、`mABC/agents/base/dao_run.py:374`、`mABC/agents/base/dao_run.py:377`。
  - 奖励发送与合并日志输出，见 `mABC/agents/base/dao_run.py:269`、`mABC/agents/base/dao_run.py:284`、`mABC/agents/base/dao_run.py:288`、`mABC/agents/base/dao_run.py:291`。
```python
# mABC/agents/base/dao_run.py:233,239,245,248,259,261
proposer = next((a for a in agents if a.role_name == proposer_role), None)
if proposer:
    self._send_reward(treasury, proposer.wallet_address, 800, 5, f"Proposal Passed: {proposal_id}")
supporters = [rec for rec in (vote_records or []) if rec.get("option") == "For"]
for rec in supporters:
    self._send_reward(treasury, rec["address"], 300, 1, f"Voting Support: {proposal_id}")
rebate_ratio = 0.7
vote_gas_limit = 200
rebate_amount = int(rebate_ratio * vote_gas_limit * 1)
for rec in supporters:
    self._send_reward(treasury, rec["address"], rebate_amount, 0, f"Gas Rebate (70%): {proposal_id}")
bounty_base = 1000
if proposer:
    self._send_reward(treasury, proposer.wallet_address, bounty_base, 0, f"Bounty: {proposal_id}")

# mABC/agents/base/dao_run.py:264,267
opponents = [rec for rec in (vote_records or []) if rec.get("option") == "Against"]
for rec in opponents:
    self._send_penalty(treasury, rec["address"], 50, -1, f"Against Passed: {proposal_id}")

# mABC/agents/base/dao_run.py:370,374,377
treasury = self._get_or_create_treasury_account()
proposer = next((a for a in agents if a.role_name == proposer_role), None)
if proposer:
    self._send_penalty(treasury, proposer.wallet_address, 300, -5, f"Proposal Failed: {proposal_id}")
supporters = [rec for rec in (vote_records or []) if rec.get("option") == "For"]
for rec in supporters:
    self._send_penalty(treasury, rec["address"], 100, -1, f"Support Failed: {proposal_id}")

# mABC/agents/base/dao_run.py:269,284,288,291
success = self.chain_client.send_and_mine(tx, silent=True)
block = self.chain_client.get_latest_block() if success else None
block_index = block.header.index if block else "-"
short_addr = f"{target_address[:6]}...{target_address[-4:]}"
print(f"奖励发送: to={short_addr}, token={amount}, rep={reputation}, success={success}, onchain_block={block_index}")
```
- 系统金库账户
  - 创建或复用金库账户（缓存地址/私钥，初始化余额与信誉），见 `mABC/agents/base/dao_run.py:311`、`mABC/agents/base/dao_run.py:323`、`mABC/agents/base/dao_run.py:325`、`mABC/agents/base/dao_run.py:331`。
  - VM 在出块时将非奖励交易的 Gas 计入金库，失败回滚时从金库扣回，见 `mABC/core/vm.py:153`、`mABC/core/vm.py:165`、`mABC/core/vm.py:179`、`mABC/core/vm.py:185`。
```python
# mABC/agents/base/dao_run.py:311,323,325,331
sk = SigningKey.generate(curve=SECP256k1)
vk = sk.get_verifying_key()
addr = generate_address(vk.to_string())
PublicKeyRegistry.register_public_key(addr, vk.to_string().hex())
acc = world_state.get_account(addr) or world_state.create_account(addr)
if acc.balance is None or acc.balance < 200000:
    acc.balance = 200000
if acc.reputation is None or acc.reputation < 80:
    acc.reputation = 80
if acc.stake is None:
    acc.stake = 0
world_state.update_account(acc)
setattr(self.blockchain, "_treasury_address", addr)
setattr(self.blockchain, "_treasury_private_key", sk)
self._treasury = DAOExecutor.TreasuryAccount(addr, sk)

# mABC/core/vm.py:153,165,179,185
account.balance -= gas_fee
world_state.update_account(account)
treasury = self._get_treasury_account()
if treasury:
    treasury.balance = (treasury.balance or 0) + gas_fee
    world_state.update_account(treasury)
# 回滚分支
account.balance += gas_fee
world_state.update_account(account)
treasury = self._get_treasury_account()
if treasury and (treasury.balance or 0) >= gas_fee:
    treasury.balance -= gas_fee
    world_state.update_account(treasury)
```

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
