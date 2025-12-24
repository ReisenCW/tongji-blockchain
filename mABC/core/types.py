"""
数据结构定义模块
实现 Block (区块)、Transaction (交易)、Account (账户) 类
"""

import time
import hashlib
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class TransactionType:
    """交易类型常量"""
    PROPOSE_ROOT_CAUSE = "propose_root_cause"
    VOTE = "vote"
    TRANSFER = "transfer"
    STAKE = "stake"
    SLASH = "slash"


class Transaction(BaseModel):
    """交易模型"""
    tx_type: str
    sender: str  # 发送者地址
    nonce: int
    gas_price: int
    gas_limit: int
    data: Dict[str, Any]
    signature: Optional[str] = None
    timestamp: int = Field(default_factory=lambda: int(time.time()))


class BlockHeader(BaseModel):
    """区块头"""
    index: int
    timestamp: int
    previous_hash: str
    merkle_root: str
    nonce: int = 0


class Block(BaseModel):
    """区块模型"""
    header: BlockHeader
    transactions: List[Transaction]
    hash: Optional[str] = None


class Account(BaseModel):
    """账户模型"""
    address: str
    name: str = ''
    balance: int = 0
    stake: int = 0          # 质押, 质押量越高，投票对提案结果的影响力越大
    reputation: int = 100   # 信誉分
    nonce: int = 0
    root_cause_proposals: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    votes: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


def calculate_hash(data: str) -> str:
    """
    计算SHA256哈希值
    
    Args:
        data: 要计算哈希的字符串数据
        
    Returns:
        str: SHA256哈希值的十六进制表示
    """
    return hashlib.sha256(data.encode()).hexdigest()


def get_merkle_root(transactions: List[Transaction]) -> str:
    """
    计算交易列表的Merkle树根哈希
    
    Args:
        transactions: 交易列表
        
    Returns:
        str: Merkle树根哈希值
    """
    if not transactions:
        return calculate_hash("")
    
    # 计算每笔交易的哈希值
    transaction_hashes = []
    for tx in transactions:
        # 将交易转换为字符串进行哈希计算
        tx_dict = tx.model_dump()
        tx_json = str(sorted(tx_dict.items()))
        transaction_hashes.append(calculate_hash(tx_json))
    
    # 构建Merkle树
    merkle_tree = transaction_hashes[:]
    
    while len(merkle_tree) > 1:
        # 如果是奇数个节点，在末尾复制最后一个节点
        if len(merkle_tree) % 2 == 1:
            merkle_tree.append(merkle_tree[-1])
        
        # 计算上一层节点
        new_level = []
        for i in range(0, len(merkle_tree), 2):
            # 将相邻两个节点的哈希值拼接后计算哈希
            combined = merkle_tree[i] + merkle_tree[i + 1]
            new_level.append(calculate_hash(combined))
        merkle_tree = new_level
    
    return merkle_tree[0]


def generate_address(public_key: bytes) -> str:
    """
    根据公钥生成账户地址
    
    Args:
        public_key: 公钥字节串
        
    Returns:
        str: 账户地址
    """
    # 使用SHA256哈希公钥，然后取前20个字节作为地址
    sha256_hash = hashlib.sha256(public_key).digest()
    # 取前20个字节并转换为十六进制字符串
    address = sha256_hash[:20].hex()
    return address