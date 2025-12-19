"""
状态管理模块
负责维护全局状态 (World State)，确保数据的一致性，实现持久化存储功能
"""

import hashlib
import json
import sqlite3
import os
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class Account(BaseModel):
    """账户模型"""
    address: str
    balance: int = 0
    nonce: int = 0
    root_cause_proposals: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    votes: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class WorldState:
    """世界状态管理器"""
    
    def __init__(self, db_path: str = "state.db"):
        self.db_path = db_path
        self.state: Dict[str, Account] = {}
        self._init_db()
        self._load_state()
    
    def _get_db_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('PRAGMA foreign_keys = ON')
        return conn
    
    def _init_db(self):
        """初始化数据库"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # 创建账户表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS accounts (
                    address TEXT PRIMARY KEY,
                    balance INTEGER,
                    nonce INTEGER,
                    root_cause_proposals TEXT,
                    votes TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            print(f"Database initialized at {self.db_path}")
        except Exception as e:
            print(f"Failed to initialize database: {e}")
    
    def _load_state(self):
        """从数据库加载状态"""
        try:
            # 确保数据库已初始化
            self._init_db()
            
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT address, balance, nonce, root_cause_proposals, votes FROM accounts')
            rows = cursor.fetchall()
            
            for row in rows:
                address, balance, nonce, proposals_json, votes_json = row
                # 处理可能的None值
                proposals = json.loads(proposals_json) if proposals_json else {}
                votes = json.loads(votes_json) if votes_json else {}
                
                account = Account(
                    address=address,
                    balance=balance or 0,
                    nonce=nonce or 0,
                    root_cause_proposals=proposals,
                    votes=votes
                )
                self.state[address] = account
            
            conn.close()
            print(f"Loaded {len(self.state)} accounts from database")
        except Exception as e:
            print(f"Failed to load state from database: {e}")
    
    def _save_state(self):
        """保存状态到数据库"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # 插入或更新所有账户
            for account in self.state.values():
                proposals_json = json.dumps(account.root_cause_proposals)
                votes_json = json.dumps(account.votes)
                
                cursor.execute('''
                    INSERT OR REPLACE INTO accounts 
                    (address, balance, nonce, root_cause_proposals, votes)
                    VALUES (?, ?, ?, ?, ?)
                ''', (account.address, account.balance, account.nonce, proposals_json, votes_json))
            
            conn.commit()
            conn.close()
            print("State saved to database")
        except Exception as e:
            print(f"Failed to save state to database: {e}")
    
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
    
    def increment_nonce(self, address: str) -> int:
        """增加账户nonce"""
        account = self.get_account(address)
        if not account:
            account = self.create_account(address)
        
        account.nonce += 1
        self.update_account(account)
        return account.nonce


class StateProcessor:
    """状态处理器，用于应用交易更新世界状态"""
    
    def __init__(self, world_state: WorldState):
        self.world_state = world_state
    
    def apply_transaction(self, tx: 'Transaction') -> bool:
        """
        应用交易到世界状态
        """
        try:
            # 根据交易类型执行不同的操作
            if tx.tx_type == "propose_root_cause":
                return self._apply_propose_root_cause(tx)
            elif tx.tx_type == "vote":
                return self._apply_vote(tx)
            elif tx.tx_type == "transfer":
                return self._apply_transfer(tx)
            else:
                print(f"Unknown transaction type: {tx.tx_type}")
                return False
        except Exception as e:
            print(f"Failed to apply transaction: {e}")
            return False
    
    def _apply_propose_root_cause(self, tx: 'Transaction') -> bool:
        """应用根因提案交易"""
        try:
            proposal_id = hashlib.sha256(
                f"{tx.sender}{tx.timestamp}{tx.data['proposal_content']}".encode()
            ).hexdigest()
            
            proposal_data = {
                "proposer": tx.sender,
                "content": tx.data["proposal_content"],
                "timestamp": tx.timestamp,
                "votes": {
                    "for": 0,
                    "against": 0,
                    "abstain": 0
                }
            }
            
            # 将提案添加到提议者账户中
            account = self.world_state.get_account(tx.sender)
            if not account:
                account = self.world_state.create_account(tx.sender)
            
            account.root_cause_proposals[proposal_id] = proposal_data
            self.world_state.update_account(account)
            return True
        except Exception as e:
            print(f"Failed to apply propose root cause transaction: {e}")
            return False
    
    def _apply_vote(self, tx: 'Transaction') -> bool:
        """应用投票交易"""
        try:
            proposal_id = tx.data["proposal_id"]
            vote_option = tx.data["vote_option"].lower()
            
            # 验证投票选项
            valid_options = ["for", "against", "abstain"]
            if vote_option not in valid_options:
                raise ValueError(f"Invalid vote option. Must be one of {valid_options}")
            
            # 查找提案
            # 遍历所有账户来查找提案
            proposal_account = None
            proposal_data = None
            for account in self.world_state.state.values():
                if proposal_id in account.root_cause_proposals:
                    proposal_account = account
                    proposal_data = account.root_cause_proposals[proposal_id]
                    break
            
            if not proposal_data:
                raise ValueError(f"Proposal {proposal_id} not found")
            
            # 添加投票到投票者账户
            voter_account = self.world_state.get_account(tx.sender)
            if not voter_account:
                voter_account = self.world_state.create_account(tx.sender)
            
            vote_data = {
                "proposal_id": proposal_id,
                "vote_option": vote_option,
                "timestamp": tx.timestamp
            }
            
            voter_account.votes[proposal_id] = vote_data
            self.world_state.update_account(voter_account)
            
            # 更新提案的投票计数
            proposal_data["votes"][vote_option] += 1
            
            # 更新提案账户
            if proposal_account:
                proposal_account.root_cause_proposals[proposal_id] = proposal_data
                self.world_state.update_account(proposal_account)
            
            return True
        except Exception as e:
            print(f"Failed to apply vote transaction: {e}")
            return False
    
    def _apply_transfer(self, tx: 'Transaction') -> bool:
        """应用转账交易"""
        try:
            to_address = tx.data["to"]
            amount = tx.data["amount"]
            
            # 执行转账
            from_account = self.world_state.get_account(tx.sender)
            to_account = self.world_state.get_account(to_address)
            
            if not from_account or from_account.balance < amount:
                return False
            
            if not to_account:
                to_account = self.world_state.create_account(to_address)
            
            from_account.balance -= amount
            to_account.balance += amount
            
            self.world_state.update_account(from_account)
            self.world_state.update_account(to_account)
            return True
        except Exception as e:
            print(f"Failed to apply transfer transaction: {e}")
            return False


# 单例模式的世界状态实例
world_state = WorldState()
# 单例模式的状态处理器实例
state_processor = StateProcessor(world_state)