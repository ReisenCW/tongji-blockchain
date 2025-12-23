from typing import Dict, Any
from core.state import WorldState

class TokenContract:
    """
    Token 管理合约
    负责转账、质押和惩罚
    """
    
    def __init__(self, world_state: WorldState):
        self.world_state = world_state

    def transfer(self, tx_data: Dict[str, Any], sender: str) -> bool:
        """
        执行转账
        :param tx_data: 包含 'to' 和 'amount'
        :param sender: 发送者地址
        """
        to_address = tx_data.get("to")
        amount = tx_data.get("amount")
        
        if not to_address or amount is None or amount < 0:
            return False

        from_account = self.world_state.get_account(sender)
        if not from_account or from_account.balance < amount:
            return False
        
        to_account = self.world_state.get_account(to_address)
        if not to_account:
            to_account = self.world_state.create_account(to_address)
            
        from_account.balance -= amount
        to_account.balance += amount
        
        self.world_state.update_account(from_account)
        self.world_state.update_account(to_account)
        return True

    def stake(self, tx_data: Dict[str, Any], sender: str) -> bool:
        """
        执行质押
        :param tx_data: 包含 'amount'
        :param sender: 发送者地址
        """
        amount = tx_data.get("amount")
        
        if amount is None or amount < 0:
            return False
            
        account = self.world_state.get_account(sender)
        if not account or account.balance < amount:
            return False
            
        account.balance -= amount
        account.stake += amount
        
        self.world_state.update_account(account)
        return True

    def slash(self, tx_data: Dict[str, Any], sender: str) -> bool:
        """
        执行惩罚 (扣除质押)
        :param tx_data: 包含 'target' 和 'amount'
        :param sender: 发送者地址 (需要权限检查，这里简化)
        """
        target_address = tx_data.get("target")
        amount = tx_data.get("amount")
        
        if not target_address or amount is None or amount < 0:
            return False
            
        target_account = self.world_state.get_account(target_address)
        if not target_account:
            return False
            
        # 扣除质押
        if target_account.stake < amount:
            amount = target_account.stake # 最多扣完
            
        target_account.stake -= amount
        # 可以在这里将扣除的 Token 销毁或转入国库
        
        self.world_state.update_account(target_account)
        return True

    def reward(self, tx_data: Dict[str, Any], sender: str) -> bool:
        """
        执行奖励 (从金库扣款 + 目标账户加款 + 信誉)
        :param tx_data: 包含 'target', 'amount', 'reputation'
        :param sender: 发送者地址 (通常是系统或合约)
        """
        target_address = tx_data.get("target")
        amount = tx_data.get("amount", 0)
        reputation = tx_data.get("reputation", 0)
        
        if not target_address:
            return False
            
        from_account = self.world_state.get_account(sender)
        if not from_account:
            from_account = self.world_state.create_account(sender)
        
        target_account = self.world_state.get_account(target_address)
        if not target_account:
            target_account = self.world_state.create_account(target_address)
            
        if amount > 0:
            if from_account.balance < amount:
                return False
            from_account.balance -= amount
            target_account.balance += amount
        if reputation != 0:
            target_account.reputation += reputation
            # 限制信誉范围 0-100
            target_account.reputation = max(0, min(100, target_account.reputation))
        
        self.world_state.update_account(from_account)
        self.world_state.update_account(target_account)
        return True
    
    def penalty(self, tx_data: Dict[str, Any], sender: str) -> bool:
        """
        执行罚没 (将目标余额的一部分转入系统金库，并降低信誉)
        :param tx_data: 包含 'target', 'amount', 'reputation'
        :param sender: 发送者地址 (通常是系统或合约)
        """
        target_address = tx_data.get("target")
        amount = tx_data.get("amount", 0)
        reputation = tx_data.get("reputation", 0)
        
        if not target_address or amount < 0:
            return False
        
        target_account = self.world_state.get_account(target_address)
        if not target_account:
            return False
        
        # 罚没金额不超过余额
        amount = min(amount, max(0, target_account.balance))
        
        # 找到系统金库账户
        try:
            from core.vm import blockchain
            treasury = blockchain._get_treasury_account()
        except Exception:
            treasury = None
        
        # 扣减余额并转入金库（若存在）
        if amount > 0:
            target_account.balance -= amount
            if treasury:
                treasury.balance = (treasury.balance or 0) + amount
                self.world_state.update_account(treasury)
        
        # 信誉调整
        if reputation != 0:
            target_account.reputation += reputation
            target_account.reputation = max(0, min(100, target_account.reputation))
        
        self.world_state.update_account(target_account)
        return True
