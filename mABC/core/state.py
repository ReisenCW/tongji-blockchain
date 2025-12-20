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
from types import Account
from core.types import Transaction

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
                    stake INTEGER,
                    reputation INTEGER,
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
            
            cursor.execute('SELECT address, balance, stake, reputation, nonce, root_cause_proposals, votes FROM accounts')
            rows = cursor.fetchall()
            
            for row in rows:
                address, balance, stake, reputation, nonce, proposals_json, votes_json = row
                # 处理可能的None值
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
                    (address, balance, stake, reputation, nonce, root_cause_proposals, votes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (account.address, account.balance, account.stake, account.reputation, account.nonce, proposals_json, votes_json))
            
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
            elif tx.tx_type == "stake":
                return self._apply_stake(tx)
            elif tx.tx_type == "slash":
                return self._apply_slash(tx)
            else:
                print(f"Unknown transaction type: {tx.tx_type}")
                return False
        except Exception as e:
            print(f"Failed to apply transaction: {e}")
            return False
    
    def _apply_propose_root_cause(self, tx: 'Transaction') -> bool:
        """应用根因提案交易"""
        try:
            # 使用成员1提供的哈希函数
            from core.types import calculate_hash
            proposal_id = calculate_hash(
                f"{tx.sender}{tx.timestamp}{tx.data['proposal_content']}"
            )
            
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
    
    # 使用governance_contract处理投票
    def _apply_vote(self, tx: 'Transaction') -> bool:
        """应用投票交易"""
        try:
            from contracts.governance_contract import GovernanceContract
            governance_contract = GovernanceContract(self.world_state)
            return governance_contract.vote(tx.data, tx.sender, tx.timestamp)
        except Exception as e:
            print(f"Failed to apply vote transaction: {e}")
            return False
    
    # 使用token_contract处理转账、质押和惩罚
    def _apply_transfer(self, tx: 'Transaction') -> bool:
        """应用转账交易"""
        try:
            from contracts.token_contract import TokenContract
            token_contract = TokenContract(self.world_state)
            return token_contract.transfer(tx.data, tx.sender)
        except Exception as e:
            print(f"Failed to apply transfer transaction: {e}")
            return False

    def _apply_stake(self, tx: 'Transaction') -> bool:
        """应用质押交易"""
        try:
            from contracts.token_contract import TokenContract
            token_contract = TokenContract(self.world_state)
            return token_contract.stake(tx.data, tx.sender)
        except Exception as e:
            print(f"Failed to apply stake transaction: {e}")
            return False

    def _apply_slash(self, tx: 'Transaction') -> bool:
        """应用惩罚交易"""
        try:
            from contracts.token_contract import TokenContract
            token_contract = TokenContract(self.world_state)
            return token_contract.slash(tx.data, tx.sender)
        except Exception as e:
            print(f"Failed to apply slash transaction: {e}")
            return False


# 单例模式的世界状态实例
world_state = WorldState()
# 单例模式的状态处理器实例
state_processor = StateProcessor(world_state)