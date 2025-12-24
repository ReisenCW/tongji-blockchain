import React, { useState, useEffect } from 'react'
import { Card, Table, Descriptions, Tag, Input, Button, Space, message, Empty, Tabs } from 'antd'
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons'
import { blockchainAPI } from '../utils/api'
import dayjs from 'dayjs'

const { TabPane } = Tabs

function TransactionView({ refreshKey }) {
  const [searchHash, setSearchHash] = useState('')
  const [transaction, setTransaction] = useState(null)
  const [loading, setLoading] = useState(false)
  const [pendingTxs, setPendingTxs] = useState([])
  const [allTransactions, setAllTransactions] = useState([])

  useEffect(() => {
    loadPendingTransactions()
    loadAllTransactions()
    // 每3秒刷新待处理交易
    const interval = setInterval(loadPendingTransactions, 3000)
    return () => clearInterval(interval)
  }, [])

  // 当选中 "交易追踪" Tab 时触发刷新
  useEffect(() => {
    if (refreshKey !== undefined) {
      loadPendingTransactions()
      loadAllTransactions()
    }
  }, [refreshKey])

  const loadPendingTransactions = async () => {
    try {
      const data = await blockchainAPI.getPendingTransactions()
      setPendingTxs(data)
    } catch (error) {
      console.error('Failed to load pending transactions:', error)
    }
  }

  const loadAllTransactions = async () => {
    try {
      const blocks = await blockchainAPI.getBlocks(100) // 获取最近100个区块
      const txs = []
      blocks.forEach(block => {
        block.transactions.forEach(tx => {
          txs.push({
            ...tx,
            blockIndex: block.index,
            blockHash: block.hash,
            timestamp: block.timestamp,
          })
        })
      })
      setAllTransactions(txs.reverse()) // 最新的在前
    } catch (error) {
      console.error('Failed to load transactions:', error)
    }
  }

  const handleSearch = async () => {
    if (!searchHash.trim()) {
      message.warning('请输入交易哈希')
      return
    }

    setLoading(true)
    try {
      const tx = await blockchainAPI.getTransaction(searchHash.trim())
      setTransaction(tx)
    } catch (error) {
      message.error('交易未找到: ' + error.message)
      setTransaction(null)
    } finally {
      setLoading(false)
    }
  }

  const txColumns = [
    {
      title: '交易哈希',
      dataIndex: 'tx_hash',
      key: 'tx_hash',
      ellipsis: true,
      render: (hash) => (
        <code style={{ fontSize: '11px' }}>
          {hash ? `${hash.substring(0, 16)}...${hash.substring(hash.length - 8)}` : 'N/A'}
        </code>
      ),
    },
    {
      title: '类型',
      dataIndex: 'tx_type',
      key: 'tx_type',
      width: 150,
      render: (type) => {
        const colors = {
          propose_root_cause: 'purple',
          vote: 'blue',
          transfer: 'green',
          stake: 'orange',
          slash: 'red',
        }
        return <Tag color={colors[type] || 'default'}>{type}</Tag>
      },
    },
    {
      title: '发送方',
      dataIndex: 'sender',
      key: 'sender',
      ellipsis: true,
      render: (sender) => <code style={{ fontSize: '11px' }}>{sender}</code>,
    },
    {
      title: '接收方',
      key: 'receiver',
      ellipsis: true,
      render: (_, record) => {
        const receiver = record.data?.target || '-'
        return <code style={{ fontSize: '11px' }}>{receiver}</code>
      },
    },
    {
      title: '区块',
      dataIndex: 'blockIndex',
      key: 'blockIndex',
      width: 100,
      render: (index) => index !== undefined ? `#${index}` : <Tag color="orange">待处理</Tag>,
    },
    {
      title: 'Gas',
      key: 'gas',
      width: 120,
      render: (_, record) => `${record.gas_price} × ${record.gas_limit}`,
    },
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
      render: (timestamp) => timestamp ? dayjs(timestamp * 1000).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
  ]

  return (
    <div>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* 交易搜索 */}
        <Card title="交易搜索">
          <Space.Compact style={{ width: '100%' }}>
            <Input
              placeholder="输入交易哈希进行搜索"
              value={searchHash}
              onChange={(e) => setSearchHash(e.target.value)}
              onPressEnter={handleSearch}
              style={{ flex: 1 }}
            />
            <Button
              type="primary"
              icon={<SearchOutlined />}
              onClick={handleSearch}
              loading={loading}
            >
              搜索
            </Button>
          </Space.Compact>
        </Card>

        {/* 交易详情 */}
        {transaction && (
          <Card
            title="交易详情"
            extra={<Button onClick={() => setTransaction(null)}>关闭</Button>}
          >
            <Descriptions bordered column={2}>
              <Descriptions.Item label="交易哈希">
                <code>{transaction.tx_hash}</code>
              </Descriptions.Item>
              <Descriptions.Item label="交易类型">
                <Tag>{transaction.tx_type}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="发送方">
                <code>{transaction.sender}</code>
              </Descriptions.Item>
              <Descriptions.Item label="接收方">
                <code>{transaction.receiver || transaction.to || transaction.data?.to || transaction.data?.target || '-'}</code>
              </Descriptions.Item>
              <Descriptions.Item label="Nonce">
                {transaction.nonce}
              </Descriptions.Item>
              <Descriptions.Item label="Gas价格">
                {transaction.gas_price}
              </Descriptions.Item>
              <Descriptions.Item label="Gas限制">
                {transaction.gas_limit}
              </Descriptions.Item>
              <Descriptions.Item label="Gas费用">
                {transaction.gas_price * transaction.gas_limit}
              </Descriptions.Item>
              <Descriptions.Item label="时间戳">
                {dayjs(transaction.timestamp * 1000).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              {transaction.block_index !== undefined && (
                <>
                  <Descriptions.Item label="区块高度">
                    #{transaction.block_index}
                  </Descriptions.Item>
                  <Descriptions.Item label="区块哈希">
                    <code style={{ fontSize: '11px' }}>
                      {transaction.block_hash}
                    </code>
                  </Descriptions.Item>
                </>
              )}
            </Descriptions>

            {/* Payload数据 */}
            <div style={{ marginTop: 24 }}>
              <h3>Payload数据</h3>
              <Card>
                <pre style={{ 
                  background: '#f5f5f5', 
                  padding: 16, 
                  borderRadius: 4,
                  overflow: 'auto',
                  maxHeight: 400
                }}>
                  {JSON.stringify(transaction.data, null, 2)}
                </pre>
              </Card>
            </div>

            {/* 执行结果 */}
            <div style={{ marginTop: 24 }}>
              <h3>执行结果</h3>
              <Card>
                {transaction.block_index !== undefined ? (
                  <Tag color="green" icon={<span>✓</span>} style={{ fontSize: 14, padding: '8px 16px' }}>
                    交易已成功上链 (区块 #{transaction.block_index})
                  </Tag>
                ) : (
                  <Tag color="orange" style={{ fontSize: 14, padding: '8px 16px' }}>
                    交易待处理中
                  </Tag>
                )}
              </Card>
            </div>
          </Card>
        )}

        {/* 交易列表 */}
        <Card
          title="交易列表"
          extra={
            <Button icon={<ReloadOutlined />} onClick={loadAllTransactions}>
              刷新
            </Button>
          }
        >
          <Tabs defaultActiveKey="all">
            <TabPane tab={`全部交易 (${allTransactions.length})`} key="all">
              <Table
                dataSource={allTransactions}
                columns={txColumns}
                rowKey="tx_hash"
                pagination={{
                  pageSize: 20,
                  showTotal: (total) => `共 ${total} 笔交易`,
                }}
                scroll={{ x: 1000 }}
              />
            </TabPane>
            <TabPane tab={`待处理交易 (${pendingTxs.length})`} key="pending">
              {pendingTxs.length > 0 ? (
                <Table
                  dataSource={pendingTxs.map(tx => ({
                    ...tx,
                    blockIndex: undefined,
                    timestamp: undefined,
                  }))}
                  columns={txColumns}
                  rowKey="tx_hash"
                  pagination={false}
                  scroll={{ x: 1000 }}
                />
              ) : (
                <Empty description="暂无待处理交易" />
              )}
            </TabPane>
          </Tabs>
        </Card>
      </Space>
    </div>
  )
}

export default TransactionView

