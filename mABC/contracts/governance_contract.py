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
        
        # 如果提案不存在，则自动为投票者创建一个提案
        if not proposal_data:
            voter_account = self.world_state.get_account(sender)
            if not voter_account:
                voter_account = self.world_state.create_account(sender)
            
            proposal_data = {
                "proposer": sender,
                "content": f"Auto-created proposal for vote {proposal_id}",
                "timestamp": timestamp,
                "votes": {
                    "for": 0,
                    "against": 0,
                    "abstain": 0
                }
            }
            voter_account.root_cause_proposals[proposal_id] = proposal_data
            self.world_state.update_account(voter_account)
            proposal_account = voter_account
            
        # 获取投票者信息
        voter_account = self.world_state.get_account(sender)
        if not voter_account:
            voter_account = self.world_state.create_account(sender)
            
        # 计算权重（与前端展示保持一致）：
        # 基础权重: 1.0
        # 信誉加成: max(0, (reputation - 50) / 10.0)
        # 质押加成: stake / 1000.0
        # 当 stake=0 时也具有非 1 的权重，避免全为 1
        rep_bonus = max(0.0, (voter_account.reputation - 50) / 10.0)
        stake_bonus = voter_account.stake / 1000.0
        weight = 1.0 + rep_bonus + stake_bonus
            
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
        逻辑：如果赞成票权重超过全网总权重的 50%，则通过；如果反对票超过 50%，则否决。
        """
        from contracts.ops_contract import ops_sop_contract
        
        votes_for = proposal_data["votes"]["for"]
        votes_against = proposal_data["votes"]["against"]
        
        # 计算参与者总权重（仅统计对该提案有投票记录的账户，避免非参与账户和系统金库影响阈值）
        total_network_weight = 0.0
        for account in self.world_state.state.values():
            if account.votes.get(proposal_id):
                rep_bonus = max(0.0, (account.reputation - 50) / 10.0)
                stake_bonus = account.stake / 1000.0
                weight = 1.0 + rep_bonus + stake_bonus
                total_network_weight += weight
            
        # 设定通过阈值 (50%)
        PASS_THRESHOLD_RATIO = 0.5
        threshold = total_network_weight * PASS_THRESHOLD_RATIO
        
        if votes_for > threshold:
            # 提案通过
            try:
                ops_sop_contract.advance_to_consensus_phase(proposal_id, passed=True)
                print(f"Proposal {proposal_id} PASSED via consensus (For: {votes_for}, Total: {total_network_weight}).")
            except Exception as e:
                print(f"Failed to advance consensus (Pass): {e}")
                
        elif votes_against > threshold:
            # 提案被否决
            try:
                ops_sop_contract.advance_to_consensus_phase(proposal_id, passed=False)
                print(f"Proposal {proposal_id} REJECTED via consensus (Against: {votes_against}, Total: {total_network_weight}).")
            except Exception as e:
                print(f"Failed to advance consensus (Reject): {e}")
