"""
区块链核心模块
实现区块链的主链维护逻辑，确保区块哈希链接的正确性
"""

import json
import time
from typing import List, Optional
from .types import Block, Transaction, Account, calculate_hash, get_merkle_root


class PublicKeyRegistry:
    """公钥注册表，根据账户地址查找对应的公钥"""
    
    # 简单的内存存储，实际项目中应该使用持久化存储
    _registry: dict = {}
    
    @classmethod
    def register_public_key(cls, address: str, public_key: str) -> None:
        """
        注册公钥
        
        Args:
            address: 账户地址
            public_key: 公钥
        """
        cls._registry[address] = public_key
    
    @classmethod
    def get_public_key(cls, address: str) -> Optional[str]:
        """
        根据账户地址查找对应的公钥
        
        Args:
            address: 账户地址
            
        Returns:
            str: 公钥，如果未找到则返回None
        """
        return cls._registry.get(address)


class Blockchain:
    """区块链类，维护主链"""
    
    def __init__(self):
        self.chain: List[Block] = []
        self._create_genesis_block()
    
    def _create_genesis_block(self) -> None:
        """创建创世区块"""
        # 创世区块的previous_hash为全0
        genesis_header = {
            "index": 0,
            "timestamp": int(time.time()),
            "previous_hash": "0" * 64,
            "merkle_root": calculate_hash(""),
            "nonce": 0
        }
        
        genesis_block = Block(
            header=genesis_header,
            transactions=[]
        )
        
        # 计算区块哈希
        genesis_block.hash = self._calculate_block_hash(genesis_block)
        self.chain.append(genesis_block)
    
    def _calculate_block_hash(self, block: Block) -> str:
        """
        计算区块哈希
        
        Args:
            block: 区块对象
            
        Returns:
            str: 区块哈希值
        """
        # 将区块头转换为字符串进行哈希计算
        header_dict = block.header.model_dump()
        header_json = json.dumps(header_dict, sort_keys=True, separators=(',', ':'))
        return calculate_hash(header_json)
    
    def add_block(self, block: Block) -> bool:
        """
        将区块添加到区块链中
        
        Args:
            block: 要添加的区块
            
        Returns:
            bool: 添加成功返回True，否则返回False
        """
        # 验证区块的previous_hash是否与链上最后一个区块的哈希匹配
        previous_block = self.chain[-1]
        if block.header.previous_hash != previous_block.hash:
            print("Invalid previous hash")
            return False
        
        # 验证区块哈希
        if block.hash != self._calculate_block_hash(block):
            print("Invalid block hash")
            return False
        
        # 验证Merkle根
        calculated_merkle_root = get_merkle_root(block.transactions)
        if block.header.merkle_root != calculated_merkle_root:
            print("Invalid Merkle root")
            return False
        
        # 区块验证通过，添加到链上
        self.chain.append(block)
        return True
    
    def get_latest_block(self) -> Block:
        """
        获取最新的区块
        
        Returns:
            Block: 最新的区块
        """
        return self.chain[-1]
    
    def is_valid_chain(self) -> bool:
        """
        验证整个区块链的有效性
        
        Returns:
            bool: 验证通过返回True，否则返回False
        """
        # 从第二个区块开始验证（跳过创世区块）
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            
            # 验证区块哈希
            if current_block.hash != self._calculate_block_hash(current_block):
                print(f"Invalid hash at block {i}")
                return False
            
            # 验证previous_hash链接
            if current_block.header.previous_hash != previous_block.hash:
                print(f"Invalid previous hash at block {i}")
                return False
            
            # 验证Merkle根
            calculated_merkle_root = get_merkle_root(current_block.transactions)
            if current_block.header.merkle_root != calculated_merkle_root:
                print(f"Invalid Merkle root at block {i}")
                return False
        
        return True