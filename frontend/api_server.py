"""
FastAPI后端API服务器
为前端提供区块链数据接口
"""

import sys
import os
import time
import json
import random
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

# 添加mABC模块路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
mabc_path = os.path.join(parent_dir, "mABC")

if os.path.exists(mabc_path):
    if mabc_path not in sys.path:
        sys.path.insert(0, mabc_path)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

# mABC Core Imports
from core.vm import blockchain
from core.types import Transaction, Block, calculate_hash, get_merkle_root
from core.state import world_state
from core.client import ChainClient
from contracts.ops_contract import ops_sop_contract

# Agent Imports
from agents.base.profile import (
    DataDetective,
    DependencyExplorer,
    ProbabilityOracle,
    FaultMapper,
    SolutionEngineer,
    AlertReceiver,
    ProcessScheduler,
)
from agents.base.run import ReActTotRun
from agents.base.dao_run import DAOExecutor
from agents.tools import process_scheduler_tools

app = FastAPI(title="mABC Blockchain API", version="1.0.0")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Response Models
class BlockResponse(BaseModel):
    index: int
    hash: str
    previous_hash: str
    timestamp: float
    merkle_root: str
    transaction_count: int
    transactions: List[Dict[str, Any]]


class BlockchainInfoResponse(BaseModel):
    block_height: int
    pending_transactions: int
    latest_block_hash: Optional[str]
    chain_id: str


class MerkleProofResponse(BaseModel):
    transaction_hash: str
    merkle_root: str
    proof_path: List[Dict[str, Any]]
    verified: bool


