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
    try:
        # Reset Blockchain
        blockchain.chain = []
        blockchain.pending_transactions = []
        blockchain._create_genesis_block()
        
        # Reset World State
        world_state.state = {}
        try:
            conn = world_state._get_db_connection()
            conn.execute("DELETE FROM accounts")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error clearing DB: {e}")
            
        # Reset SOP Contract
        ops_sop_contract.reset_for_testing()
        
        return {"success": True, "message": "System data reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-test-data")
async def generate_test_data():
    try:
        from ecdsa import SigningKey, SECP256k1
        from core.client import ChainClient
        from core.types import generate_address
        from core.blockchain import PublicKeyRegistry
        
        import random
        
        client = ChainClient(blockchain)
        
        # 1. 获取现有账户或创建新账户
        accounts = []
        existing_accounts = list(world_state.state.values())
        
        # 简单的内存缓存，用于存储生成的私钥 (仅用于演示，重启丢失)
        if not hasattr(app, "demo_private_keys"):
            app.demo_private_keys = {}
            
        if len(existing_accounts) < 5:
            # 如果账户不足5个，补充创建 (系统初始化或恢复)
            for i in range(5 - len(existing_accounts)):
                private_key = SigningKey.generate(curve=SECP256k1)
                public_key = private_key.get_verifying_key()
                address = generate_address(public_key.to_string())
                
                PublicKeyRegistry.register_public_key(
                    address,
                    public_key.to_string().hex()
                )
                
                account = world_state.create_account(address)
                account.balance = random.randint(10000, 80000)
                account.reputation = random.randint(80, 100)
                world_state.update_account(account)
                
                app.demo_private_keys[address] = private_key
                accounts.append({'address': address, 'private_key': private_key})
        
        # [新增] 模拟真实场景：动态扩容
        # 10% 的概率会有新 Agent 加入网络 (模拟节点上线/扩容)
        elif random.random() < 0.1:
            print("Simulating Network Expansion: New Agent Joining...")
            private_key = SigningKey.generate(curve=SECP256k1)
            public_key = private_key.get_verifying_key()
            address = generate_address(public_key.to_string())
            
            PublicKeyRegistry.register_public_key(
                address,
                public_key.to_string().hex()
            )
            
            account = world_state.create_account(address)
            account.balance = random.randint(5000, 20000) # 新节点初始资金较少
            account.reputation = 60 # 新节点初始信誉较低
            world_state.update_account(account)
            
            app.demo_private_keys[address] = private_key
            # 将新 Agent 也加入到当次可用的 accounts 列表中
            accounts.append({'address': address, 'private_key': private_key})
            
            # 记录一个特殊的“节点加入”日志事件，让前端能看到
            ops_sop_contract.submit_data_collection(
                agent_id=address,
                data_summary="新节点入网注册",
                raw_data={"event": "node_join", "version": "v1.2.0", "status": "online"}
            )
        else:
            # 如果已有账户，使用现有账户
            # 注意：这里我们只能使用我们在内存中保存了私钥的账户
            for acc in existing_accounts:
                if acc.address in app.demo_private_keys:
                    accounts.append({
                        'address': acc.address, 
                        'private_key': app.demo_private_keys[acc.address]
                    })
            
            # 如果所有现有账户都没有私钥（比如重启服务后），则必须强制创建新账户
            if not accounts:
                print("Warning: Existing accounts found but private keys lost. Creating new accounts.")
                for i in range(5):
                    private_key = SigningKey.generate(curve=SECP256k1)
                    public_key = private_key.get_verifying_key()
                    address = generate_address(public_key.to_string())
                    PublicKeyRegistry.register_public_key(address, public_key.to_string().hex())
                    account = world_state.create_account(address)
                    account.balance = random.randint(10000, 80000)
                    account.reputation = random.randint(80, 100)
                    world_state.update_account(account)
                    app.demo_private_keys[address] = private_key
                    accounts.append({'address': address, 'private_key': private_key})
        
        # 确保 accounts 不为空
        if not accounts:
             raise HTTPException(status_code=500, detail="No available accounts with private keys")

        transactions_created = 0
        
        # 随机生成一些交易
        if len(accounts) >= 2:
            num_txs = random.randint(3, 8)
            for _ in range(num_txs):
                sender_idx = random.randint(0, len(accounts)-1)
                receiver_idx = (sender_idx + random.randint(1, len(accounts)-1)) % len(accounts)
                
                tx = client.create_transaction(
                    tx_type="transfer",
                    sender=accounts[sender_idx]['address'],
                    data={"to": accounts[receiver_idx]['address'], "amount": random.randint(100, 2000)},
                    private_key=accounts[sender_idx]['private_key']
                )
                if client.send_transaction(tx):
                    transactions_created += 1

        # 随机Stake
        for i in range(len(accounts)):
            if random.random() > 0.3: # 70% 概率质押
                tx = client.create_transaction(
                    tx_type="stake",
                    sender=accounts[i]['address'],
                    data={"amount": random.randint(1000, 10000)},
                    private_key=accounts[i]['private_key']
                )
                if client.send_transaction(tx):
                    transactions_created += 1
        
        block1 = client.mine_block()
        block1_info = None
        if block1:
            block1_info = {
                "index": block1.header.index,
                "transactions": len(block1.transactions)
            }
        
        # 模拟SOP流程事件，填充日志流
        ops_sop_contract.storage["current_state"] = "Init"
        ops_sop_contract.storage["events"] = []
        ops_sop_contract.storage["proposals"] = {}
        
        # 随机选择一个场景（故障或健康）
        scenarios = [
            {
                "incident": "系统例行健康巡检 - 各项指标正常",
                "raw": {"cpu": 15, "memory": 20, "latency": 45, "status": "healthy"},
                "causes": ["系统运行状况良好，无需干预", "资源负载均衡，性能优异", "网络连接稳定"]
            },
            {
                "incident": "检测到节点3 CPU使用率异常 (95%)",
                "raw": {"cpu": 95, "memory": 80, "node_id": "node-3"},
                "causes": ["共识算法死循环", "非法交易泛洪攻击", "加密计算模块过载"]
            },
            {
                "incident": "节点1 内存占用持续攀升 (92%)",
                "raw": {"cpu": 40, "memory": 92, "node_id": "node-1"},
                "causes": ["交易池内存泄漏导致处理延迟", "区块缓存未及时释放", "状态树膨胀"]
            },
            {
                "incident": "P2P 网络广播延迟超过阈值 (500ms)",
                "raw": {"latency": 520, "packet_loss": 0.05, "node_id": "all"},
                "causes": ["部分节点带宽被占用", "路由表更新异常", "DDoS攻击"]
            },
            {
                "incident": "节点4 磁盘空间不足 (剩余 5%)",
                "raw": {"disk_usage": 95, "inode_usage": 60, "node_id": "node-4"},
                "causes": ["日志文件切割失败", "历史区块数据冗余", "本地数据库损坏"]
            }
        ]
        
        selected_scenario = random.choice(scenarios)
        selected_cause = random.choice(selected_scenario["causes"])
        
        # 1. 数据采集事件
        ops_sop_contract.submit_data_collection(
            agent_id=accounts[0]['address'],
            data_summary=selected_scenario["incident"],
            raw_data=selected_scenario["raw"]
        )
        
        # 2. 根因分析提案事件 (随机选择一个Agent发起)
        proposer_idx = random.randint(0, len(accounts)-1)
        res_proposal = ops_sop_contract.propose_root_cause(
            agent_id=accounts[proposer_idx]['address'],
            content=selected_cause
        )
        # 手动同步到 Proposer 的账户状态中
        proposer_acc = world_state.get_account(accounts[proposer_idx]['address'])
        if proposer_acc:
            proposal_id = res_proposal['proposal_id']
            proposer_acc.root_cause_proposals[proposal_id] = {
                "proposal_id": proposal_id,
                "content": selected_cause,
                "timestamp": 1234567890,
                "votes": {"for": 0, "against": 0, "abstain": 0},
                "status": "active"
            }
            world_state.update_account(proposer_acc)
        
        # 3. 模拟投票
        current_proposal = ops_sop_contract.get_current_proposal()
        if current_proposal:
            proposal_id = current_proposal['proposal_id']
            
            votes_for_sum = 0
            votes_against_sum = 0
            votes_abstain_sum = 0
            
            # 其他 Agent 随机投票
            for i in range(len(accounts)):
                if i == proposer_idx:
                    continue
                    
                # 80% 概率参与投票
                if random.random() > 0.2:
                    acc = world_state.get_account(accounts[i]['address'])
                    vote_weight = max(1.0, acc.stake * (acc.reputation / 100.0))
                    
                    # 70% 概率投赞成票
                    vote_option = "for" if random.random() > 0.3 else "against"
                    
                    acc.votes[proposal_id] = {
                        "vote_option": vote_option,
                        "weight": vote_weight,
                        "timestamp": 1234567890
                    }
                    world_state.update_account(acc)
                    
                    if vote_option == "for":
                        votes_for_sum += vote_weight
                    else:
                        votes_against_sum += vote_weight
            
            # 更新Proposal中的投票统计
            proposer_acc = world_state.get_account(accounts[proposer_idx]['address'])
            if proposal_id in proposer_acc.root_cause_proposals:
                 proposer_acc.root_cause_proposals[proposal_id]["votes"] = {
                     "for": votes_for_sum,
                     "against": votes_against_sum,
                     "abstain": votes_abstain_sum
                 }
                 world_state.update_account(proposer_acc)
        
        print(f"DEBUG: Generated test data. Current state: {ops_sop_contract.storage['current_state']}")
        print(f"DEBUG: Events count: {len(ops_sop_contract.storage['events'])}")

        return {
            "success": True,
            "message": "测试数据生成成功",
            "accounts_created": len(accounts),
            "transactions_created": transactions_created,
            "blocks_mined": [block1_info],
            "current_block_height": len(blockchain.chain),
            "pending_transactions": len(blockchain.pending_transactions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成测试数据失败: {str(e)}")

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
