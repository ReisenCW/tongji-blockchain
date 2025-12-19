"""
区块链核心开发 - 执行层
负责交易执行与状态更新，实现接口文档中成员2的职责
"""

import hashlib
import json
import time
from typing import Dict, Any, Optional, List
from ecdsa import SigningKey, VerifyingKey, SECP256k1
from ecdsa.util import sigencode_der, sigdecode_der
from pydantic import BaseModel, Field
from .state import world_state, Account


class TransactionType:
    """交易类型常量"""
    # 根据接口文档和mABC项目需求定义交易类型
    SUBMIT_ANALYSIS = "submit_analysis"
    PROPOSE_ROOT_CAUSE = "propose_root_cause"
    VOTE = "vote"
    TRANSFER = "transfer"
    STAKE = "stake"


class Transaction(BaseModel):
    """交易模型 - 符合接口文档中成员1的数据定义职责"""
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
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class StateProcessor:
    """状态处理器 - 负责执行交易并更新世界状态
    符合接口文档中成员2的状态更新职责
    """
    
    def __init__(self):
        self.gas_price = 1  # 每单位Gas的价格
        self.min_gas_limit = 21000  # 最小Gas限制
    
    def apply_transaction(self, tx: Transaction) -> TransactionReceipt:
        """应用交易并更新状态
        符合接口文档中成员2的状态更新接口
        """
        # 计算交易哈希
        tx_hash = self.hash_transaction(tx)
        
        # 验证交易
        is_valid, validation_msg = self.validate_transaction(tx)
        if not is_valid:
            return TransactionReceipt(
                tx_hash=tx_hash,
                success=False,
                gas_used=0,
                error_message=validation_msg
            )
        
        # 扣除Gas费用
        gas_fee = tx.gas_price * tx.gas_limit
        account = world_state.get_account(tx.sender)
        if not account:
            account = world_state.create_account(tx.sender)
        
        account.balance -= gas_fee
        world_state.update_account(account)
        
        # 根据交易类型执行不同的操作
        result = None
        try:
            if tx.tx_type == TransactionType.SUBMIT_ANALYSIS:
                result = self._execute_submit_analysis(tx)
            elif tx.tx_type == TransactionType.PROPOSE_ROOT_CAUSE:
                result = self._execute_propose_root_cause(tx)
            elif tx.tx_type == TransactionType.VOTE:
                result = self._execute_vote(tx)
            elif tx.tx_type == TransactionType.TRANSFER:
                result = self._execute_transfer(tx)
            elif tx.tx_type == TransactionType.STAKE:
                result = self._execute_stake(tx)
            else:
                raise ValueError(f"Unknown transaction type: {tx.tx_type}")
            
            # 增加nonce
            world_state.increment_nonce(tx.sender)
            
            return TransactionReceipt(
                tx_hash=tx_hash,
                success=True,
                gas_used=self.min_gas_limit,  # 简化处理，实际应根据不同操作计算Gas消耗
                result=result
            )
        except Exception as e:
            # 如果执行失败，退还多余的Gas费用（简化处理）
            account.balance += gas_fee - (self.gas_price * self.min_gas_limit)
            world_state.update_account(account)
            
            return TransactionReceipt(
                tx_hash=tx_hash,
                success=False,
                gas_used=self.min_gas_limit,
                error_message=str(e)
            )
    
    def hash_transaction(self, tx: Transaction) -> str:
        """计算交易哈希 - 符合接口文档中成员1的哈希计算职责"""
        # 创建不包含签名的交易副本用于哈希计算
        tx_dict = tx.dict(exclude={'signature'})
        tx_json = json.dumps(tx_dict, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(tx_json.encode()).hexdigest()
    
    def sign_transaction(self, tx: Transaction, private_key: str) -> Transaction:
        """对交易进行签名"""
        # 生成签名密钥对象
        sk = SigningKey.from_string(bytes.fromhex(private_key), curve=SECP256k1)
        
        # 计算交易哈希
        tx_hash = self.hash_transaction(tx)
        
        # 对哈希进行签名
        signature = sk.sign(bytes.fromhex(tx_hash), sigencode=sigencode_der)
        tx.signature = signature.hex()
        
        return tx
    
    def verify_transaction_signature(self, tx: Transaction) -> bool:
        """验证交易签名 - 符合接口文档中成员2的交易池管理职责"""
        if not tx.signature:
            return False
        
        try:
            # 获取发送者的公钥（这里简化处理，实际应从地址推导公钥）
            # 在实际实现中，应该从tx.sender地址推导出公钥
            # 这里为了简化，我们假设tx.sender就是公钥
            vk = VerifyingKey.from_string(bytes.fromhex(tx.sender), curve=SECP256k1)
            
            # 计算交易哈希
            tx_hash = self.hash_transaction(tx)
            
            # 验证签名
            return vk.verify(
                bytes.fromhex(tx.signature), 
                bytes.fromhex(tx_hash), 
                sigdecode=sigdecode_der
            )
        except Exception as e:
            print(f"Signature verification failed: {e}")
            return False
    
    def validate_transaction(self, tx: Transaction) -> tuple[bool, str]:
        """验证交易的有效性 - 符合接口文档中成员2的交易池管理职责"""
        # 1. 检查nonce
        account = world_state.get_account(tx.sender)
        if account and tx.nonce != account.nonce:
            return False, f"Invalid nonce. Expected {account.nonce}, got {tx.nonce}"
        
        # 2. 检查Gas限制
        if tx.gas_limit < self.min_gas_limit:
            return False, f"Gas limit too low. Minimum is {self.min_gas_limit}"
        
        # 3. 检查发送者余额
        required_gas = tx.gas_price * tx.gas_limit
        if account and account.balance < required_gas:
            return False, f"Insufficient balance. Required {required_gas}, available {account.balance}"
        
        # 4. 验证签名
        if not self.verify_transaction_signature(tx):
            return False, "Invalid signature"
        
        # 5. 根据交易类型验证数据
        if tx.tx_type == TransactionType.SUBMIT_ANALYSIS:
            if "analysis_content" not in tx.data:
                return False, "Missing analysis_content in data for submit_analysis transaction"
        elif tx.tx_type == TransactionType.PROPOSE_ROOT_CAUSE:
            if "proposal_content" not in tx.data:
                return False, "Missing proposal_content in data for root cause proposal"
        elif tx.tx_type == TransactionType.VOTE:
            if "proposal_id" not in tx.data or "vote_option" not in tx.data:
                return False, "Missing proposal_id or vote_option in data for vote transaction"
        elif tx.tx_type == TransactionType.TRANSFER:
            if "to" not in tx.data or "amount" not in tx.data:
                return False, "Missing to or amount in data for transfer transaction"
        elif tx.tx_type == TransactionType.STAKE:
            if "amount" not in tx.data:
                return False, "Missing amount in data for stake transaction"
        
        return True, "Valid transaction"
    
    def _execute_submit_analysis(self, tx: Transaction) -> Dict[str, Any]:
        """执行提交分析交易 - 符合接口文档中成员3的SOP状态流转职责"""
        analysis_id = hashlib.sha256(
            f"{tx.sender}{tx.timestamp}{tx.data['analysis_content']}".encode()
        ).hexdigest()
        
        analysis_data = {
            "submitter": tx.sender,
            "content": tx.data["analysis_content"],
            "timestamp": tx.timestamp,
            "status": "submitted"
        }
        
        # 将分析提交到提交者账户中
        account = world_state.get_account(tx.sender)
        if not account:
            account = world_state.create_account(tx.sender)
        
        if not hasattr(account, 'analyses'):
            account.analyses = {}
        
        account.analyses[analysis_id] = analysis_data
        world_state.update_account(account)
        
        return {
            "analysis_id": analysis_id,
            "message": "Analysis submitted successfully"
        }
    
    def _execute_propose_root_cause(self, tx: Transaction) -> Dict[str, Any]:
        """执行根因提案交易"""
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
        world_state.add_root_cause_proposal(tx.sender, proposal_id, proposal_data)
        
        return {
            "proposal_id": proposal_id,
            "message": "Root cause proposal created successfully"
        }
    
    def _execute_vote(self, tx: Transaction) -> Dict[str, Any]:
        """执行投票交易 - 符合接口文档中成员4的共识投票职责"""
        proposal_id = tx.data["proposal_id"]
        vote_option = tx.data["vote_option"].lower()
        
        # 验证投票选项
        valid_options = ["for", "against", "abstain"]
        if vote_option not in valid_options:
            raise ValueError(f"Invalid vote option. Must be one of {valid_options}")
        
        # 查找提案
        all_proposals = world_state.get_all_proposals()
        if proposal_id not in all_proposals:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        # 添加投票到投票者账户
        vote_data = {
            "proposal_id": proposal_id,
            "vote_option": vote_option,
            "timestamp": tx.timestamp
        }
        
        world_state.add_vote(tx.sender, proposal_id, vote_data)
        
        # 更新提案的投票计数
        proposal = all_proposals[proposal_id]
        proposal["votes"][vote_option] += 1
        
        return {
            "proposal_id": proposal_id,
            "vote_option": vote_option,
            "message": "Vote recorded successfully"
        }
    
    def _execute_transfer(self, tx: Transaction) -> Dict[str, Any]:
        """执行转账交易 - 符合接口文档中成员4的Token管理职责"""
        to_address = tx.data["to"]
        amount = tx.data["amount"]
        
        # 执行转账
        success = world_state.transfer_balance(tx.sender, to_address, amount)
        if not success:
            raise ValueError("Transfer failed due to insufficient balance")
        
        return {
            "to": to_address,
            "amount": amount,
            "message": "Transfer completed successfully"
        }
    
    def _execute_stake(self, tx: Transaction) -> Dict[str, Any]:
        """执行质押交易 - 符合接口文档中成员4的Token管理职责"""
        amount = tx.data["amount"]
        
        # 检查发送者余额
        account = world_state.get_account(tx.sender)
        if not account or account.balance < amount:
            raise ValueError("Insufficient balance for staking")
        
        # 扣除质押金额（在实际实现中可能需要特殊的质押账户）
        account.balance -= amount
        
        # 增加质押量（在实际实现中可能需要单独的质押字段）
        if not hasattr(account, 'staked_amount'):
            account.staked_amount = 0
        account.staked_amount += amount
        
        world_state.update_account(account)
        
        return {
            "amount": amount,
            "message": "Staking completed successfully"
        }


# 单例模式的虚拟机实例
vm = StateProcessor()


def generate_keypair():
    """生成密钥对（用于测试）"""
    sk = SigningKey.generate(curve=SECP256k1)
    vk = sk.get_verifying_key()
    return sk.to_string().hex(), vk.to_string().hex()


def create_test_transaction():
    """创建测试交易（用于演示）"""
    # 生成测试密钥对
    private_key, public_key = generate_keypair()
    
    # 创建测试账户并充值
    account = world_state.create_account(public_key)
    account.balance = 1000000  # 充值1000000
    world_state.update_account(account)
    
    # 创建根因提案交易
    tx = Transaction(
        tx_type=TransactionType.PROPOSE_ROOT_CAUSE,
        sender=public_key,
        nonce=0,
        gas_price=1,
        gas_limit=50000,
        data={
            "proposal_content": "Root cause: Database connection timeout in user service"
        }
    )
    
    # 签名交易
    signed_tx = vm.sign_transaction(tx, private_key)
    
    return signed_tx, private_key, public_key


if __name__ == "__main__":
    # 演示如何使用VM执行交易
    print("Creating test transaction...")
    tx, private_key, public_key = create_test_transaction()
    
    print(f"Executing transaction: {tx}")
    receipt = vm.execute_transaction(tx)
    print(f"Transaction receipt: {receipt}")
    
    if receipt.success:
        print("Transaction executed successfully!")
        print(f"Result: {receipt.result}")
        
        # 显示当前状态
        account = world_state.get_account(public_key)
        print(f"Account balance: {account.balance}")
        print(f"Account nonce: {account.nonce}")
        print(f"Proposals: {account.root_cause_proposals}")