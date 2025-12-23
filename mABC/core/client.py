"""
ChainClient - 区块链客户端
封装 Agent 与区块链的所有交互逻辑
"""

import json
import hashlib
from typing import Optional, Dict, Any, List
from ecdsa import SigningKey
from ecdsa.util import sigencode_der

from core.types import Transaction, Block
from core.state import world_state


class ChainClient:
    """
    区块链客户端
    为 Agent 提供与区块链交互的高层接口
    """
    
    def __init__(self, blockchain):
        """
        初始化区块链客户端
        
        Args:
            blockchain: Blockchain 实例（成员2提供）
        """
        self.blockchain = blockchain
    
    def send_transaction(self, tx: Transaction) -> bool:
        """
        发送交易到区块链
        
        Args:
            tx: 已签名的交易对象
        
        Returns:
            bool: 交易是否成功添加到交易池
        """
        return self.blockchain.add_transaction(tx)
    
    def mine_block(self) -> Optional[Block]:
        """
        触发出块（打包当前交易池中的交易）
        
        Returns:
            Optional[Block]: 新生成的区块，如果没有待处理交易则返回 None
        """
        return self.blockchain.mine_block()
    
    def send_and_mine(self, tx: Transaction, silent: bool = False) -> bool:
        """
        发送交易并立即触发出块（适用于测试/开发环境）
        
        Args:
            tx: 已签名的交易对象
        
        Returns:
            bool: 交易是否成功上链
        """
        # 1. 提交交易到交易池
        if not self.send_transaction(tx):
            if not silent:
                print(f"❌ 交易提交失败: {tx.tx_type}")
            return False
        
        # 2. 立即触发出块
        block = self.mine_block()
        if block is None:
            if not silent:
                print("❌ 出块失败")
            return False
        if not silent:
            print(f"✅ 交易已上链: Block #{block.header.index}, TX: {tx.tx_type}")
        return True
    
    def get_account(self, address: str):
        """
        查询账户信息
        
        Args:
            address: 账户地址
        
        Returns:
            Account: 账户对象，如果不存在则返回 None
        """
        return world_state.get_account(address)
    
    def get_balance(self, address: str) -> int:
        """
        查询账户余额
        
        Args:
            address: 账户地址
        
        Returns:
            int: 账户余额（Token数量）
        """
        account = self.get_account(address)
        return account.balance if account else 0
    
    def get_stake(self, address: str) -> int:
        """
        查询账户质押金额
        
        Args:
            address: 账户地址
        
        Returns:
            int: 质押金额
        """
        account = self.get_account(address)
        return account.stake if account else 0
    
    def get_block_height(self) -> int:
        """
        获取当前区块链高度
        
        Returns:
            int: 区块数量
        """
        return len(self.blockchain.chain)
    
    def get_latest_block(self) -> Optional[Block]:
        """
        获取最新区块
        
        Returns:
            Optional[Block]: 最新的区块
        """
        if len(self.blockchain.chain) > 0:
            return self.blockchain.chain[-1]
        return None
    
    def get_block(self, index: int) -> Optional[Block]:
        """
        根据索引获取区块
        
        Args:
            index: 区块索引（从0开始）
        
        Returns:
            Optional[Block]: 区块对象，如果索引无效则返回 None
        """
        if 0 <= index < len(self.blockchain.chain):
            return self.blockchain.chain[index]
        return None
    
    def get_pending_transactions(self) -> List[Transaction]:
        """
        获取待处理的交易列表
        
        Returns:
            List[Transaction]: 交易池中的所有交易
        """
        return self.blockchain.pending_transactions.copy()
    
    def sign_transaction(self, tx: Transaction, private_key: SigningKey) -> str:
        """
        使用 ECDSA 对交易进行签名
        
        Args:
            tx: 待签名的交易
            private_key: ECDSA 私钥
        
        Returns:
            str: 签名的十六进制字符串
        """
        # 1. 计算交易哈希（排除 signature 字段）
        tx_dict = tx.model_dump(exclude={'signature'})
        tx_json = json.dumps(tx_dict, sort_keys=True, separators=(',', ':'))
        
        # 使用成员1的哈希函数（与 vm.py 验证逻辑保持一致）
        from .types import calculate_hash
        tx_hash = calculate_hash(tx_json)
        
        # 2. 使用私钥签名（tx_hash 是十六进制字符串，需要转为字节）
        signature = private_key.sign_digest(bytes.fromhex(tx_hash), sigencode=sigencode_der)
        
        # 3. 返回十六进制编码
        return signature.hex()
    
    def create_transaction(self, 
                          tx_type: str,
                          sender: str,
                          data: Dict[str, Any],
                          private_key: SigningKey,
                          gas_price: int = 1,
                          gas_limit: int = 200) -> Transaction:
        """
        创建并签名一个交易
        
        Args:
            tx_type: 交易类型（vote, stake, transfer等）
            sender: 发送者地址
            data: 交易数据
            private_key: 发送者私钥
            gas_price: Gas 价格（默认1）
            gas_limit: Gas 限制（默认5000）
        
        Returns:
            Transaction: 已签名的交易对象
        """
        # 获取发送者账户的 nonce
        account = self.get_account(sender)
        if account is None:
            raise ValueError(f"账户不存在: {sender}")
        
        # 创建交易对象
        tx = Transaction(
            tx_type=tx_type,
            sender=sender,
            nonce=account.nonce,
            gas_price=gas_price,
            gas_limit=gas_limit,
            data=data,
            signature=""
        )
        
        # 签名
        tx.signature = self.sign_transaction(tx, private_key)
        
        return tx
    
    def wait_for_receipt(self, tx_hash: str, timeout: int = 30) -> Optional[Dict]:
        """
        等待交易回执（用于异步场景）
        
        注意：当前实现是同步的，此方法主要用于API兼容性
        
        Args:
            tx_hash: 交易哈希
            timeout: 超时时间（秒）
        
        Returns:
            Optional[Dict]: 交易回执
        """
        # TODO: 实现异步等待逻辑
        # 当前版本由于是即时出块，可以直接返回最新区块信息
        latest_block = self.get_latest_block()
        if latest_block:
            return {
                "block_number": latest_block.header.index,
                "block_hash": latest_block.hash,
                "success": True
            }
        return None
    
    def get_events(self, contract_name: str = "ops_contract", 
                   event_name: Optional[str] = None,
                   limit: int = 50) -> List[Dict]:
        """
        从智能合约获取事件日志
        
        Args:
            contract_name: 合约名称（默认为 ops_contract）
            event_name: 事件名称（可选，用于过滤）
            limit: 返回的最大事件数量
        
        Returns:
            List[Dict]: 事件列表
        """
        # 导入合约（避免循环依赖）
        if contract_name == "ops_contract":
            from contracts.ops_contract import ops_sop_contract
            events = ops_sop_contract.get_events(limit=limit)
            
            # 如果指定了事件名称，进行过滤
            if event_name:
                events = [e for e in events if e.get("name") == event_name]
            
            return events
        
        return []
    
    def check_consensus(self, proposal_id: str) -> Optional[Dict]:
        """
        检查提案的共识结果
        
        Args:
            proposal_id: 提案ID
        
        Returns:
            Optional[Dict]: 共识结果，包含 passed、votes_for 等信息
        """
        events = self.get_events(event_name="ConsensusReached", limit=20)
        
        # 查找对应提案的共识结果
        for event in reversed(events):
            if event.get("proposal_id") == proposal_id:
                return {
                    "passed": event.get("passed", False),
                    "votes_for": event.get("votes_for", 0),
                    "votes_against": event.get("votes_against", 0),
                    "votes_abstain": event.get("votes_abstain", 0)
                }
        
        return None
    
    def get_blockchain_info(self) -> Dict[str, Any]:
        """
        获取区块链的整体信息
        
        Returns:
            Dict: 包含区块高度、待处理交易数等信息
        """
        return {
            "block_height": self.get_block_height(),
            "pending_transactions": len(self.get_pending_transactions()),
            "latest_block_hash": self.get_latest_block().hash if self.get_latest_block() else None,
            "chain_id": "mABC-DAO-Chain"
        }
    
    def __repr__(self) -> str:
        return f"<ChainClient: height={self.get_block_height()}, pending={len(self.get_pending_transactions())}>"
