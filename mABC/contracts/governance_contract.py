from typing import Dict, Any
from core.state import WorldState

class GovernanceContract:
    """
    治理合约
    负责共识投票
    """
    
    def __init__(self, world_state: WorldState):
        self.world_state = world_state

    def vote(self, tx_data: Dict[str, Any], sender: str, timestamp: int) -> bool:
        """
        执行投票
        :param tx_data: 包含 'proposal_id', 'vote_option'
        :param sender: 投票者地址
        :param timestamp: 时间戳
        """
        proposal_id = tx_data.get("proposal_id")
        vote_option = tx_data.get("vote_option", "").lower()
        
        valid_options = ["for", "against", "abstain"]
        if vote_option not in valid_options:
            return False
            
        # 查找提案
        proposal_account = None
        proposal_data = None
        for account in self.world_state.state.values():
            if proposal_id in account.root_cause_proposals:
                proposal_account = account
                proposal_data = account.root_cause_proposals[proposal_id]
                break
        
        if not proposal_data:
            return False
            
        # 获取投票者信息
        voter_account = self.world_state.get_account(sender)
        if not voter_account:
            voter_account = self.world_state.create_account(sender)
            
        # 计算权重: 质押量 * (信誉分 / 100)
        # 基础权重为 1 (防止无质押无法投票，或者根据业务逻辑调整)
        weight = max(1.0, voter_account.stake * (voter_account.reputation / 100.0))
            
        vote_data = {
            "proposal_id": proposal_id,
            "vote_option": vote_option,
            "weight": weight,
            "timestamp": timestamp
        }
        
        voter_account.votes[proposal_id] = vote_data
        self.world_state.update_account(voter_account)
        
        # 更新提案的投票计数 (加权)
        proposal_data["votes"][vote_option] += weight
        
        # 更新提案账户
        if proposal_account:
            proposal_account.root_cause_proposals[proposal_id] = proposal_data
            self.world_state.update_account(proposal_account)
            
            # 检查共识是否达成
            self._check_consensus(proposal_id, proposal_data)
            
        return True

    def _check_consensus(self, proposal_id: str, proposal_data: Dict[str, Any]):
        """
        检查是否达成共识
        简单逻辑：如果赞成票权重超过总质押量的 50% (或者简单设定一个阈值)，则通过
        """
        from contracts.ops_contract import ops_sop_contract
        
        votes_for = proposal_data["votes"]["for"]
        votes_against = proposal_data["votes"]["against"]
        
        # 这里简化处理：假设总权重阈值为 10 (实际应计算全网总质押量)
        CONSENSUS_THRESHOLD = 10.0
        
        if votes_for >= CONSENSUS_THRESHOLD:
            # 提案通过
            try:
                ops_sop_contract.advance_to_consensus_phase(proposal_id, passed=True)
                print(f"Proposal {proposal_id} PASSED via consensus.")
            except Exception as e:
                print(f"Failed to advance consensus (Pass): {e}")
                
        elif votes_against >= CONSENSUS_THRESHOLD:
            # 提案被否决
            try:
                ops_sop_contract.advance_to_consensus_phase(proposal_id, passed=False)
                print(f"Proposal {proposal_id} REJECTED via consensus.")
            except Exception as e:
                print(f"Failed to advance consensus (Reject): {e}")
