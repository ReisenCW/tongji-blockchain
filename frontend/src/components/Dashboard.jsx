import React, { useEffect, useState } from 'react'
import { Row, Col, Card, List, Steps, Tag, Table, Space, Statistic, message, Avatar, Typography, Progress, Tooltip, Divider } from 'antd'
import { PieChart, Pie, Cell, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts'
import { UserOutlined, TrophyOutlined, BankOutlined, SafetyCertificateOutlined, CrownOutlined } from '@ant-design/icons'
import { blockchainAPI } from '../utils/api'

const sopSteps = ['Init', 'Data_Collected', 'Root_Cause_Proposed', 'Consensus', 'Solution']
const COLORS = ['#2ecc71', '#e74c3c', '#f1c40f']

function Dashboard() {
  const [events, setEvents] = useState([])
  const [sopState, setSopState] = useState('Init')
  const [proposal, setProposal] = useState(null)
  const [incident, setIncident] = useState(null)
  const [accounts, setAccounts] = useState([])
  const [voting, setVoting] = useState(null)

  const loadSop = async () => {
    try {
      const data = await blockchainAPI.getSOPState()
      console.log('SOP State loaded:', data) // Debug log
      setSopState(data.current_state || 'Init')
      setProposal(data.current_proposal || null)
      setIncident(data.incident_data || null)
      setEvents(data.events || [])
    } catch (e) {
      console.error('SOP load failed:', e)
    }
  }

  const loadAccounts = async () => {
    try {
      const data = await blockchainAPI.getAgentsState()
      const rawAccounts = data.accounts || []
      // Sort by balance descending to determine rank
      const sortedAccounts = rawAccounts.sort((a, b) => b.balance - a.balance)
      // Add rank property
      const rankedAccounts = sortedAccounts.map((item, index) => ({
        ...item,
        rank: index + 1
      }))
      setAccounts(rankedAccounts)
    } catch (e) {
      // message.error('经济数据加载失败')
    }
  }

  const loadVoting = async () => {
    try {
      const data = await blockchainAPI.getVotingStatus()
      setVoting(data || null)
    } catch (e) {
      // message.error('投票状态加载失败')
    }
  }

  const pollEvents = async () => {
    try {
      const data = await blockchainAPI.getEvents(100)
      setEvents(data || [])
    } catch {}
  }

  const runAgentsOnce = async () => {
    try {
      message.loading({ content: '正在读取指标与拓扑进行根因分析...', key: 'run' })
      const res = await blockchainAPI.runAgents()
      if (res.success) {
        message.success({ content: '七智能体分析完成，投票与状态已更新', key: 'run' })
      } else {
        message.error({ content: '分析未成功', key: 'run' })
      }
    } catch (e) {
      const errorMsg = e.response?.data?.detail || e.message || '未知错误'
      message.error({ content: `分析失败: ${errorMsg}`, key: 'run' })
    } finally {
      loadAccounts()
      loadSop()
      loadVoting()
      pollEvents()
    }
  }

  useEffect(() => {
    runAgentsOnce()
    const t1 = setInterval(loadSop, 5000)
    const t2 = setInterval(loadVoting, 5000)
    const t3 = setInterval(pollEvents, 2000)
    return () => {
      clearInterval(t1)
      clearInterval(t2)
      clearInterval(t3)
    }
  }, [])

  const currentIndex = sopSteps.indexOf(sopState)

  const accountColumns = [
    {
      title: '排名',
      key: 'rank',
      width: 50,
      align: 'center',
      render: (_, record) => {
        const rank = record.rank
        let icon = null
        let color = '#d9d9d9'
        
        if (rank === 1) {
          icon = <CrownOutlined />
          color = '#ffc107' // Gold
        } else if (rank === 2) {
          icon = <TrophyOutlined />
          color = '#b0bec5' // Silver
        } else if (rank === 3) {
          icon = <TrophyOutlined />
          color = '#cd7f32' // Bronze
        }

        return (
          <Avatar 
            size={24} 
            style={{ 
              backgroundColor: rank <= 3 ? 'transparent' : '#f0f0f0', 
              color: rank <= 3 ? color : '#8c8c8c',
              fontSize: rank <= 3 ? 18 : 12
            }}
          >
            {rank <= 3 ? icon : rank}
          </Avatar>
        )
      },
    },
    {
      title: 'Agent',
      dataIndex: 'address',
      key: 'address',
      render: (text) => (
        <Space>
          <Avatar 
            size="small" 
            style={{ backgroundColor: `#${text.slice(2, 8)}`, verticalAlign: 'middle' }}
          >
            {text[0].toUpperCase()}
          </Avatar>
          <Typography.Text 
            copyable={{ text }} 
            ellipsis={{ tooltip: text }} 
            style={{ width: 80, fontSize: 12 }}
          >
            {text.slice(0, 6)}...{text.slice(-4)}
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: '资产 & 信誉',
      key: 'stats',
      render: (_, record) => (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <Space split={<span style={{ color: '#d9d9d9' }}>|</span>} style={{ fontSize: 12 }}>
            <span title="余额">
              <BankOutlined style={{ color: '#1890ff', marginRight: 4 }} />
              <Typography.Text strong>{record.balance.toLocaleString()}</Typography.Text>
            </span>
            <span title="质押">
              <SafetyCertificateOutlined style={{ color: '#52c41a', marginRight: 4 }} />
              {record.stake.toLocaleString()}
            </span>
          </Space>
          <Tooltip title={`信誉分: ${record.reputation}`}>
            <Progress 
              percent={record.reputation} 
              size={[100, 4]} 
              showInfo={false}
              strokeColor={{
                '0%': '#ff4d4f',
                '100%': '#52c41a',
              }}
            />
          </Tooltip>
        </div>
      ),
    },
  ]

  const voteData = voting && voting.active ? [
    { name: '赞成', value: voting.statistics.for },
    { name: '反对', value: voting.statistics.against },
    { name: '弃权', value: voting.statistics.abstain },
  ] : []

  return (
    <Row gutter={[16, 16]} style={{ height: 'calc(100vh - 120px)' }}>
      <Col span={6} style={{ height: '100%', overflow: 'auto' }}>
        <Card title="实时日志流" style={{ height: '100%' }} bodyStyle={{ padding: '0 12px' }}>
          <List
            dataSource={[...(events || [])].reverse()}
            renderItem={(item) => (
              <List.Item style={{ padding: '12px 0' }}>
                <Space direction="vertical" style={{ width: '100%' }} size={4}>
                  <Space style={{ justifyContent: 'space-between', width: '100%' }}>
                    <Tag color="blue">{item.name}</Tag>
                    <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                      {new Date(item.timestamp).toLocaleTimeString()}
                    </Typography.Text>
                  </Space>
                  <div style={{ 
                    fontSize: 12, 
                    color: '#595959', 
                    background: '#f5f5f5', 
                    padding: 8, 
                    borderRadius: 4,
                    wordBreak: 'break-all'
                  }}>
                    {Object.entries(item).map(([k, v]) => {
                      if (['name', 'timestamp'].includes(k)) return null;
                      return (
                        <div key={k}>
                          <span style={{ fontWeight: 500 }}>{k}:</span> {JSON.stringify(v)}
                        </div>
                      )
                    })}
                  </div>
                </Space>
              </List.Item>
            )}
          />
        </Card>
      </Col>
      <Col span={10} style={{ height: '100%', overflow: 'auto' }}>
        <Space direction="vertical" style={{ width: '100%' }} size={16}>
          <Card title="运维SOP状态机">
            <Steps current={currentIndex} size="small" status="process">
              {sopSteps.map((s) => (
                <Steps.Step key={s} title={s.replace(/_/g, ' ')} />
              ))}
            </Steps>
            <div style={{ marginTop: 24, textAlign: 'center' }}>
              <Statistic 
                title="当前阶段" 
                value={sopState} 
                valueStyle={{ color: '#1890ff' }}
              />
              {proposal && (
                <div style={{ marginTop: 16, padding: 12, background: '#e6f7ff', borderRadius: 4 }}>
                  <Typography.Text type="secondary">当前提案: </Typography.Text>
                  <Typography.Text strong>{proposal.content}</Typography.Text>
                </div>
              )}
            </div>
          </Card>
          <Card title="投票博弈与决策路径" bodyStyle={{ padding: '12px 24px' }}>
            {voting && voting.active ? (
              <>
                <Row gutter={16} align="middle">
                  <Col span={10}>
                    <div style={{ height: 140, position: 'relative' }}>
                      <ResponsiveContainer>
                        <PieChart>
                          <Pie
                            data={voteData}
                            dataKey="value"
                            nameKey="name"
                            cx="50%"
                            cy="50%"
                            innerRadius={35}
                            outerRadius={60}
                            paddingAngle={2}
                          >
                            {voteData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                          </Pie>
                          <RechartsTooltip />
                        </PieChart>
                      </ResponsiveContainer>
                      <div style={{ 
                        position: 'absolute', 
                        top: '50%', 
                        left: '50%', 
                        transform: 'translate(-50%, -50%)', 
                        textAlign: 'center',
                        fontSize: 12,
                        color: '#8c8c8c'
                      }}>
                        共识池
                      </div>
                    </div>
                  </Col>
                  <Col span={14}>
                    <Statistic 
                      title="当前提案支持率" 
                      value={(voting.statistics.support_rate * 100).toFixed(1)} 
                      suffix="%" 
                      valueStyle={{ color: voting.statistics.consensus_reached ? '#52c41a' : '#1890ff', fontSize: 20 }}
                    />
                    <div style={{ marginTop: 8 }}>
                      <Tag color={voting.statistics.consensus_reached ? 'success' : 'processing'}>
                        {voting.statistics.consensus_reached ? '已达成共识' : '博弈进行中'}
                      </Tag>
                      <div style={{ fontSize: 11, color: '#bfbfbf', marginTop: 4 }}>
                        通过阈值: >50% 全网权重
                      </div>
                    </div>
                  </Col>
                </Row>

                <Divider style={{ margin: '12px 0' }} dashed />

                <div style={{ maxHeight: 240, overflow: 'auto' }}>
                  <List
                    header={
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#595959', fontWeight: 600 }}>
                        <span>Agent 决策者</span>
                        <span>权重 (质押×信誉) & 态度</span>
                      </div>
                    }
                    size="small"
                    dataSource={voting.votes}
                    renderItem={item => (
                      <List.Item style={{ padding: '8px 0' }}>
                        <Space>
                          <Avatar 
                            size={20}
                            style={{ backgroundColor: `#${item.address.slice(2, 8)}`, fontSize: 10 }}
                          >
                            {item.address[0].toUpperCase()}
                          </Avatar>
                          <Typography.Text style={{ fontSize: 12, width: 70 }} ellipsis={{ tooltip: item.address }}>
                            {item.address.slice(0, 6)}...
                          </Typography.Text>
                        </Space>
                        <Space>
                          <span style={{ fontSize: 12, color: '#8c8c8c', fontFamily: 'monospace' }}>
                            W:{item.weight.toFixed(0)}
                          </span>
                          <Tag 
                            color={item.option === 'for' ? 'success' : (item.option === 'against' ? 'error' : 'default')}
                            style={{ marginRight: 0, minWidth: 40, textAlign: 'center' }}
                          >
                            {item.option === 'for' ? '赞成' : (item.option === 'against' ? '反对' : '弃权')}
                          </Tag>
                        </Space>
                      </List.Item>
                    )}
                  />
                </div>
              </>
            ) : (
              <div style={{ textAlign: 'center', padding: '40px 0', color: '#bfbfbf' }}>
                <SafetyCertificateOutlined style={{ fontSize: 32, marginBottom: 8 }} />
                <div>暂无活跃投票提案</div>
              </div>
            )}
          </Card>
        </Space>
      </Col>
      <Col span={8} style={{ height: '100%', overflow: 'auto' }}>
        <Card 
          title="经济看板" 
          bodyStyle={{ padding: 0 }}
          extra={null}
        >
          <Table
            columns={accountColumns}
            dataSource={accounts}
            rowKey="address"
            size="small"
            pagination={{ pageSize: 8, size: 'small' }}
            scroll={{ x: 'max-content' }}
          />
        </Card>
        {incident && (
          <Card title="故障现场快照" style={{ marginTop: 16 }} size="small">
            <Typography.Paragraph 
              ellipsis={{ rows: 3, expandable: true, symbol: '展开' }}
              style={{ marginBottom: 0, fontFamily: 'monospace' }}
            >
              {JSON.stringify(incident, null, 2)}
            </Typography.Paragraph>
          </Card>
        )}
      </Col>
    </Row>
  )
}

export default Dashboard
