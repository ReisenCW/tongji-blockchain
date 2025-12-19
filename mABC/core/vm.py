"""
虚拟机执行层
实现一个简易的状态机执行引擎，用于处理交易并更新状态
增强Gas机制实现
"""

import hashlib
import json
import time
from typing import Dict, Any, Optional, List
from ecdsa import SigningKey, VerifyingKey, SECP256k1
from ecdsa.util import sigencode_der, sigdecode_der
from pydantic import BaseModel, Field
from .state import world_state, state_processor, Account


class TransactionType:
    """交易类型常量"""
    PROPOSE_ROOT_CAUSE = "propose_root_cause"
    VOTE = "vote"
    TRANSFER = "transfer"


class Transaction(BaseModel):
    """交易模型"""
    tx_type: str
    sender: str
    nonce: int
    gas_price: int
    gas_limit: int
    data: Dict[str, Any]
    signature: Optional[str] = None
    timestamp: int = Field(default_factory=lambda: int(time.time()))


class TransactionReceipt(BaseModel):
    """交易收据"""
    tx_hash: str
    success: bool
    gas_used: int
    gas_fee: int
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class GasCalculator:
    """Gas计算器"""
    
    # 基础Gas消耗
    BASE_GAS = 21000
    # 不同操作的Gas消耗
    GAS_COSTS = {
        TransactionType.TRANSFER: 21000,
        TransactionType.PROPOSE_ROOT_CAUSE: 30000,
        TransactionType.VOTE: 25000
    }
    
    @classmethod
    def calculate_gas_cost(cls, tx_type: str) -> int:
        """计算交易的Gas消耗"""
        return cls.GAS_COSTS.get(tx_type, cls.BASE_GAS)


class Block(BaseModel):
    """区块模型"""
    index: int
    timestamp: int
    transactions: List[Transaction]
    previous_hash: str
    nonce: int = 0
    hash: Optional[str] = None


class Blockchain:
    """区块链类，负责交易池管理和挖矿出块"""
    
    def __init__(self):
        self.pending_transactions: List[Transaction] = []
        self.chain: List[Block] = []
        self.gas_price = 1  # 每单位Gas的价格
        self.min_gas_limit = 21000  # 最小Gas限制
        # 创建创世区块
        self._create_genesis_block()
    
    def _create_genesis_block(self):
        """创建创世区块"""
        genesis_block = Block(
            index=0,
            timestamp=int(time.time()),
            transactions=[],
            previous_hash="0" * 64
        )
        genesis_block.hash = self._calculate_block_hash(genesis_block)
        self.chain.append(genesis_block)
        print("Genesis block created")
    
    def _calculate_block_hash(self, block: Block) -> str:
        """计算区块哈希"""
        block_dict = block.dict(exclude={'hash'})
        block_json = json.dumps(block_dict, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(block_json.encode()).hexdigest()
    
    def add_transaction(self, tx: Transaction) -> bool:
        """
        添加交易到交易池
        根据接口文档要求实现
        """
        # 1. 验证交易签名
        if not self._verify_transaction_signature(tx):
            print("Invalid transaction signature")
            return False
        
        # 2. 检查Nonce防止重放
        account = world_state.get_account(tx.sender)
        if account and tx.nonce != account.nonce:
            print(f"Invalid nonce. Expected {account.nonce}, got {tx.nonce}")
            return False
        
        # 3. 检查Gas限制
        if tx.gas_limit < self.min_gas_limit:
            print(f"Gas limit too low. Minimum is {self.min_gas_limit}")
            return False
        
        # 4. 检查发送者余额
        required_gas = tx.gas_price * tx.gas_limit
        if account and account.balance < required_gas:
            print(f"Insufficient balance. Required {required_gas}, available {account.balance}")
            return False
        
        # 交易验证通过，加入待打包交易池
        self.pending_transactions.append(tx)
        print(f"Transaction added to pending pool: {tx.tx_type}")
        return True
    
    def mine_block(self) -> Optional[Block]:
        """
        挖矿/出块
        根据接口文档要求实现
        """
        if not self.pending_transactions:
            print("No pending transactions to mine")
            return None
        
        # 从池中取出交易
        transactions_to_mine = self.pending_transactions.copy()
        self.pending_transactions.clear()
        
        # 创建新区块
        previous_block = self.chain[-1]
        new_block = Block(
            index=previous_block.index + 1,
            timestamp=int(time.time()),
            transactions=transactions_to_mine,
            previous_hash=previous_block.hash or ""
        )
        
        # 调用StateProcessor执行交易
        successful_transactions = []
        for tx in transactions_to_mine:
            # 执行交易前先扣除Gas费用
            gas_fee = tx.gas_price * tx.gas_limit
            account = world_state.get_account(tx.sender)
            if not account:
                account = world_state.create_account(tx.sender)
            
            if account.balance >= gas_fee:
                account.balance -= gas_fee
                world_state.update_account(account)
                
                # 调用StateProcessor应用交易
                if state_processor.apply_transaction(tx):
                    successful_transactions.append(tx)
                    # 增加nonce
                    world_state.increment_nonce(tx.sender)
                else:
                    print(f"Failed to apply transaction: {tx.tx_type}")
                    # 退还Gas费用
                    account.balance += gas_fee
                    world_state.update_account(account)
            else:
                print(f"Insufficient balance for gas fee: {tx.sender}")
        
        # 更新区块的交易列表为成功执行的交易
        new_block.transactions = successful_transactions
        
        # 计算区块哈希
        new_block.hash = self._calculate_block_hash(new_block)
        
        # 将合法区块追加到链上
        self.chain.append(new_block)
        print(f"New block mined: #{new_block.index} with {len(successful_transactions)} transactions")
        
        return new_block
    
    def _verify_transaction_signature(self, tx: Transaction) -> bool:
        """验证交易签名"""
        if not tx.signature:
            return False
        
        try:
            # 获取发送者的公钥（这里简化处理，实际应从地址推导公钥）
            # 在实际实现中，应该从tx.sender地址推导出公钥
            # 这里为了简化，我们假设tx.sender就是公钥
            vk = VerifyingKey.from_string(bytes.fromhex(tx.sender), curve=SECP256k1)
            
            # 计算交易哈希
            tx_dict = tx.dict(exclude={'signature'})
            tx_json = json.dumps(tx_dict, sort_keys=True, separators=(',', ':'))
            tx_hash = hashlib.sha256(tx_json.encode()).hexdigest()
            
            # 验证签名
            return vk.verify(
                bytes.fromhex(tx.signature), 
                bytes.fromhex(tx_hash), 
                sigdecode=sigdecode_der
            )
        except Exception as e:
            print(f"Signature verification failed: {e}")
            return False


# 单例模式的区块链实例
blockchain = Blockchain()