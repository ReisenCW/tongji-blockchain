"""
mABC/contracts/ops_contract.py

运维 SOP 流程控制合约（严格分工版 - 仅成员3职责）
严格定义状态流转：Init → Data_Collected → Root_Cause_Proposed → Consensus → Solution
负责：
1. SOP 状态机管理
2. 每个步骤的前置校验
3. 关键步骤的事件日志发射
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib


class SOPState(str, Enum):
    """SOP 状态机定义"""
    Init = "Init"
    Data_Collected = "Data_Collected"
    Root_Cause_Proposed = "Root_Cause_Proposed"
    Consensus = "Consensus"
    Solution = "Solution"


class OpsSOPContract:
    """
    运维 SOP 主合约（仅流程控制）
    使用类级存储，所有实例共享（单例模式）
    """

    # 类级存储（内存中全局唯一）
    _storage: Dict[str, Any] = {
        "current_state": SOPState.Init.value,
        "incident_data": {},                    # 数据采集阶段信息
        "proposals": {},                        # proposal_id -> {proposer, content, timestamp}
        "current_proposal_id": None,            # 当前处于 Root_Cause_Proposed 阶段的提案ID
        "events": []                            # 事件日志列表
    }

    def __init__(self):
        self.storage = OpsSOPContract._storage

    def _emit_event(self, name: str, **kwargs):
        """发射事件（供前端和成员4监听）"""
        # 生成唯一ID
        event_id = hashlib.sha256(f"{name}{datetime.now().isoformat()}{str(kwargs)}".encode()).hexdigest()
        event = {
            "id": event_id,
            "name": name,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        self.storage["events"].append(event)

    # ====================== 核心方法（Agent 可直接调用） ======================

    def submit_data_collection(self, agent_id: str, data_summary: str, raw_data: Optional[Dict] = None):
        """提交数据采集结果（Init → Data_Collected）"""
        if self.storage["current_state"] != SOPState.Init.value:
            raise ValueError("Data collection can only be submitted in Init state")

        self.storage["current_state"] = SOPState.Data_Collected.value
        self.storage["incident_data"] = {
            "submitter": agent_id,
            "summary": data_summary,
            "raw_data": raw_data or {},
            "timestamp": datetime.now().isoformat()
        }

        self._emit_event(
            "DataCollected",
            agent_id=agent_id,
            summary=data_summary
        )

        return {"new_state": self.storage["current_state"], "message": "Data collection completed"}

    def propose_root_cause(self, agent_id: str, content: str):
        """提出根因分析提案（Data_Collected → Root_Cause_Proposed）"""
        if self.storage["current_state"] != SOPState.Data_Collected.value:
            raise ValueError("Root cause can only be proposed after data collection")

        proposal_id = hashlib.sha256(f"{agent_id}{content}{datetime.now().isoformat()}".encode()).hexdigest()

        proposal = {
            "proposal_id": proposal_id,
            "proposer": agent_id,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "status": "pending"
        }

        self.storage["proposals"][proposal_id] = proposal
        self.storage["current_proposal_id"] = proposal_id
        self.storage["current_state"] = SOPState.Root_Cause_Proposed.value

        self._emit_event(
            "RootCauseProposed",
            proposal_id=proposal_id,
            proposer=agent_id,
            content=content
        )

        return {
            "proposal_id": proposal_id,
            "new_state": self.storage["current_state"],
            "message": "Root cause proposal submitted"
        }

    # ====================== 内部方法（仅供智能合约调用） ======================

    def advance_to_consensus_phase(self, proposal_id: str, passed: bool):
        """
        由智能合约调用
        在完成投票统计、质押检查、奖惩执行后，调用此方法推进 SOP 状态并发射事件
        """
        if self.storage["current_state"] != SOPState.Root_Cause_Proposed.value:
            raise ValueError("Can only advance consensus from Root_Cause_Proposed state")

        if proposal_id != self.storage["current_proposal_id"]:
            raise ValueError("Proposal ID does not match current active proposal")

        if passed:
            # 通过 → Consensus → Solution
            self.storage["current_state"] = SOPState.Consensus.value
            self._emit_event("ConsensusReached", proposal_id=proposal_id, passed=True)

            self.storage["current_state"] = SOPState.Solution.value
            proposal = self.storage["proposals"][proposal_id]
            self._emit_event(
                "SolutionPhaseEntered",
                proposal_id=proposal_id,
                root_cause=proposal["content"]
            )
        else:
            # 否决 → 回退到 Data_Collected，可重新提案
            self.storage["current_state"] = SOPState.Data_Collected.value
            self.storage["current_proposal_id"] = None
            self._emit_event("ConsensusReached", proposal_id=proposal_id, passed=False)
            self._emit_event(
                "ProposalRejected",
                proposal_id=proposal_id,
                proposer=self.storage["proposals"][proposal_id]["proposer"]
            )

    # ====================== 查询接口（供前端/API 使用） ======================

    def get_current_state(self) -> str:
        return self.storage["current_state"]

    def get_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.storage["events"][-limit:]

    def get_current_proposal(self) -> Optional[Dict[str, Any]]:
        pid = self.storage["current_proposal_id"]
        return self.storage["proposals"].get(pid)

    def get_incident_data(self) -> Dict[str, Any]:
        return self.storage["incident_data"]

    def reset_for_testing(self):
        """仅用于单元测试：重置合约状态"""
        # 修改为原地更新，确保实例引用的 storage 被重置
        self.storage["current_state"] = SOPState.Init.value
        self.storage["incident_data"] = {}
        self.storage["proposals"] = {}
        self.storage["current_proposal_id"] = None
        self.storage["events"] = []


# 全局单例实例（全项目统一使用）
ops_sop_contract = OpsSOPContract()