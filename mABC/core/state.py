"""
状态管理模块
负责维护全局状态 (World State)，确保数据的一致性
"""

import hashlib
import json
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class Account(BaseModel):
    """账户模型 - 符合接口文档中成员1的数据定义职责"""
    address: str
    balance: int = 0
    nonce: int = 0
    root_cause_proposals: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    votes: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    analyses: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    staked_amount: int = 0


class WorldState:
    """世界状态管理器"""
    
    def __init__(self, db_path: str = "state.db"):
        self.db_path = db_path
        self.state: Dict[str, Account] = {}
        self._load_state()
    
    def _load_state(self):
        """从数据库加载状态"""
        try:
            # 简化的内存状态管理，实际项目中可以使用LevelDB或SQLite
            print("Loading state from memory...")
        except Exception as e:
            print(f"Failed to load state: {e}")
    
    def _save_state(self):
        """保存状态到数据库"""
        try:
            # 简化的内存状态管理，实际项目中可以使用LevelDB或SQLite
            print("Saving state to memory...")
        except Exception as e:
            print(f"Failed to save state: {e}")
    
    def get_account(self, address: str) -> Optional[Account]:
        """获取账户信息"""
        return self.state.get(address)
    
    def create_account(self, address: str) -> Account:
        """创建新账户"""
        if address not in self.state:
            self.state[address] = Account(address=address)
            self._save_state()
        return self.state[address]
    
    def update_account(self, account: Account):
        """更新账户信息"""
        self.state[account.address] = account
        self._save_state()
    
    def get_balance(self, address: str) -> int:
        """获取账户余额"""
        account = self.get_account(address)
        return account.balance if account else 0
    
    def transfer_balance(self, from_address: str, to_address: str, amount: int) -> bool:
        """转账"""
        from_account = self.get_account(from_address)
        to_account = self.get_account(to_address)
        
        if not from_account or from_account.balance < amount:
            return False
        
        if not to_account:
            to_account = self.create_account(to_address)
        
        from_account.balance -= amount
        to_account.balance += amount
        
        self.update_account(from_account)
        self.update_account(to_account)
        return True
    
    def increment_nonce(self, address: str) -> int:
        """增加账户nonce"""
        account = self.get_account(address)
        if not account:
            account = self.create_account(address)
        
        account.nonce += 1
        self.update_account(account)
        return account.nonce
    
    def add_root_cause_proposal(self, proposer: str, proposal_id: str, proposal_data: Dict[str, Any]):
        """添加根因提案"""
        account = self.get_account(proposer)
        if not account:
            account = self.create_account(proposer)
        
        account.root_cause_proposals[proposal_id] = proposal_data
        self.update_account(account)
    
    def add_vote(self, voter: str, proposal_id: str, vote_data: Dict[str, Any]):
        """添加投票"""
        account = self.get_account(voter)
        if not account:
            account = self.create_account(voter)
        
        account.votes[proposal_id] = vote_data
        self.update_account(account)
    
    def add_analysis(self, proposer: str, analysis_id: str, analysis_data: Dict[str, Any]):
        """添加分析报告"""
        account = self.get_account(proposer)
        if not account:
            account = self.create_account(proposer)
        
        account.analyses[analysis_id] = analysis_data
        self.update_account(account)
    
    def get_all_proposals(self) -> Dict[str, Dict[str, Any]]:
        """获取所有根因提案"""
        all_proposals = {}
        for account in self.state.values():
            all_proposals.update(account.root_cause_proposals)
        return all_proposals
    
    def get_proposal_votes(self, proposal_id: str) -> Dict[str, Dict[str, Any]]:
        """获取特定提案的所有投票"""
        proposal_votes = {}
        for account in self.state.values():
            if proposal_id in account.votes:
                proposal_votes[account.address] = account.votes[proposal_id]
        return proposal_votes


# 单例模式的世界状态实例
world_state = WorldState()