# DualOutput for capturing logs
class DualOutput:
    def __init__(self, original_stdout):
        self.original_stdout = original_stdout

    def write(self, message):
        self.original_stdout.write(message)

        msg_str = str(message)
        stripped = msg_str.strip()

        if not stripped:
            return

        # 1. 关键词过滤 (只允许 Thought, Action, Final Answer)
        has_keyword = False
        log_type = "info"

        if "Final Answer:" in msg_str:
            has_keyword = True
            log_type = "answer"
        elif "Action:" in msg_str or "Action Tool" in msg_str:
            has_keyword = True
            log_type = "action"
        elif "Thought:" in msg_str:
            has_keyword = True
            log_type = "thought"
        elif "奖励" in msg_str or "reward" in msg_str.lower():
            has_keyword = True
            log_type = "reward"

        if not has_keyword:
            return

        # 2. 排除垃圾信息 (历史记录dump, 分割线)
        if stripped.startswith("[{") or stripped.startswith("*"):
            return

        if log_type == "reward":
            lower_msg = msg_str.lower()
            if "transaction added to pending pool" in lower_msg:
                return
            is_full_reward = (
                ("奖励发送" in msg_str)
                and ("to=" in msg_str)
                and ("token=" in msg_str)
                and ("rep=" in msg_str)
                and ("onchain_block=" in msg_str)
            )
            if not is_full_reward:
                return
            to_part = None
            token_part = None
            rep_part = None
            block_part = None
            try:
                s = stripped
                idx_to = s.find("to=")
                idx_token = s.find("token=")
                idx_rep = s.find("rep=")
                idx_block = s.find("onchain_block=")
                if (
                    idx_to != -1
                    and idx_token != -1
                    and idx_rep != -1
                    and idx_block != -1
                ):
                    to_part = s[idx_to + 3 : s.find(",", idx_to)]
                    token_part = s[idx_token + 6 : s.find(",", idx_token)]
                    rep_part = s[idx_rep + 4 : s.find(",", idx_rep)]
                    end_block = s.find(",", idx_block)
                    block_part = s[
                        idx_block + 13 : end_block if end_block != -1 else len(s)
                    ]
            except Exception:
                pass
            if to_part and token_part and rep_part and block_part:
                key = f"{to_part}:{token_part}:{rep_part}:{block_part}"
                if not hasattr(app, "_recent_reward_keys"):
                    app._recent_reward_keys = []
                if key in app._recent_reward_keys:
                    return
                app._recent_reward_keys.append(key)
                if len(app._recent_reward_keys) > 1000:
                    app._recent_reward_keys = app._recent_reward_keys[-1000:]

        # Init logs if not exists
        if not hasattr(app, "agent_logs"):
            app.agent_logs = []

        # 3. 清理内容 (去除 A: 前缀)
        content = stripped
        if content.startswith("A: "):
            content = content[3:].strip()

        # Add to logs
        app.agent_logs.append(
            {
                "id": str(uuid.uuid4()),
                "type": "agent_log",
                "log_type": log_type,
                "content": content,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Keep log size manageable
        if len(app.agent_logs) > 1000:
            app.agent_logs = app.agent_logs[-1000:]

    def flush(self):
        self.original_stdout.flush()


# Routes
@app.get("/api/blocks", response_model=List[BlockResponse])
async def get_blocks(limit: int = 10, offset: int = 0):
    try:
        chain = blockchain.chain
        total_blocks = len(chain)
        start = offset or 0
        end = start + limit if limit else total_blockstx_js
        blocks = chain[start:end]

        result = []
        for block in blocks:
            tx_list = []
            for tx in block.transactions:
                tx_dict = tx.model_dump()
                tx_json = str(sorted(tx_dict.items()))
                tx_hash = calculate_hash(tx_json)
                tx_dict["tx_hash"] = tx_hash
                tx_list.append(tx_dict)

            result.append(
                BlockResponse(
                    index=block.header.index,
                    hash=block.hash,
                    previous_hash=block.header.previous_hash,
                    timestamp=block.header.timestamp,
                    merkle_root=block.header.merkle_root,
                    transaction_count=len(block.transactions),
                    transactions=tx_list,
                )
            )

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/block/{index}", response_model=BlockResponse)
async def get_block(index: int):
    try:
        if index < 0 or index >= len(blockchain.chain):
            raise HTTPException(status_code=404, detail="Block not found")

        block = blockchain.chain[index]

        tx_list = []
        for tx in block.transactions:
            tx_dict = tx.model_dump()
            tx_json = str(sorted(tx_dict.items()))
            tx_hash = calculate_hash(tx_json)
            tx_dict["tx_hash"] = tx_hash
            tx_list.append(tx_dict)

        return BlockResponse(
            index=block.header.index,
            hash=block.hash,
            previous_hash=block.header.previous_hash,
            timestamp=block.header.timestamp,
            merkle_root=block.header.merkle_root,
            transaction_count=len(block.transactions),
            transactions=tx_list,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/transaction/{tx_hash}")
async def get_transaction(tx_hash: str):
    try:
        for block in blockchain.chain:
            for tx in block.transactions:
                tx_dict = tx.model_dump()
                tx_json = str(sorted(tx_dict.items()))
                calculated_hash = calculate_hash(tx_json)

                if calculated_hash == tx_hash:
                    tx_dict["tx_hash"] = calculated_hash
                    tx_dict["block_index"] = block.header.index
                    tx_dict["block_hash"] = block.hash
                    return tx_dict

        raise HTTPException(status_code=404, detail="Transaction not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/blockchain/info", response_model=BlockchainInfoResponse)
async def get_blockchain_info():
    try:
        latest_block = blockchain.chain[-1] if blockchain.chain else None
        return BlockchainInfoResponse(
            block_height=len(blockchain.chain),
            pending_transactions=len(blockchain.pending_transactions),
            latest_block_hash=latest_block.hash if latest_block else None,
            chain_id="mABC-DAO-Chain",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/merkle-proof/{block_index}/{tx_index}", response_model=MerkleProofResponse
)
async def get_merkle_proof(block_index: int, tx_index: int):
    try:
        if block_index < 0 or block_index >= len(blockchain.chain):
            raise HTTPException(status_code=404, detail="Block not found")

        block = blockchain.chain[block_index]

        if tx_index < 0 or tx_index >= len(block.transactions):
            raise HTTPException(status_code=404, detail="Transaction not found")

        transaction_hashes = []
        for tx in block.transactions:
            tx_dict = tx.model_dump()
            tx_json = str(sorted(tx_dict.items()))
            transaction_hashes.append(calculate_hash(tx_json))

        target_tx_hash = transaction_hashes[tx_index]

        proof_path = []
        merkle_tree = transaction_hashes[:]
        current_index = tx_index

        while len(merkle_tree) > 1:
            if current_index % 2 == 0:
                sibling_index = current_index + 1
                if sibling_index < len(merkle_tree):
                    proof_path.append(
                        {"position": "right", "hash": merkle_tree[sibling_index]}
                    )
            else:
                sibling_index = current_index - 1
                proof_path.append(
                    {"position": "left", "hash": merkle_tree[sibling_index]}
                )

            new_level = []
            for i in range(0, len(merkle_tree), 2):
                if i + 1 < len(merkle_tree):
                    combined = merkle_tree[i] + merkle_tree[i + 1]
                else:
                    combined = merkle_tree[i] + merkle_tree[i]
                new_level.append(calculate_hash(combined))

            merkle_tree = new_level
            current_index = current_index // 2

        verified_root = target_tx_hash
        for proof in proof_path:
            if proof["position"] == "left":
                combined = proof["hash"] + verified_root
            else:
                combined = verified_root + proof["hash"]
            verified_root = calculate_hash(combined)

        verified = verified_root == block.header.merkle_root

        return MerkleProofResponse(
            transaction_hash=target_tx_hash,
            merkle_root=block.header.merkle_root,
            proof_path=proof_path,
            verified=verified,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pending-transactions")
async def get_pending_transactions():
    try:
        result = []
        for tx in blockchain.pending_transactions:
            tx_dict = tx.model_dump()
            tx_json = str(sorted(tx_dict.items()))
            tx_hash = calculate_hash(tx_json)
            tx_dict["tx_hash"] = tx_hash
            result.append(tx_dict)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reset")
async def reset_data():
    try:
        # 1. 重置世界状态
        # 清空内存中的状态
        world_state.state = {}
        # 删除数据库文件
        db_path = world_state.db_path
        if os.path.exists(db_path):
            try:
                # 尝试关闭现有的连接（如果有办法访问的话）
                # 这里直接删除，依赖 os 操作
                os.remove(db_path)
            except Exception as e:
                print(f"Warning: Failed to delete db file: {e}")

        # 重新初始化数据库
        world_state._init_db()
        print("✅ World State has been reset.")

        # 2. 重置 SOP 合约状态
        ops_sop_contract.reset_for_testing()

        # 3. 清空日志
        if hasattr(app, "agent_logs"):
            app.agent_logs = []

        # 4. 初始化核心 Agent 账户资产
        if not hasattr(app, "dao_agents"):
            app.dao_agents = {
                "AlertReceiver": AlertReceiver(),
                "ProcessScheduler": ProcessScheduler(),
                "DataDetective": DataDetective(),
                "DependencyExplorer": DependencyExplorer(),
                "ProbabilityOracle": ProbabilityOracle(),
                "FaultMapper": FaultMapper(),
                "SolutionEngineer": SolutionEngineer(),
            }
        agent_addresses = set()
        for ag in app.dao_agents.values():
            agent_addresses.add(ag.wallet_address)
            acc = world_state.get_account(
                ag.wallet_address
            ) or world_state.create_account(ag.wallet_address)
            acc.name = ag.role_name
            acc.balance = 20000
            acc.reputation = 80
            acc.stake = 0
            world_state.update_account(acc)
            print(
                "name: "
                + str(ag.role_name)
                + ", address: "
                + str(ag.wallet_address)
                + ", balance: "
                + str(acc.balance)
            )

        # 5. 更新区块链的Agent地址名单，防止误判金库
        blockchain.agent_addresses = agent_addresses

        # 6. 显式初始化系统金库 (Treasury)
        # 生成一个独立的金库地址
        from ecdsa import SigningKey, SECP256k1
        from core.types import generate_address
        from core.blockchain import PublicKeyRegistry

        # 创建金库账户
        sk = SigningKey.generate(curve=SECP256k1)
        vk = sk.get_verifying_key()
        treasury_addr = generate_address(vk.to_string())
        PublicKeyRegistry.register_public_key(treasury_addr, vk.to_string().hex())

        treasury_acc = world_state.get_account(
            treasury_addr
        ) or world_state.create_account(treasury_addr)
        treasury_acc.balance = 200000
        treasury_acc.reputation = 80
        treasury_acc.stake = 0
        world_state.update_account(treasury_acc)

        # 强制更新 blockchain 的金库地址缓存
        blockchain._treasury_address = treasury_addr
        blockchain._treasury_private_key = sk

        return {"success": True, "message": "System reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-test-data")
async def generate_test_data():
    raise HTTPException(status_code=410, detail="接口已移除，请使用 /api/run-agents")


@app.post("/api/run-agents")
async def run_agents():
    try:
        # 初始化 Agents
        if not hasattr(app, "dao_agents"):
            app.dao_agents = {
                "AlertReceiver": AlertReceiver(),
                "ProcessScheduler": ProcessScheduler(),
                "DataDetective": DataDetective(),
                "DependencyExplorer": DependencyExplorer(),
                "ProbabilityOracle": ProbabilityOracle(),
                "FaultMapper": FaultMapper(),
                "SolutionEngineer": SolutionEngineer(),
            }
        agents_list = list(app.dao_agents.values())

        # 加载数据 (优先使用 root/data, 降级使用 mABC/simple_sample)
        selected_endpoint = "food-buy"
        selected_time = "2023-10-15 14:00:00"

        # Root data paths
        data_stat_path = os.path.join(
            parent_dir, "data", "topology", "endpoints_stat.json"
        )
        data_map_path = os.path.join(
            parent_dir, "data", "topology", "endpoints_maps.json"
        )

        # Simple sample paths
        sample_stat_path = os.path.join(
            parent_dir, "mABC", "simple_sample", "endpoint_stats.json"
        )
        sample_map_path = os.path.join(
            parent_dir, "mABC", "simple_sample", "endpoints_maps.json"
        )

        if os.path.exists(data_stat_path) and os.path.exists(data_map_path):
            stat_path = data_stat_path
            map_path = data_map_path
        elif os.path.exists(sample_stat_path) and os.path.exists(sample_map_path):
            stat_path = sample_stat_path
            map_path = sample_map_path
        else:
            raise HTTPException(
                status_code=500,
                detail=f"缺少数据文件。查找路径: {data_stat_path} 或 {sample_stat_path}",
            )

        endpoint_stats = {}
        endpoint_maps = {}
        try:
            with open(stat_path, "r", encoding="utf-8") as f:
                endpoint_stats = json.load(f)
        except Exception:
            endpoint_stats = {}
        try:
            with open(map_path, "r", encoding="utf-8") as f:
                endpoint_maps = json.load(f)
        except Exception:
            endpoint_maps = {}

        metrics = (
            endpoint_stats.get(selected_endpoint, {}).get(selected_time, {})
        ) or {
            "calls": 95,
            "success_rate": 90.0,
            "error_rate": 10.0,
            "average_duration": 300.0,
            "timeout_rate": 5.0,
        }
        downstreams = endpoint_maps.get(selected_endpoint, {}).get(selected_time, [])

        # 重置 SOP 状态以开始新一轮诊断
        ops_sop_contract.reset_for_testing()

        # 清空日志
        if hasattr(app, "agent_logs"):
            app.agent_logs = []

        # 1. AlertReceiver/System 提交数据收集 (模拟)
        ops_sop_contract.submit_data_collection(
            agent_id=app.dao_agents["AlertReceiver"].wallet_address,
            data_summary=f"{selected_endpoint} 指标异常",
            raw_data={
                "endpoint": selected_endpoint,
                "time": selected_time,
                "metrics": metrics,
                "downstreams": downstreams,
            },
        )

        # 2. 构造分析问题
        question = f"Analyze the root cause of the anomaly in endpoint {selected_endpoint} at time {selected_time}. The metrics are: {metrics}. The downstream dependencies are: {downstreams}."

        # 3. 初始化运行环境
        scheduler = app.dao_agents["ProcessScheduler"]
        dao_executor = DAOExecutor(blockchain)
        run = ReActTotRun()

        print(f"🚀 Starting Multi-Agent Analysis for {selected_endpoint}...")

        # 4. 在线程池中运行同步的 Agent 逻辑
        old_stdout = sys.stdout
        sys.stdout = DualOutput(old_stdout)

        try:
            answer = await run_in_threadpool(
                run.run,
                agent=scheduler,
                question=question,
                agent_tool_env=vars(process_scheduler_tools),
                eval_run=dao_executor,
                agents=agents_list,
                sop_contract=ops_sop_contract,
            )

            voting_status = await get_voting_status()

            return {
                "success": True,
                "message": "七智能体根因分析已完成",
                "final_answer": answer,
                "voting": voting_status,
            }

        except Exception as run_error:
            print(f"❌ Analysis failed: {run_error}")
            raise HTTPException(
                status_code=500, detail=f"智能体分析运行失败: {str(run_error)}"
            )
        finally:
            sys.stdout = old_stdout

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"运行七智能体失败: {str(e)}")


@app.get("/api/state/sop")
async def get_sop_state():
    try:
        current_state = ops_sop_contract.get_current_state()
        current_proposal = ops_sop_contract.get_current_proposal()
        incident_data = ops_sop_contract.get_incident_data()
        events = ops_sop_contract.get_events(limit=100)
        return {
            "current_state": current_state,
            "current_proposal": current_proposal,
            "incident_data": incident_data,
            "events": events,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/events")
async def get_events(limit: Optional[int] = 100):
    try:
        # 获取合约事件
        contract_events = ops_sop_contract.get_events(limit=limit or 100)

        # 获取实时日志
        log_events = (
            app.agent_logs[-(limit or 100) :] if hasattr(app, "agent_logs") else []
        )

        # 合并两者
        all_events = contract_events + log_events

        # 按时间戳排序
        all_events.sort(key=lambda x: x.get("timestamp", 0))

        # 返回最近的 limit 条
        return all_events[-(limit or 100) :]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/state/agents")
async def get_agents_state(limit: Optional[int] = None):
    try:
        # 确保 DAO Agents 初始化，以便正确过滤非系统账户
        if not hasattr(app, "dao_agents"):
            app.dao_agents = {
                "AlertReceiver": AlertReceiver(),
                "ProcessScheduler": ProcessScheduler(),
                "DataDetective": DataDetective(),
                "DependencyExplorer": DependencyExplorer(),
                "ProbabilityOracle": ProbabilityOracle(),
                "FaultMapper": FaultMapper(),
                "SolutionEngineer": SolutionEngineer(),
            }
        # 仅展示系统管理的 DAO Agents，避免把临时/自动创建的提案账户混入经济看板
        agent_addresses = set()
        if hasattr(app, "dao_agents"):
            agent_addresses = {ag.wallet_address for ag in app.dao_agents.values()}
        # 构造只读的核心Agent账户列表，不在此处修改链上状态
        agent_accounts = []
        for account in world_state.state.values():
            if not agent_addresses or account.address in agent_addresses:
                agent_accounts.append(
                    {
                        "address": account.address,
                        "balance": account.balance,
                        "name": account.name,
                        "stake": account.stake,
                        "reputation": account.reputation,
                    }
                )
        agent_accounts.sort(
            key=lambda x: (x["balance"] or 0, x["stake"] or 0, x["reputation"] or 0),
            reverse=True,
        )
        if limit:
            agent_accounts = agent_accounts[:limit]
        # 识别并返回系统金库账户（与七个Agent隔离显示）
        treasury_accounts = []
        treasury = blockchain._get_treasury_account()
        if treasury:
            treasury_accounts.append(
                {
                    "address": treasury.address,
                    "balance": treasury.balance,
                    "stake": treasury.stake,
                    "reputation": treasury.reputation,
                }
            )
        return {
            "accounts": agent_accounts,
            "treasury": treasury_accounts,
            "total": len(agent_accounts),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/economy/overview")
async def get_economy_overview():
    try:
        if not hasattr(app, "dao_agents"):
            app.dao_agents = {
                "AlertReceiver": AlertReceiver(),
                "ProcessScheduler": ProcessScheduler(),
                "DataDetective": DataDetective(),
                "DependencyExplorer": DependencyExplorer(),
                "ProbabilityOracle": ProbabilityOracle(),
                "FaultMapper": FaultMapper(),
                "SolutionEngineer": SolutionEngineer(),
            }
        # 确保 blockchain 知道 Agent 地址
        blockchain.agent_addresses = {
            ag.wallet_address for ag in app.dao_agents.values()
        }

        economy_data = {
            "agent_initial_balance": 20000,
            "gas_price": blockchain.gas_price,
            "min_gas_limit": blockchain.min_gas_limit,
            "vote_gas_limit": 200,
            "reward_gas_limit": 200,
            "proposer_reward_token": 800,
            "proposer_reward_rep": 5,
            "supporter_reward_token": 300,
            "supporter_reward_rep": 1,
            "pass_rebate_ratio": 0.7,
            "bounty_base_token": 1000,
            "penalty_against_pass_token": 50,
            "penalty_against_pass_rep": -1,
            "penalty_support_fail_token": 100,
            "penalty_support_fail_rep": -1,
            "penalty_proposer_fail_token": 300,
            "penalty_proposer_fail_rep": -5,
            "agent_count": 7,
        }

        # 获取系统金库账户
        treasury = blockchain._get_treasury_account()
        if treasury:
            economy_data["treasury_address"] = treasury.address
            economy_data["treasury_balance"] = treasury.balance

        return economy_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/voting/status")
async def get_voting_status():
    try:
        proposal = ops_sop_contract.get_current_proposal()
        if not proposal:
            return {
                "active": False,
                "message": "no active proposal",
                "statistics": {
                    "for": 0,
                    "against": 0,
                    "abstain": 0,
                    "total_network_weight": 0.0,
                    "support_rate": 0.0,
                    "participation_rate": 0.0,
                    "consensus_reached": False,
                },
                "votes": [],
            }

        proposal_id = proposal["proposal_id"]
        proposal_holder = None
        proposal_data = None

        for acc in world_state.state.values():
            if proposal_id in acc.root_cause_proposals:
                proposal_holder = acc.address
                proposal_data = acc.root_cause_proposals[proposal_id]
                break

        votes_for = 0.0
        votes_against = 0.0
        votes_abstain = 0.0
        total_network_weight = 0.0
        votes_list = []
        participants = 0

        for acc in world_state.state.values():
            # 与治理合约一致的权重计算公式
            rep_bonus = max(0.0, (acc.reputation - 50) / 10.0)
            stake_bonus = acc.stake / 1000.0
            weight = 1.0 + rep_bonus + stake_bonus
            total_network_weight += weight
            v = acc.votes.get(proposal_id)
            if v:
                participants += 1
                votes_list.append(
                    {
                        "address": acc.address,
                        "option": v["vote_option"],
                        "weight": v.get("weight", weight),
                    }
                )

        if proposal_data:
            votes_for = proposal_data["votes"]["for"]
            votes_against = proposal_data["votes"]["against"]
            votes_abstain = proposal_data["votes"]["abstain"]

        support_rate = (
            (votes_for / total_network_weight) if total_network_weight > 0 else 0.0
        )
        participation_rate = (
            (participants / max(1, len(world_state.state)))
            if len(world_state.state) > 0
            else 0.0
        )
        consensus_reached = (
            support_rate > 0.5
            or ops_sop_contract.get_current_state() in ["Consensus", "Solution"]
        )

        return {
            "active": True,
            "proposal": {
                "proposal_id": proposal_id,
                "proposer": proposal["proposer"],
                "content": proposal["content"],
                "holder_address": proposal_holder,
            },
            "statistics": {
                "for": votes_for,
                "against": votes_against,
                "abstain": votes_abstain,
                "total_network_weight": total_network_weight,
                "support_rate": support_rate,
                "participation_rate": participation_rate,
                "consensus_reached": consensus_reached,
            },
            "votes": votes_list,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    # 打印所有注册的路由，帮助调试
    print("\n=== Registered Routes ===")
    for route in app.routes:
        print(f"Route: {route.path} [{','.join(route.methods)}]")
    print("=========================\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
