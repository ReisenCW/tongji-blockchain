import React, { useEffect, useState } from 'react'
import { Row, Col, Card, List, Steps, Tag, Table, Space, Statistic, message, Avatar, Typography, Progress, Tooltip, Button, Divider } from 'antd'
import { PieChart, Pie, Cell, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts'
import { UserOutlined, TrophyOutlined, BankOutlined, SafetyCertificateOutlined, CrownOutlined, ThunderboltOutlined, DeleteOutlined } from '@ant-design/icons'
import { blockchainAPI } from '../utils/api'

const sopSteps = ['Init', 'Data_Collected', 'Root_Cause_Proposed', 'Consensus', 'Solution']
const COLORS = ['#2ecc71', '#e74c3c', '#f1c40f']

function Dashboard({ refreshKey }) {
  const [events, setEvents] = useState([])
  const [sopState, setSopState] = useState('Init')
  const [proposal, setProposal] = useState(null)
  const [incident, setIncident] = useState(null)
  const [accounts, setAccounts] = useState([])
  const [treasury, setTreasury] = useState([])
  const [voting, setVoting] = useState(null)
  const [economy, setEconomy] = useState(null)

  // 当切换到运维控制台 Tab 时触发一次刷新
  useEffect(() => {
    if (refreshKey !== undefined) {
      loadSop()
      loadAccounts()
      loadVoting()
      pollEvents()
      loadEconomy()
    }
  }, [refreshKey])

  const loadSop = async () => {
    try {
      const data = await blockchainAPI.getSOPState()
      console.log('SOP State loaded:', data) // Debug log
      setSopState(data.current_state || 'Init')
      setProposal(data.current_proposal || null)
      setIncident(data.incident_data || null)
      // setEvents(data.events || []) // Removed to avoid overwriting agent logs
    } catch (e) {
      console.error('SOP load failed:', e)
    }
  }

  const loadAccounts = async () => {
    try {
      const data = await blockchainAPI.getAgentsState()
      const rawAccounts = data.accounts || []
      const rawTreasury = data.treasury || []
      // Sort by balance descending to determine rank
      const sortedAccounts = rawAccounts.sort((a, b) => b.balance - a.balance)
      // Add rank property
      const rankedAccounts = sortedAccounts.map((item, index) => ({
        ...item,
        rank: index + 1
      }))
      setAccounts(rankedAccounts)
      setTreasury(rawTreasury.sort((a, b) => (b.balance || 0) - (a.balance || 0)))
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
      await loadAccounts()
    } catch {}
  }

  const loadEconomy = async () => {
    try {
      const data = await blockchainAPI.getEconomyOverview()
      setEconomy(data || null)
    } catch {}
  }

  const handleRunAnalysis = async () => {
    try {
      message.loading({ content: '多智能体分析进行中...', key: 'gen', duration: 0 })
      // 开始轮询事件，以便用户看到进度
      const interval = setInterval(pollEvents, 1000)
      
      const res = await blockchainAPI.runAgents()
      
      clearInterval(interval)
      if (res.success) {
        message.success({ content: '分析完成！共识已达成', key: 'gen' })
        loadAccounts()
        loadSop()
        loadVoting()
        pollEvents()
      }
    } catch (e) {
      message.error({ content: '分析失败: ' + (e.response?.data?.detail || e.message), key: 'gen' })
    }
  }

  const handleResetData = async () => {
    try {
      message.loading({ content: '重置数据中...', key: 'reset' })
      const res = await blockchainAPI.resetData()
      if (res.success) {
        message.success({ content: '系统数据已重置', key: 'reset' })
        loadAccounts()
        loadSop()
        loadVoting()
        pollEvents()
      }
    } catch (e) {
      const errorMsg = e.response?.data?.detail || e.message || '未知错误'
      message.error({ content: `重置失败: ${errorMsg}`, key: 'reset' })
      console.error('Reset failed:', e)
    }
  }

  useEffect(() => {
    loadSop()
    loadAccounts()
    loadVoting()
    loadEconomy()
    const t1 = setInterval(loadSop, 5000)
    const t2 = setInterval(loadVoting, 5000)
    const t3 = setInterval(pollEvents, 1000)
    const t4 = setInterval(loadEconomy, 5000)
    return () => {
      clearInterval(t1)
      clearInterval(t2)
      clearInterval(t3)
      clearInterval(t4)
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
      dataIndex: 'name',
      key: 'name',
      width: 120,
      render: (text) => (
        <Typography.Text strong style={{ fontSize: 12, maxWidth: 120 }} ellipsis={{ tooltip: text }}>
          {text}
        </Typography.Text>
      ),
    },
    {
      title: '钱包地址',
      dataIndex: 'address',
      key: 'address',
      width: 100,
      render: (text) => (
        <Typography.Text
          copyable={{ text }}
          ellipsis={{ tooltip: text }}
          style={{ width: 100, fontSize: 12, textAlign: 'left', display: 'inline-block' }}
        >
          {text.slice(0, 6)}...{text.slice(-4)}
        </Typography.Text>
      ),
    },
    {
      title: '资产 & 质押',
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
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 11, color: '#8c8c8c' }}>信誉</span>
              <Typography.Text style={{ fontSize: 11, color: '#8c8c8c' }}>{`${record.reputation}/100`}</Typography.Text>
            </div>
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
            dataSource={[...(events || [])].filter(item => item.type === 'agent_log').reverse()}
            rowKey="id"
            renderItem={(item) => {
              const isAgentLog = true // Filtered above, so always true
              
              let tagColor = 'blue'
              let tagName = item.name
              let content = null

              if (isAgentLog) {
                switch (item.log_type) {
                  case 'thought':
                    tagColor = 'purple'
                    tagName = '思考'
                    break
                  case 'action':
                    tagColor = 'orange'
                    tagName = '执行'
                    break
                  case 'answer':
                    tagColor = 'green'
                    tagName = '结论'
                    break
                  case 'reward':
                    tagColor = 'gold'
                    tagName = '奖励'
                    break
                  default:
                    tagColor = 'default'
                    tagName = '日志'
                }
                content = (
                  <div style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                    {item.content}
                  </div>
                )
              } else {
                // Contract Event
                tagName = item.name
                content = (
                  <div style={{ wordBreak: 'break-all' }}>
                    {Object.entries(item).map(([k, v]) => {
                      if (['name', 'timestamp'].includes(k)) return null;
                      return (
                        <div key={k}>
                          <span style={{ fontWeight: 500 }}>{k}:</span> {
                            typeof v === 'object' ? JSON.stringify(v) : v
                          }
                        </div>
                      )
                    })}
                  </div>
                )
              }

              return (
                <List.Item style={{ padding: '12px 0' }}>
                  <Space direction="vertical" style={{ width: '100%' }} size={4}>
                    <Space style={{ justifyContent: 'space-between', width: '100%' }}>
                      <Tag color={tagColor}>{tagName}</Tag>
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
                    }}>
                      {content}
                    </div>
                  </Space>
                </List.Item>
              )
            }}
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
                <div style={{ marginBottom: 12, padding: '8px', background: '#f9f9f9', borderRadius: 4 }}>
                  <Typography.Text strong style={{ fontSize: 12 }}>提案内容：</Typography.Text>
                  <Typography.Paragraph 
                    ellipsis={{ rows: 2, expandable: true, symbol: '展开' }} 
                    style={{ fontSize: 12, color: '#595959', margin: 0 }}
                  >
                    {voting.proposal?.content || '暂无内容'}
                  </Typography.Paragraph>
                </div>
                
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
                        通过阈值: &gt; 50% 全网权重
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
                        <span>权重 (信誉+质押) & 态度</span>
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
          extra={
            <Space>
              <Button 
                icon={<DeleteOutlined />} 
                onClick={handleResetData}
                size="large"
              >
                重置数据
              </Button>
              <Button 
                type="primary" 
                icon={<ThunderboltOutlined />} 
                onClick={handleRunAnalysis}
                size="large"
              >
                开始诊断
              </Button>
            </Space>
          }
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
        {treasury && treasury.length > 0 && (
          <Card title="系统金库" style={{ marginTop: 16 }} size="small">
            <List
              size="small"
              dataSource={treasury}
              renderItem={(item) => (
                <List.Item>
                  <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                    <Space>
                      <Avatar 
                        size={20}
                        style={{ backgroundColor: `#${item.address.slice(2, 8)}`, fontSize: 10 }}
                      >
                        {item.address[0].toUpperCase()}
                      </Avatar>
                      <Typography.Text style={{ fontSize: 12 }} ellipsis={{ tooltip: item.address }}>
                        {item.address.slice(0, 6)}...{item.address.slice(-4)}
                      </Typography.Text>
                    </Space>
                    <Space split={<span style={{ color: '#d9d9d9' }}>|</span>} style={{ fontSize: 12 }}>
                      <span title="余额">
                        <BankOutlined style={{ color: '#1890ff', marginRight: 4 }} />
                        <Typography.Text strong>{(item.balance || 0).toLocaleString()}</Typography.Text>
                      </span>
                      <span title="质押">
                        <SafetyCertificateOutlined style={{ color: '#52c41a', marginRight: 4 }} />
                        {(item.stake || 0).toLocaleString()}
                      </span>
                      <span title="信誉">
                        <Typography.Text style={{ fontSize: 12, color: '#8c8c8c' }}>{`${item.reputation || 0}/100`}</Typography.Text>
                      </span>
                    </Space>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        )}
        {economy && (
          <Card title="经济系统概览" style={{ marginTop: 16 }} size="small">
            <List
              size="small"
              dataSource={[
                { k: 'Agent 初始资金', v: `${economy.agent_initial_balance}` },
                { k: 'Gas 价格 × 最小限额', v: `${economy.gas_price} × ${economy.min_gas_limit}` },
                { k: '投票 Gas 限额', v: `${economy.vote_gas_limit}` },
                { k: '奖励 Gas 限额', v: `${economy.reward_gas_limit}` },
                { k: '奖励规则（提案人）', v: `+${economy.proposer_reward_token} Token, +${economy.proposer_reward_rep} Reputation` },
                { k: '奖励规则（支持者）', v: `+${economy.supporter_reward_token} Token, +${economy.supporter_reward_rep} Reputation` },
                { k: '通过返还（支持者）', v: `返还投票Gas ${Math.round((economy.pass_rebate_ratio || 0) * 100)}%` },
                { k: '成果赏金（提案人）', v: `基础额 +${economy.bounty_base_token} Token` },
                { k: '罚没（提案通过时反对者）', v: `-${economy.penalty_against_pass_token} Token, ${economy.penalty_against_pass_rep} Reputation` },
                { k: '罚没（提案失败时支持者）', v: `-${economy.penalty_support_fail_token} Token, ${economy.penalty_support_fail_rep} Reputation` },
                { k: '罚没（提案失败时提案人）', v: `-${economy.penalty_proposer_fail_token} Token, ${economy.penalty_proposer_fail_rep} Reputation` },
                { k: '系统金库余额', v: `${(economy.treasury_balance || 0).toLocaleString()}` },
                { k: '系统金库地址', v: `${economy.treasury_address ? economy.treasury_address.slice(0,6)+'...'+economy.treasury_address.slice(-4) : '-'}` },
                { k: '核心 Agent 数量', v: `${economy.agent_count}` },
              ]}
              renderItem={(item) => (
                <List.Item>
                  <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                    <Typography.Text style={{ fontSize: 12, color: '#8c8c8c' }}>{item.k}</Typography.Text>
                    <Typography.Text style={{ fontSize: 12 }} strong>{item.v}</Typography.Text>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        )}
      </Col>
    </Row>
  )
}

export default Dashboard
