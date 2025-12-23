"""
FastAPI后端API服务器
为前端提供区块链数据接口
"""

import sys
import os

# 添加mABC模块路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
mabc_path = os.path.join(parent_dir, 'mABC')

if os.path.exists(mabc_path):
    if mabc_path not in sys.path:
        sys.path.insert(0, mabc_path)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import json

from core.vm import blockchain
from core.types import Transaction, Block, calculate_hash, get_merkle_root
from core.state import world_state
from contracts.ops_contract import ops_sop_contract

app = FastAPI(title="mABC Blockchain API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BlockResponse(BaseModel):
    index: int
    hash: Optional[str]
    previous_hash: str
    timestamp: int
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
    proof_path: List[Dict[str, str]]
    verified: bool

@app.get("/")
async def root():
    return {"message": "mABC Blockchain API", "version": "1.0.0"}

@app.get("/api/blocks", response_model=List[BlockResponse])
async def get_blocks(limit: Optional[int] = None, offset: Optional[int] = 0):
    try:
        chain = blockchain.chain
        total_blocks = len(chain)
        start = offset or 0
        end = start + limit if limit else total_blocks
        blocks = chain[start:end]
        
        result = []
        for block in blocks:
            tx_list = []
            for tx in block.transactions:
                tx_dict = tx.model_dump()
                # 使用与 get_merkle_root 相同的方式计算交易哈希
                tx_json = str(sorted(tx_dict.items()))
                tx_hash = calculate_hash(tx_json)
                tx_dict['tx_hash'] = tx_hash
                tx_list.append(tx_dict)
            
            result.append(BlockResponse(
                index=block.header.index,
                hash=block.hash,
                previous_hash=block.header.previous_hash,
                timestamp=block.header.timestamp,
                merkle_root=block.header.merkle_root,
                transaction_count=len(block.transactions),
                transactions=tx_list
            ))
        
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
            tx_json = json.dumps(tx_dict, sort_keys=True, separators=(',', ':'))
            tx_hash = calculate_hash(tx_json)
            tx_dict['tx_hash'] = tx_hash
            tx_list.append(tx_dict)
        
        return BlockResponse(
            index=block.header.index,
            hash=block.hash,
            previous_hash=block.header.previous_hash,
            timestamp=block.header.timestamp,
            merkle_root=block.header.merkle_root,
            transaction_count=len(block.transactions),
            transactions=tx_list
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
                # 使用与 get_merkle_root 相同的方式计算交易哈希
                tx_json = str(sorted(tx_dict.items()))
                calculated_hash = calculate_hash(tx_json)
                
                if calculated_hash == tx_hash:
                    tx_dict['tx_hash'] = calculated_hash
                    tx_dict['block_index'] = block.header.index
                    tx_dict['block_hash'] = block.hash
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
            chain_id="mABC-DAO-Chain"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/merkle-proof/{block_index}/{tx_index}", response_model=MerkleProofResponse)
async def get_merkle_proof(block_index: int, tx_index: int):
    try:
        if block_index < 0 or block_index >= len(blockchain.chain):
            raise HTTPException(status_code=404, detail="Block not found")
        
        block = blockchain.chain[block_index]
        
        if tx_index < 0 or tx_index >= len(block.transactions):
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        transaction_hashes = []
        for tx in block.transactions:
            # 使用与 get_merkle_root 相同的方式计算交易哈希
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
                    proof_path.append({
                        "position": "right",
                        "hash": merkle_tree[sibling_index]
                    })
            else:
                sibling_index = current_index - 1
                proof_path.append({
                    "position": "left",
                    "hash": merkle_tree[sibling_index]
                })
            
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
            verified=verified
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
            # 使用与 get_merkle_root 相同的方式计算交易哈希
            tx_json = str(sorted(tx_dict.items()))
            tx_hash = calculate_hash(tx_json)
            tx_dict['tx_hash'] = tx_hash
            result.append(tx_dict)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reset")
async def reset_data():
    raise HTTPException(status_code=410, detail="接口已移除")

@app.post("/api/generate-test-data")
async def generate_test_data():
    raise HTTPException(status_code=410, detail="接口已移除，请使用 /api/run-agents")

@app.post("/api/run-agents")
async def run_agents():
    try:
        from core.client import ChainClient
        from agents.base.profile import DataDetective, DependencyExplorer, ProbabilityOracle, FaultMapper, SolutionEngineer, AlertReceiver, ProcessScheduler
        import json
        import random
        import time
        client = ChainClient(blockchain)
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
        agents = list(app.dao_agents.values())
        for ag in agents:
            acc = world_state.get_account(ag.wallet_address) or world_state.create_account(ag.wallet_address)
            if acc.balance < 20000:
                acc.balance = 20000
            if acc.reputation is None or acc.reputation < 60:
                acc.reputation = 80
            world_state.update_account(acc)
        selected_endpoint = "food-buy"
        selected_time = "2023-10-15 14:00:00"
        data_stat_path = os.path.join(parent_dir, "mABC", "data", "metric", "endpoint_stats.json")
        data_map_path = os.path.join(parent_dir, "mABC", "data", "topology", "endpoint_maps.json")
        sample_stat_path = os.path.join(parent_dir, "mABC", "simple_sample", "endpoints_stat.json")
        sample_map_path = os.path.join(parent_dir, "mABC", "simple_sample", "endpoints_maps.json")
        stat_path = data_stat_path if (os.path.exists(data_stat_path) and os.path.exists(data_map_path)) else None
        map_path = data_map_path if stat_path else None
        if stat_path is None or map_path is None:
            if os.path.exists(sample_stat_path) and os.path.exists(sample_map_path):
                stat_path = sample_stat_path
                map_path = sample_map_path
            else:
                raise HTTPException(status_code=500, detail="缺少 mABC/data 的指标或拓扑文件")
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
        metrics = (endpoint_stats.get(selected_endpoint, {}).get(selected_time, {})) or {
            "calls": 95,
            "success_rate": 90.0,
            "error_rate": 10.0,
            "average_duration": 300.0,
            "timeout_rate": 5.0
        }
        downstreams = endpoint_maps.get(selected_endpoint, {}).get(selected_time, [])
        ops_sop_contract.reset_for_testing()
        ops_sop_contract.submit_data_collection(
            agent_id=agents[0].wallet_address,
            data_summary=f"{selected_endpoint} 指标异常",
            raw_data={"endpoint": selected_endpoint, "time": selected_time, "metrics": metrics, "downstreams": downstreams}
        )
        proposer = app.dao_agents["ProcessScheduler"]
        proposal_content = f"{selected_endpoint} 出现异常，可能由下游 {','.join(downstreams) or '未知下游'} 引发；平均耗时 {metrics.get('average_duration', 0)}ms，错误率 {metrics.get('error_rate', 0)}%"
        res_proposal = ops_sop_contract.propose_root_cause(
            agent_id=proposer.wallet_address,
            content=proposal_content
        )
        proposal_id = res_proposal["proposal_id"]
        # 同步提案到世界状态，供治理合约投票权重统计
        proposer_acc = world_state.get_account(proposer.wallet_address) or world_state.create_account(proposer.wallet_address)
        proposer_acc.root_cause_proposals[proposal_id] = {
            "proposal_id": proposal_id,
            "proposer": proposer.wallet_address,
            "content": proposal_content,
            "timestamp": int(time.time()),
            "votes": {"for": 0, "against": 0, "abstain": 0}
        }
        world_state.update_account(proposer_acc)
        transactions_created = 0
        for ag in agents:
            stake_amount = random.randint(1000, 5000)
            tx_stake = client.create_transaction(
                tx_type="stake",
                sender=ag.wallet_address,
                data={"amount": stake_amount},
                private_key=ag.private_key
            )
            if client.send_and_mine(tx_stake):
                transactions_created += 1
        vote_options = []
        base_condition = (metrics.get("error_rate", 0) >= 10.0) or (metrics.get("average_duration", 0) >= 250.0)
        for ag in agents:
            rnd = random.random()
            if rnd < 0.1:
                opt = "abstain"
            else:
                opt = "for" if base_condition else ("against" if rnd < 0.6 else "for")
            vote_options.append(opt)
            tx_vote = client.create_transaction(
                tx_type="vote",
                sender=ag.wallet_address,
                data={"proposal_id": proposal_id, "vote_option": opt},
                private_key=ag.private_key
            )
            if client.send_and_mine(tx_vote):
                transactions_created += 1
        voting_status = await get_voting_status()
        return {
            "success": True,
            "message": "七智能体根因分析与链上投票完成",
            "agents_involved": len(agents),
            "proposal_id": proposal_id,
            "transactions_created": transactions_created,
            "voting": voting_status
        }
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
            "events": events
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/events")
async def get_events(limit: Optional[int] = 100):
    try:
        return ops_sop_contract.get_events(limit=limit or 100)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/state/agents")
async def get_agents_state(limit: Optional[int] = None):
    try:
        accounts = []
        for account in world_state.state.values():
            accounts.append({
                "address": account.address,
                "balance": account.balance,
                "stake": account.stake,
                "reputation": account.reputation
            })
        accounts.sort(key=lambda x: (x["balance"], x["stake"], x["reputation"]), reverse=True)
        if limit:
            accounts = accounts[:limit]
        return {"accounts": accounts, "total": len(world_state.state)}
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
                    "consensus_reached": False
                },
                "votes": []
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
            weight = max(1.0, acc.stake * (acc.reputation / 100.0))
            total_network_weight += weight
            v = acc.votes.get(proposal_id)
            if v:
                participants += 1
                votes_list.append({
                    "address": acc.address,
                    "option": v["vote_option"],
                    "weight": v["weight"]
                })
        if proposal_data:
            votes_for = proposal_data["votes"]["for"]
            votes_against = proposal_data["votes"]["against"]
            votes_abstain = proposal_data["votes"]["abstain"]
        support_rate = (votes_for / total_network_weight) if total_network_weight > 0 else 0.0
        participation_rate = (participants / max(1, len(world_state.state))) if len(world_state.state) > 0 else 0.0
        consensus_reached = support_rate > 0.5 or ops_sop_contract.get_current_state() in ["Consensus", "Solution"]
        return {
            "active": True,
            "proposal": {
                "proposal_id": proposal_id,
                "proposer": proposal["proposer"],
                "content": proposal["content"],
                "holder_address": proposal_holder
            },
            "statistics": {
                "for": votes_for,
                "against": votes_against,
                "abstain": votes_abstain,
                "total_network_weight": total_network_weight,
                "support_rate": support_rate,
                "participation_rate": participation_rate,
                "consensus_reached": consensus_reached
            },
            "votes": votes_list
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
