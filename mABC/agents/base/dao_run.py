"""
DAO化的Agent执行器
将多智能体投票机制从纯内存操作改造为基于区块链的链上交易模式
"""

import time
from typing import List, Dict, Any
from ecdsa import SigningKey, SECP256k1

from .run import BaseRun
from agents.base.profile import AgentWorkflow
from core.client import ChainClient
from core.blockchain import PublicKeyRegistry
from core.types import generate_address
from core.state import world_state


class DAOExecutor(BaseRun):
    """
    DAO化的Agent执行器，替代 ThreeHotCotRun
    所有投票决策都通过区块链交易执行
    """
    class TreasuryAccount:
        def __init__(self, wallet_address: str, private_key: SigningKey):
            self.wallet_address = wallet_address
            self.private_key = private_key
    
    def __init__(self, blockchain, alpha: float = 0.5, beta: float = 0.5):
        """
        初始化DAO执行器
        
        Args:
            blockchain: Blockchain实例(来自成员2)
            alpha: 支持率阈值(默认0.5，即50%)
            beta: 参与率阈值(默认0.5，即50%)
        """
        super().__init__()
        self.blockchain = blockchain
        self.chain_client = ChainClient(blockchain)  # 使用 ChainClient 封装区块链交互
        self.alpha = alpha
        self.beta = beta
        self.proposal_counter = 0  # 提案ID计数器
    
    def run(self, agents: List[AgentWorkflow], poll_role: str, 
            poll_problem: str, poll_content: str, proposal_id: str = None) -> bool:
        """
        执行DAO投票流程(保持与ThreeHotCotRun相同的接口)
        
        Args:
            agents: 参与投票的Agent列表
            poll_role: 提案发起者的角色名
            poll_problem: 投票的问题
            poll_content: 问题的详细内容
            proposal_id: 外部指定的提案ID(可选)
        
        Returns:
            bool: 提案是否通过
        """
        # 如果禁用了投票(alpha和beta都为-1)，则直接通过
        if self.alpha == -1 and self.beta == -1:
            return True
        
        # 生成提案ID (如果未提供)
        if proposal_id is None:
            proposal_id = f"proposal_{self.proposal_counter}_{int(time.time())}"
            self.proposal_counter += 1
        
        print(f"\n{'='*60}")
        print(f"🗳️  发起DAO投票")
        print(f"提案ID: {proposal_id}")
        print(f"问题: {poll_problem}")
        print(f"发起者: {poll_role}")
        print(f"{'='*60}\n")
        
        # 第一步：检查是否有人发起投票
        poll_initiator = None
        poll_reason = ""
        
        # 更新所有Agent的链上状态和权重
        print(f"🔄 同步Agent链上状态...")
        for agent in agents:
            try:
                account = self.chain_client.get_account(agent.wallet_address)
                if account:
                    # 计算动态权重
                    # 基础权重: 1.0
                    # 信誉加成: (信誉值 - 50) / 10.0 (例如: 80分 -> +3.0权重)
                    # 质押加成: 质押量 / 1000.0 (例如: 1000 Token -> +1.0权重)
                    reputation_bonus = max(0, (account.reputation - 50) / 10.0)
                    stake_bonus = account.stake / 1000.0
                    
                    agent.weight = 1.0 + reputation_bonus + stake_bonus
                    
                    # 同步其他属性用于显示
                    if hasattr(agent, 'reputation'):
                        agent.reputation = account.reputation
                    if hasattr(agent, 'balance'):
                        agent.balance = account.balance
                        
                    print(f"  - {agent.role_name}: 权重={agent.weight:.2f} (信誉={account.reputation}, 质押={account.stake})")
                else:
                    agent.weight = 1.0
                    print(f"  - {agent.role_name}: 账户未找到，使用默认权重 1.0")
            except Exception as e:
                print(f"  - {agent.role_name}: 状态同步失败 ({e})，使用当前权重 {getattr(agent, 'weight', 1.0)}")

        for agent in agents:
            if "Alert Receiver" in getattr(agent, "role_name", ""):
                continue
            # 让每个Agent判断是否要发起投票挑战
            poll_result = self.poll(agent, poll_role, poll_problem, poll_content)
            if poll_result['poll'] == "Yes":
                poll_initiator = agent.role_name
                poll_reason = poll_result['reason']
                print(f"⚠️  {agent.role_name} 发起投票挑战")
                print(f"理由: {poll_reason}\n")
                break
        
        # 如果没人发起投票，仍然进入投票流程(自动发起)
        if poll_initiator is None:
            poll_initiator = poll_role
            poll_reason = "Auto-started voting due to no challenge"
            print("ℹ️ 无人发起挑战，系统自动发起投票以记录决策与发放激励\n")
        
        # 第二步：所有Agent进行链上投票
        print(f"📊 开始链上投票流程...\n")
        
        # 在投票前进行“自动质押”，质押目标基于信誉分并设定上限避免余额被快速消耗
        print(f"🔒 执行自动质押策略以提升高信誉Agent的影响力")
        for agent in agents:
            if "Alert Receiver" in getattr(agent, "role_name", ""):
                continue
            try:
                account = self.chain_client.get_account(agent.wallet_address)
                if not account:
                    continue
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
                    print(f"  - {agent.role_name}: 自动质押 {stake_delta} (信誉={account.reputation}, 余额={account.balance}) => {('✅ 成功' if st_ok else '❌ 失败')}")
            except Exception as e:
                print(f"  - {agent.role_name}: 自动质押异常 ({e})")
        
        total_weight = 0
        vote_weights = {"For": 0, "Against": 0, "Abstain": 0}
        vote_records: List[Dict[str, Any]] = []
        
        for agent in agents:
            if "Alert Receiver" in getattr(agent, "role_name", ""):
                continue
            # 获取Agent的投票选项
            vote_option = self.submit_vote(agent, poll_initiator, poll_reason, 
                                          poll_role, poll_problem, poll_content)
            
            # 创建并提交投票交易
            success = self._create_and_submit_vote_transaction(
                agent, proposal_id, vote_option
            )
            
            if success:
                # 质押后刷新最新权重(信誉+质押)
                try:
                    acc_now = self.chain_client.get_account(agent.wallet_address)
                    if acc_now:
                        reputation_bonus = max(0, (acc_now.reputation - 50) / 10.0)
                        stake_bonus = acc_now.stake / 1000.0
                        agent.weight = 1.0 + reputation_bonus + stake_bonus
                except Exception:
                    pass
                # 计算投票权重(基于Agent的weight属性)
                weight = agent.weight if hasattr(agent, 'weight') else 1.0
                vote_weights[vote_option] += weight
                total_weight += weight
                vote_records.append({
                    "address": agent.wallet_address,
                    "role": agent.role_name,
                    "option": vote_option,
                    "weight": weight
                })
                
                print(f"  {agent.role_name}: {vote_option} (权重: {weight:.2f})")
        
        # 第三步：计算共识结果
        if total_weight == 0:
            print("\n❌ 无有效投票，提案被否决\n")
            return False
        
        support_rate = vote_weights["For"] / total_weight
        participation_rate = (vote_weights["For"] + vote_weights["Against"]) / total_weight
        
        print(f"\n📈 投票结果统计:")
        print(f"  支持: {vote_weights['For']:.2f} ({support_rate*100:.1f}%)")
        print(f"  反对: {vote_weights['Against']:.2f}")
        print(f"  弃权: {vote_weights['Abstain']:.2f}")
        print(f"  参与率: {participation_rate*100:.1f}%")
        print(f"  阈值要求: 支持率≥{self.alpha*100}%, 参与率≥{self.beta*100}%")
        
        # 判断是否通过
        run_result = support_rate >= self.alpha and participation_rate >= self.beta
        
        if run_result:
            print(f"\n✅ 提案通过！\n")
            # 触发奖励机制
            self.distribute_rewards(agents, poll_initiator, vote_weights, proposal_id, vote_records)
        else:
            print(f"\n❌ 提案被否决！\n")
            # 触发惩罚机制
            self.distribute_penalties(agents, poll_initiator, vote_weights, proposal_id, vote_records)
        
        return run_result

    def distribute_rewards(self, agents: List[AgentWorkflow], proposer_role: str, vote_weights: Dict[str, float], proposal_id: str, vote_records: List[Dict[str, Any]]):
        """
        分发奖励
        
        奖励规则:
        1. 提案人 (Proposer): +100 Token, +5 Reputation
        2. 支持者 (Voters for 'For'): +10 Token, +1 Reputation
        
        Args:
            agents: 所有Agent列表
            proposer_role: 提案人角色名
            vote_weights: 投票权重统计
            proposal_id: 提案ID
        """
        print(f"\n🎁 开始分发奖励...")
        treasury = self._get_or_create_treasury_account()
        
        # 2. 奖励提案人
        proposer = next((a for a in agents if a.role_name == proposer_role), None)
        if proposer:
            self._send_reward(treasury, proposer.wallet_address, 800, 5, f"Proposal Passed: {proposal_id}")
            print(f"  - 提案人 {proposer.role_name}: +800 Token, +5 Reputation")
            
        # 3. 奖励支持者(仅对投票为 'For' 的地址发放)
        supporters = [rec for rec in (vote_records or []) if rec.get("option") == "For"]
        for rec in supporters:
            self._send_reward(treasury, rec["address"], 300, 1, f"Voting Support: {proposal_id}")
            print(f"  - 支持者 {rec['role']}: +300 Token, +1 Reputation (W={rec['weight']:.2f})")
        
        # 4. 通过返还支持者的投票Gas 70%
        rebate_ratio = 0.7
        vote_gas_limit = 200
        vote_gas_price = 1
        rebate_amount = int(rebate_ratio * vote_gas_limit * vote_gas_price)
        supporters = [rec for rec in (vote_records or []) if rec.get("option") == "For"]
        for rec in supporters:
            self._send_reward(treasury, rec["address"], rebate_amount, 0, f"Gas Rebate (70%): {proposal_id}")
            print(f"  - 支持者 {rec['role']}: 返还Gas {rebate_amount}")
        
        # 5. 成果赏金基础额发放(给提案人)
        bounty_base = 1000
        if proposer:
            self._send_reward(treasury, proposer.wallet_address, bounty_base, 0, f"Bounty: {proposal_id}")
            print(f"  - 提案人 {proposer.role_name}: 赏金 +{bounty_base} Token")
        
        # 6. 通过时惩罚反对者：小额罚没 + 信誉下降
        opponents = [rec for rec in (vote_records or []) if rec.get("option") == "Against"]
        for rec in opponents:
            self._send_penalty(treasury, rec["address"], 50, -1, f"Against Passed: {proposal_id}")

    def _send_reward(self, admin_agent: AgentWorkflow, target_address: str, amount: int, reputation: int, memo: str):
        """发送奖励交易"""
        try:
            tx = self.chain_client.create_transaction(
                tx_type="reward",
                sender=admin_agent.wallet_address,
                data={
                    "target": target_address,
                    "amount": amount,
                    "reputation": reputation,
                    "memo": memo
                },
                private_key=admin_agent.private_key,
                gas_limit=200
            )
            success = self.chain_client.send_and_mine(tx, silent=True)
            block = self.chain_client.get_latest_block() if success else None
            block_index = block.header.index if block else "-"
            short_addr = f"{target_address[:6]}...{target_address[-4:]}"
            print(f"奖励发送: to={short_addr}, token={amount}, rep={reputation}, success={success}, onchain_block={block_index}")
        except Exception as e:
            short_addr = f"{target_address[:6]}...{target_address[-4:]}"
            print(f"奖励发送: to={short_addr}, token={amount}, rep={reputation}, success=False, onchain_block=-, error={e}")
    
    def _send_penalty(self, admin_agent: AgentWorkflow, target_address: str, amount: int, reputation: int, memo: str):
        try:
            tx = self.chain_client.create_transaction(
                tx_type="penalty",
                sender=admin_agent.wallet_address,
                data={
                    "target": target_address,
                    "amount": amount,
                    "reputation": reputation,
                    "memo": memo
                },
                private_key=admin_agent.private_key,
                gas_limit=200
            )
            self.chain_client.send_and_mine(tx, silent=True)
        except Exception:
            pass
    
    def _get_or_create_treasury_account(self):
        if hasattr(self, "_treasury") and self._treasury:
            return self._treasury
        addr = getattr(self.blockchain, "_treasury_address", None)
        pk = getattr(self.blockchain, "_treasury_private_key", None)
        if addr and pk and world_state.get_account(addr):
            self._treasury = DAOExecutor.TreasuryAccount(addr, pk)
            return self._treasury
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
        return self._treasury
    
    def _create_and_submit_vote_transaction(self, agent: AgentWorkflow, 
                                           proposal_id: str, vote_option: str) -> bool:
        """
        创建投票交易并提交到区块链
        
        Args:
            agent: 投票的Agent
            proposal_id: 提案ID
            vote_option: 投票选项 (For/Against/Abstain)
        
        Returns:
            bool: 交易是否成功提交
        """
        try:
            # 使用 ChainClient 创建并提交交易
            # 投票交易是轻量级操作，gas_limit 设为 5000
            tx = self.chain_client.create_transaction(
                tx_type="vote",
                sender=agent.wallet_address,
                data={
                    "proposal_id": proposal_id,
                    "vote_option": vote_option
                },
                private_key=agent.private_key,
                gas_limit=200
            )
            
            # 提交交易并出块
            return self.chain_client.send_and_mine(tx)
            
        except Exception as e:
            print(f"❌ 创建投票交易失败: {e}")
            return False

    def distribute_penalties(self, agents: List[AgentWorkflow], proposer_role: str, vote_weights: Dict[str, float], proposal_id: str, vote_records: List[Dict[str, Any]]):
        treasury = self._get_or_create_treasury_account()
        proposer = next((a for a in agents if a.role_name == proposer_role), None)
        if proposer:
            self._send_penalty(treasury, proposer.wallet_address, 300, -5, f"Proposal Failed: {proposal_id}")
        supporters = [rec for rec in (vote_records or []) if rec.get("option") == "For"]
        for rec in supporters:
            self._send_penalty(treasury, rec["address"], 100, -1, f"Support Failed: {proposal_id}")
    
    def _sign_transaction(self, tx, private_key: SigningKey) -> str:
        """
        使用ECDSA对交易进行签名
        
        Args:
            tx: 待签名的交易
            private_key: Agent的私钥
        
        Returns:
            签名的十六进制字符串
        """
        # 1. 计算交易哈希(排除signature字段)
        tx_dict = tx.model_dump(exclude={'signature'})
        tx_json = json.dumps(tx_dict, sort_keys=True, separators=(',', ':'))
        tx_hash = hashlib.sha256(tx_json.encode()).digest()
        
        # 2. 使用私钥签名
        signature = private_key.sign_digest(tx_hash, sigencode=sigencode_der)
        
        # 3. 返回十六进制编码
        return signature.hex()
    
    def _submit_and_mine(self, tx) -> bool:
        """
        提交交易并触发出块
        
        Args:
            tx: 待提交的交易
        
        Returns:
            bool: 交易是否成功执行
        """
        # 1. 添加交易到交易池
        success = self.blockchain.add_transaction(tx)
        if not success:
            print(f"❌ 交易提交失败: {tx.sender[:8]}... - {tx.tx_type}")
            return False
        
        # 2. 立即触发出块(模拟环境下)
        block = self.blockchain.mine_block()
        if block is None:
            print("❌ 出块失败")
            return False
        
        print(f"✅ 交易已上链: Block #{block.header.index}")
        return True
    
    def poll(self, agent: AgentWorkflow, poll_role: str, poll_problem: str, 
             poll_content: str) -> Dict[str, str]:
        """
        询问Agent是否要发起投票挑战
        
        Args:
            agent: 被询问的Agent
            poll_role: 提案发起者角色
            poll_problem: 投票问题
            poll_content: 问题详细内容
        
        Returns:
            {"poll": "Yes/No", "reason": "理由"}
        """
        messages = [
            {"role": "system", "content": f"{agent.role_desc}{agent.base_prompt}"},
            {"role": "user", "content": agent.poll_prompt.format(
                poll_role=poll_role, 
                poll_problem=poll_problem, 
                poll_content=poll_content
            )},
        ]
        answer = self.qa(messages, stop_words="")
        result = self._parse_poll(answer)
        return result
    
    def _parse_poll(self, answer: str) -> Dict[str, str]:
        """解析poll结果"""
        result = {"poll": None, "reason": None}
        
        if "Poll:" in answer and "Reason:" in answer:
            result["poll"] = answer.split("Poll:")[1].split("\n")[0].strip()
            result["reason"] = answer.split("Reason:")[1].strip()
        
        # 容错处理
        if result["poll"] not in ["Yes", "No"]:
            if "Yes" in answer:
                result["poll"] = "Yes"
            elif "No" in answer:
                result["poll"] = "No"
            else:
                result["poll"] = "No"  # 默认不发起投票
        
        return result
    
    def submit_vote(self, agent: AgentWorkflow, poll_initiator: str, 
                   poll_reason: str, poll_role: str, poll_problem: str, 
                   poll_content: str) -> str:
        """
        Agent提交投票
        
        Returns:
            投票选项: For/Against/Abstain
        """
        messages = [
            {"role": "system", "content": f"{agent.role_desc}{agent.base_prompt}"},
            {"role": "user", "content": agent.vote_prompt.format(
                poll_initiator=poll_initiator,
                poll_reason=poll_reason,
                poll_role=poll_role,
                poll_problem=poll_problem,
                poll_content=poll_content
            )},
        ]
        answer = self.qa(messages, stop_words="")
        result = self._parse_vote(answer)
        return result
    
    def _parse_vote(self, answer: str) -> str:
        """解析投票结果"""
        result = None
        
        if "Option:" in answer:
            result = answer.split("Option:")[1].split("\n")[0].strip()
        
        # 容错处理
        if result not in ["For", "Against", "Abstain"]:
            if "For" in answer:
                result = "For"
            elif "Against" in answer:
                result = "Against"
            elif "Abstain" in answer:
                result = "Abstain"
            else:
                result = "Abstain"  # 默认弃权
        
        return result
    
    def _stake_tokens(self, agent: AgentWorkflow, amount: int) -> bool:
        """
        Agent质押Token以参与投票
        
        Args:
            agent: 质押的Agent
            amount: 质押金额
        
        Returns:
            bool: 质押是否成功
        """
        if amount <= 0:
            return True  # 不质押也允许
        
        try:
            # 检查余额
            balance = self.chain_client.get_balance(agent.wallet_address)
            if balance < amount:
                print(f"⚠️  {agent.role_name} 余额不足，无法质押")
                return False
            
            # 使用 ChainClient 创建质押交易
            tx = self.chain_client.create_transaction(
                tx_type="stake",
                sender=agent.wallet_address,
                data={"amount": amount},
                private_key=agent.private_key,
                gas_limit=200
            )
            
            # 上链执行
            return self.chain_client.send_and_mine(tx)
            
        except Exception as e:
            print(f"❌ 质押失败: {e}")
            return False
    
    def _calculate_stake_amount(self, agent: AgentWorkflow, 
                               confidence: float) -> int:
        """
        根据Agent的信心度决定质押金额
        
        Args:
            confidence: 0-1之间的信心度
        
        Returns:
            质押金额
        """
        balance = self.chain_client.get_balance(agent.wallet_address)
        
        if confidence > 0.8:
            return int(balance * 0.3)  # 高信心质押30%
        elif confidence > 0.5:
            return int(balance * 0.1)  # 中等信心质押10%
        else:
            return 0  # 低信心不质押(弃权)
