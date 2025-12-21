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

@app.post("/api/generate-test-data")
async def generate_test_data():
    try:
        from ecdsa import SigningKey, SECP256k1
        from core.client import ChainClient
        from core.state import world_state
        from core.types import generate_address
        from core.blockchain import PublicKeyRegistry
        
        client = ChainClient(blockchain)
        
        accounts = []
        for i in range(5):
            private_key = SigningKey.generate(curve=SECP256k1)
            public_key = private_key.get_verifying_key()
            address = generate_address(public_key.to_string())
            
            PublicKeyRegistry.register_public_key(
                address,
                public_key.to_string().hex()
            )
            
            account = world_state.get_account(address)
            if account is None:
                account = world_state.create_account(address)
            account.balance = 50000
            account.reputation = 100
            world_state.update_account(account)
            
            accounts.append({
                'address': address,
                'private_key': private_key
            })
        
        transactions_created = 0
        
        if len(accounts) >= 2:
            tx = client.create_transaction(
                tx_type="transfer",
                sender=accounts[0]['address'],
                data={"to": accounts[1]['address'], "amount": 1000},
                private_key=accounts[0]['private_key']
            )
            if client.send_transaction(tx):
                transactions_created += 1
        
        if len(accounts) >= 1:
            tx = client.create_transaction(
                tx_type="stake",
                sender=accounts[0]['address'],
                data={"amount": 5000},
                private_key=accounts[0]['private_key']
            )
            if client.send_transaction(tx):
                transactions_created += 1
        
        for i in range(2, min(4, len(accounts))):
            tx = client.create_transaction(
                tx_type="transfer",
                sender=accounts[i]['address'],
                data={"to": accounts[(i+1) % len(accounts)]['address'], "amount": 500 + i * 100},
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
        
        for i in range(min(3, len(accounts))):
            tx = client.create_transaction(
                tx_type="transfer",
                sender=accounts[i]['address'],
                data={"to": accounts[(i+1) % len(accounts)]['address'], "amount": 200 + i * 50},
                private_key=accounts[i]['private_key']
            )
            client.send_transaction(tx)
        
        block2 = client.mine_block()
        block2_info = None
        if block2:
            block2_info = {
                "index": block2.header.index,
                "transactions": len(block2.transactions)
            }
        
        return {
            "success": True,
            "message": "测试数据生成成功",
            "accounts_created": len(accounts),
            "transactions_created": transactions_created,
            "blocks_mined": [block1_info, block2_info],
            "current_block_height": len(blockchain.chain),
            "pending_transactions": len(blockchain.pending_transactions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成测试数据失败: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
