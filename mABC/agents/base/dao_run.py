"""
DAO化的Agent执行器
将多智能体投票机制从纯内存操作改造为基于区块链的链上交易模式
"""

import time
from typing import List, Dict, Any
from ecdsa import SigningKey

from .run import BaseRun
from agents.base.profile import AgentWorkflow
from core.client import ChainClient


class DAOExecutor(BaseRun):
    """
    DAO化的Agent执行器，替代 ThreeHotCotRun
    所有投票决策都通过区块链交易执行
    """
    
    def __init__(self, blockchain, alpha: float = 0.5, beta: float = 0.5):
        """
        初始化DAO执行器
        
        Args:
            blockchain: Blockchain实例（来自成员2）
            alpha: 支持率阈值（默认0.5，即50%）
            beta: 参与率阈值（默认0.5，即50%）
        """
        super().__init__()
        self.blockchain = blockchain
        self.chain_client = ChainClient(blockchain)  # 使用 ChainClient 封装区块链交互
        self.alpha = alpha
        self.beta = beta
        self.proposal_counter = 0  # 提案ID计数器
    
    def run(self, agents: List[AgentWorkflow], poll_role: str, 
            poll_problem: str, poll_content: str) -> bool:
        """
        执行DAO投票流程（保持与ThreeHotCotRun相同的接口）
        
        Args:
            agents: 参与投票的Agent列表
            poll_role: 提案发起者的角色名
            poll_problem: 投票的问题
            poll_content: 问题的详细内容
        
        Returns:
            bool: 提案是否通过
        """
        # 如果禁用了投票（alpha和beta都为-1），则直接通过
        if self.alpha == -1 and self.beta == -1:
            return True
        
        # 生成提案ID
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
        
        for agent in agents:
            # 让每个Agent判断是否要发起投票挑战
            poll_result = self.poll(agent, poll_role, poll_problem, poll_content)
            if poll_result['poll'] == "Yes":
                poll_initiator = agent.role_name
                poll_reason = poll_result['reason']
                print(f"⚠️  {agent.role_name} 发起投票挑战")
                print(f"理由: {poll_reason}\n")
                break
        
        # 如果没人发起投票，默认通过
        if poll_initiator is None:
            print("✅ 无人发起投票，提案默认通过\n")
            return True
        
        # 第二步：所有Agent进行链上投票
        print(f"📊 开始链上投票流程...\n")
        
        total_weight = 0
        vote_weights = {"For": 0, "Against": 0, "Abstain": 0}
        
        for agent in agents:
            # 获取Agent的投票选项
            vote_option = self.submit_vote(agent, poll_initiator, poll_reason, 
                                          poll_role, poll_problem, poll_content)
            
            # 创建并提交投票交易
            success = self._create_and_submit_vote_transaction(
                agent, proposal_id, vote_option
            )
            
            if success:
                # 计算投票权重（基于Agent的weight属性）
                weight = agent.weight if hasattr(agent, 'weight') else 1.0
                vote_weights[vote_option] += weight
                total_weight += weight
                
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
        else:
            print(f"\n❌ 提案被否决！\n")
        
        return run_result
    
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
            tx = self.chain_client.create_transaction(
                tx_type="vote",
                sender=agent.wallet_address,
                data={
                    "proposal_id": proposal_id,
                    "vote_option": vote_option
                },
                private_key=agent.private_key
            )
            
            # 提交交易并出块
            return self.chain_client.send_and_mine(tx)
            
        except Exception as e:
            print(f"❌ 创建投票交易失败: {e}")
            return False
    
    def _sign_transaction(self, tx, private_key: SigningKey) -> str:
        """
        使用ECDSA对交易进行签名
        
        Args:
            tx: 待签名的交易
            private_key: Agent的私钥
        
        Returns:
            签名的十六进制字符串
        """
        # 1. 计算交易哈希（排除signature字段）
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
        
        # 2. 立即触发出块（模拟环境下）
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
                private_key=agent.private_key
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
            return 0  # 低信心不质押（弃权）
