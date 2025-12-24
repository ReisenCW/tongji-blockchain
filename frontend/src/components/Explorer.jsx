import React, { useState, useEffect } from 'react'
import { Tabs, Card, Tag, Button, Space, message } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import { blockchainAPI } from '../utils/api'
import BlockChainView from './BlockChainView'
import TransactionView from './TransactionView'
import AuditView from './AuditView'
import Dashboard from './Dashboard'
import './Explorer.css'

const { TabPane } = Tabs

function Explorer() {
  const [blockchainInfo, setBlockchainInfo] = useState(null)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('blocks')
  // counters used to trigger refresh in child components when tab becomes active
  const [refreshCounters, setRefreshCounters] = useState({
    blocks: 0,
    transactions: 0,
    audit: 0,
    dashboard: 0,
  })

  const handleTabChange = (key) => {
    setActiveTab(key)
    setRefreshCounters(prev => ({ ...prev, [key]: (prev[key] || 0) + 1 }))
  }

  useEffect(() => {
    loadBlockchainInfo()
    // 每5秒刷新一次区块链信息
    const interval = setInterval(loadBlockchainInfo, 5000)
    return () => clearInterval(interval)
  }, [])

  const loadBlockchainInfo = async () => {
    try {
      const info = await blockchainAPI.getBlockchainInfo()
      setBlockchainInfo(info)
    } catch (error) {
      console.error('Failed to load blockchain info:', error)
    }
  }

  const handleRefresh = () => {
    loadBlockchainInfo()
    message.success('已刷新')
  }

  return (
    <div className="explorer-container">
      {/* 区块链信息卡片 */}
      <Card className="info-card" style={{ marginBottom: 24 }}>
        <Space size="large" style={{ width: '100%', justifyContent: 'space-between' }}>
          <div>
            <h2 style={{ margin: 0, marginBottom: 8 }}>区块链概览</h2>
            {blockchainInfo && (
              <Space size="large">
                <span>
                  <strong>区块高度:</strong> {blockchainInfo.block_height}
                </span>
                <span>
                  <strong>待处理交易:</strong> {blockchainInfo.pending_transactions}
                </span>
                <span>
                  <strong>链ID:</strong> {blockchainInfo.chain_id}
                </span>
                {blockchainInfo.latest_block_hash && (
                  <span>
                    <strong>最新区块哈希:</strong>{' '}
                    <code style={{ fontSize: '12px' }}>
                      {blockchainInfo.latest_block_hash.substring(0, 16)}...
                    </code>
                  </span>
                )}
              </Space>
            )}
          </div>
          <Button 
            icon={<ReloadOutlined />} 
            onClick={handleRefresh}
            loading={loading}
          >
            刷新
          </Button>
        </Space>
      </Card>

      {/* 主内容区域 */}
      <Card>
        <Tabs activeKey={activeTab} onChange={handleTabChange} size="large">
          <TabPane tab="区块浏览器" key="blocks">
            <BlockChainView refreshKey={refreshCounters.blocks} />
          </TabPane>
          <TabPane tab="交易追踪" key="transactions">
            <TransactionView refreshKey={refreshCounters.transactions} />
          </TabPane>
          <TabPane tab="审计视图" key="audit">
            <AuditView refreshKey={refreshCounters.audit} />
          </TabPane>
          <TabPane tab="运维控制台" key="dashboard">
            <Dashboard refreshKey={refreshCounters.dashboard} />
          </TabPane>
        </Tabs>
      </Card>
    </div>
  )
}

export default Explorer

