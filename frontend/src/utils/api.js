import axios from 'axios'

const API_BASE_URL = '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
})

export const blockchainAPI = {
  // 获取区块列表
  getBlocks: async (limit, offset = 0) => {
    const params = {}
    if (limit) params.limit = limit
    if (offset) params.offset = offset
    const response = await api.get('/blocks', { params })
    return response.data
  },

  // 获取单个区块
  getBlock: async (index) => {
    const response = await api.get(`/block/${index}`)
    return response.data
  },

  // 获取交易详情
  getTransaction: async (txHash) => {
    const response = await api.get(`/transaction/${txHash}`)
    return response.data
  },

  // 获取区块链信息
  getBlockchainInfo: async () => {
    const response = await api.get('/blockchain/info')
    return response.data
  },

  // 获取Merkle Proof
  getMerkleProof: async (blockIndex, txIndex) => {
    const response = await api.get(`/merkle-proof/${blockIndex}/${txIndex}`)
    return response.data
  },

  // 获取待处理交易
  getPendingTransactions: async () => {
    const response = await api.get('/pending-transactions')
    return response.data
  },
}

export default api

