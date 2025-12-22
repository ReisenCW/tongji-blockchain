import axios from 'axios'

const API_BASE_URL = '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
    'Expires': '0',
  },
})

// 添加请求拦截器，为每个 GET 请求增加时间戳
api.interceptors.request.use((config) => {
  if (config.method === 'get') {
    config.params = { ...config.params, _t: Date.now() }
  }
  return config
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

  getSOPState: async () => {
    const response = await api.get('/state/sop')
    return response.data
  },

  getEvents: async (limit = 100) => {
    const response = await api.get('/events', { params: { limit } })
    return response.data
  },

  getAgentsState: async (limit) => {
    const params = {}
    if (limit) params.limit = limit
    const response = await api.get('/state/agents', { params })
    return response.data
  },

  getVotingStatus: async () => {
    const response = await api.get('/voting/status')
    return response.data
  },

  generateTestData: async () => {
    const response = await api.post('/generate-test-data')
    return response.data
  },

  resetData: async () => {
    const response = await api.post('/reset')
    return response.data
  },
}

export default api

