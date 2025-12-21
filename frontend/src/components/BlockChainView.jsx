import React, { useState, useEffect } from 'react'
import { Table, Card, Descriptions, Tag, Button, Space, message, Spin, Empty } from 'antd'
import { EyeOutlined, ArrowRightOutlined } from '@ant-design/icons'
import { blockchainAPI } from '../utils/api'
import dayjs from 'dayjs'

function BlockChainView() {
  const [blocks, setBlocks] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedBlock, setSelectedBlock] = useState(null)
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0,
  })

  useEffect(() => {
    loadBlocks()
  }, [pagination.current, pagination.pageSize])

  const loadBlocks = async () => {
    setLoading(true)
    try {
      const offset = (pagination.current - 1) * pagination.pageSize
      const limit = pagination.pageSize
      const data = await blockchainAPI.getBlocks(limit, offset)
      
      // 获取总数
      const info = await blockchainAPI.getBlockchainInfo()
      
      setBlocks(data.reverse()) // 最新的在前
      setPagination(prev => ({
        ...prev,
        total: info.block_height,
      }))
    } catch (error) {
      message.error('加载区块失败: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  const handleViewBlock = async (index) => {
    try {
      const block = await blockchainAPI.getBlock(index)
      setSelectedBlock(block)
    } catch (error) {
      message.error('加载区块详情失败: ' + error.message)
    }
  }

  const columns = [
    {
      title: '区块高度',
      dataIndex: 'index',
      key: 'index',
      width: 100,
      sorter: (a, b) => b.index - a.index,
      render: (index) => <strong>#{index}</strong>,
    },
    {
      title: '区块哈希',
      dataIndex: 'hash',
      key: 'hash',
      ellipsis: true,
      render: (hash) => (
        <code style={{ fontSize: '12px' }}>
          {hash ? `${hash.substring(0, 16)}...${hash.substring(hash.length - 8)}` : 'N/A'}
        </code>
      ),
    },
    {
      title: '前一区块哈希',
      dataIndex: 'previous_hash',
      key: 'previous_hash',
      ellipsis: true,
      render: (hash) => (
        <code style={{ fontSize: '12px' }}>
          {hash ? `${hash.substring(0, 16)}...${hash.substring(hash.length - 8)}` : 'Genesis'}
        </code>
      ),
    },
    {
      title: 'Merkle根',
      dataIndex: 'merkle_root',
      key: 'merkle_root',
      ellipsis: true,
      render: (root) => (
        <code style={{ fontSize: '12px' }}>
          {root ? `${root.substring(0, 16)}...${root.substring(root.length - 8)}` : 'N/A'}
        </code>
      ),
    },
    {
      title: '交易数量',
      dataIndex: 'transaction_count',
      key: 'transaction_count',
      width: 100,
      render: (count) => <Tag color="blue">{count}</Tag>,
    },
    {
      title: '时间戳',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
      render: (timestamp) => dayjs(timestamp * 1000).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_, record) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => handleViewBlock(record.index)}
        >
          查看详情
        </Button>
      ),
    },
  ]

  return (
    <div>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* 区块列表 */}
        <Card title="区块列表" extra={<Button onClick={loadBlocks}>刷新</Button>}>
          <Table
            columns={columns}
            dataSource={blocks}
            loading={loading}
            rowKey="index"
            pagination={{
              ...pagination,
              showSizeChanger: true,
              showTotal: (total) => `共 ${total} 个区块`,
              onChange: (page, pageSize) => {
                setPagination(prev => ({
                  ...prev,
                  current: page,
                  pageSize: pageSize,
                }))
              },
            }}
          />
        </Card>

        {/* 区块详情 */}
        {selectedBlock && (
          <Card
            title={`区块详情 #${selectedBlock.index}`}
            extra={
              <Button onClick={() => setSelectedBlock(null)}>关闭</Button>
            }
          >
            <Descriptions bordered column={2}>
              <Descriptions.Item label="区块高度">
                <strong>#{selectedBlock.index}</strong>
              </Descriptions.Item>
              <Descriptions.Item label="区块哈希">
                <code>{selectedBlock.hash}</code>
              </Descriptions.Item>
              <Descriptions.Item label="前一区块哈希">
                <code>{selectedBlock.previous_hash || 'Genesis Block'}</code>
              </Descriptions.Item>
              <Descriptions.Item label="Merkle根">
                <code>{selectedBlock.merkle_root}</code>
              </Descriptions.Item>
              <Descriptions.Item label="时间戳">
                {dayjs(selectedBlock.timestamp * 1000).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="交易数量">
                <Tag color="blue">{selectedBlock.transaction_count}</Tag>
              </Descriptions.Item>
            </Descriptions>

            {/* 链式结构可视化 */}
            <div style={{ marginTop: 24 }}>
              <h3>链式结构</h3>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
                {selectedBlock.index > 0 && (
                  <>
                    <div style={{ textAlign: 'center' }}>
                      <Card size="small" style={{ width: 200 }}>
                        <div>Block #{selectedBlock.index - 1}</div>
                        <code style={{ fontSize: '10px' }}>
                          {selectedBlock.previous_hash.substring(0, 12)}...
                        </code>
                      </Card>
                    </div>
                    <ArrowRightOutlined style={{ fontSize: 24, color: '#1890ff' }} />
                  </>
                )}
                <div style={{ textAlign: 'center' }}>
                  <Card size="small" style={{ width: 200, border: '2px solid #1890ff' }}>
                    <div><strong>Block #{selectedBlock.index}</strong></div>
                    <code style={{ fontSize: '10px' }}>
                      {selectedBlock.hash.substring(0, 12)}...
                    </code>
                  </Card>
                </div>
                {selectedBlock.index < pagination.total - 1 && (
                  <>
                    <ArrowRightOutlined style={{ fontSize: 24, color: '#1890ff' }} />
                    <div style={{ textAlign: 'center' }}>
                      <Card size="small" style={{ width: 200, opacity: 0.5 }}>
                        <div>Block #{selectedBlock.index + 1}</div>
                        <code style={{ fontSize: '10px' }}>...</code>
                      </Card>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* 交易列表 */}
            {selectedBlock.transactions.length > 0 && (
              <div style={{ marginTop: 24 }}>
                <h3>交易列表</h3>
                <Table
                  dataSource={selectedBlock.transactions}
                  rowKey="tx_hash"
                  pagination={false}
                  size="small"
                  columns={[
                    {
                      title: '交易哈希',
                      dataIndex: 'tx_hash',
                      key: 'tx_hash',
                      ellipsis: true,
                      render: (hash) => <code style={{ fontSize: '11px' }}>{hash}</code>,
                    },
                    {
                      title: '类型',
                      dataIndex: 'tx_type',
                      key: 'tx_type',
                      render: (type) => <Tag>{type}</Tag>,
                    },
                    {
                      title: '发送方',
                      dataIndex: 'sender',
                      key: 'sender',
                      ellipsis: true,
                      render: (sender) => <code style={{ fontSize: '11px' }}>{sender}</code>,
                    },
                    {
                      title: 'Gas',
                      key: 'gas',
                      render: (_, record) => `${record.gas_price} × ${record.gas_limit}`,
                    },
                  ]}
                />
              </div>
            )}
          </Card>
        )}
      </Space>
    </div>
  )
}

export default BlockChainView

