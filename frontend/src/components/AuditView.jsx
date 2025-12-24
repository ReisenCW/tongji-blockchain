import React, { useState, useEffect } from 'react'
import { Card, Form, InputNumber, Button, Descriptions, Tag, Alert, Space, message, Tree } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined, SearchOutlined } from '@ant-design/icons'
import { blockchainAPI } from '../utils/api'

function AuditView({ refreshKey }) {
  const [form] = Form.useForm()
  const [proof, setProof] = useState(null)
  const [loading, setLoading] = useState(false)
  const [treeData, setTreeData] = useState([])

  // 当切换到审计视图时，重置表单/结果，保证内容是最新状态
  useEffect(() => {
    if (refreshKey !== undefined) {
      form.resetFields()
      setProof(null)
      setTreeData([])
    }
  }, [refreshKey])

  const handleVerify = async (values) => {
    setLoading(true)
    try {
      const result = await blockchainAPI.getMerkleProof(values.blockIndex, values.txIndex)
      setProof(result)
      
      // 构建树形结构用于可视化
      buildTreeData(result)
      
      message.success('Merkle Proof验证完成')
    } catch (error) {
      message.error('验证失败: ' + error.message)
      setProof(null)
    } finally {
      setLoading(false)
    }
  }

  const buildTreeData = (proofData) => {
    const nodes = []
    
    // 添加目标交易节点（叶子节点）
    nodes.push({
      title: (
        <span>
          <strong>目标交易</strong>
          <br />
          <code style={{ fontSize: '10px' }}>
            {proofData.transaction_hash.substring(0, 20)}...
          </code>
        </span>
      ),
      key: 'target',
    })

    // 构建证明路径（从叶子到根）
    const proofPath = [...proofData.proof_path]
    
    proofPath.forEach((proof, index) => {
      const siblingHash = proof.hash
      const isLeft = proof.position === 'left'
      
      nodes.push({
        title: (
          <span>
            {isLeft ? '左' : '右'}兄弟节点 (Level {index + 1})
            <br />
            <code style={{ fontSize: '10px' }}>
              {siblingHash.substring(0, 20)}...
            </code>
          </span>
        ),
        key: `sibling-${index}`,
      })
    })

    // 根节点
    nodes.push({
      title: (
        <span>
          <strong>Merkle Root</strong>
          <br />
          <code style={{ fontSize: '10px' }}>
            {proofData.merkle_root.substring(0, 20)}...
          </code>
        </span>
      ),
      key: 'root',
    })

    setTreeData([{
      title: (
        <span>
          <strong>Merkle Tree 验证路径</strong>
          <br />
          <code style={{ fontSize: '10px' }}>
            {proofData.merkle_root.substring(0, 20)}...
          </code>
        </span>
      ),
      key: 'root',
      children: nodes,
    }])
  }

  const generateAuditReport = () => {
    if (!proof) return null

    const report = {
      title: '可信审计报告',
      timestamp: new Date().toISOString(),
      transactionHash: proof.transaction_hash,
      merkleRoot: proof.merkle_root,
      verificationResult: proof.verified ? '通过' : '失败',
      proofPath: proof.proof_path,
      conclusion: proof.verified
        ? '该交易已通过Merkle Proof验证，确认为区块链上的有效交易，数据完整性得到保证。'
        : '该交易的Merkle Proof验证失败，数据可能已被篡改或不存在于区块链上。',
    }

    return report
  }

  const auditReport = generateAuditReport()

  return (
    <div>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* 验证表单 */}
        <Card title="Merkle Proof验证">
          <Form
            form={form}
            layout="inline"
            onFinish={handleVerify}
            style={{ marginBottom: 16 }}
          >
            <Form.Item
              name="blockIndex"
              label="区块索引"
              rules={[{ required: true, message: '请输入区块索引' }]}
            >
              <InputNumber min={0} placeholder="区块索引" style={{ width: 150 }} />
            </Form.Item>
            <Form.Item
              name="txIndex"
              label="交易索引"
              rules={[{ required: true, message: '请输入交易索引' }]}
            >
              <InputNumber min={0} placeholder="交易索引" style={{ width: 150 }} />
            </Form.Item>
            <Form.Item>
              <Button
                type="primary"
                icon={<SearchOutlined />}
                htmlType="submit"
                loading={loading}
              >
                验证
              </Button>
            </Form.Item>
          </Form>
          <Alert
            message="使用说明"
            description="输入区块索引和交易索引，系统将生成并验证该交易的Merkle Proof，确保交易数据的完整性和真实性。"
            type="info"
            showIcon
          />
        </Card>

        {/* 验证结果 */}
        {proof && (
          <>
            <Card title="验证结果">
              <Descriptions bordered column={2}>
                <Descriptions.Item label="交易哈希">
                  <code>{proof.transaction_hash}</code>
                </Descriptions.Item>
                <Descriptions.Item label="Merkle根">
                  <code>{proof.merkle_root}</code>
                </Descriptions.Item>
                <Descriptions.Item label="验证状态" span={2}>
                  {proof.verified ? (
                    <Tag color="success" icon={<CheckCircleOutlined />} style={{ fontSize: 14, padding: '8px 16px' }}>
                      验证通过
                    </Tag>
                  ) : (
                    <Tag color="error" icon={<CloseCircleOutlined />} style={{ fontSize: 14, padding: '8px 16px' }}>
                      验证失败
                    </Tag>
                  )}
                </Descriptions.Item>
              </Descriptions>

              {/* Proof路径 */}
              <div style={{ marginTop: 24 }}>
                <h3>Proof路径</h3>
                <Card>
                  {proof.proof_path.length > 0 ? (
                    <Space direction="vertical" style={{ width: '100%' }}>
                      {proof.proof_path.map((p, index) => (
                        <Card key={index} size="small" style={{ background: '#f5f5f5' }}>
                          <Space>
                            <Tag color={p.position === 'left' ? 'blue' : 'green'}>
                              {p.position === 'left' ? '左' : '右'}兄弟节点
                            </Tag>
                            <code style={{ fontSize: '11px' }}>{p.hash}</code>
                          </Space>
                        </Card>
                      ))}
                    </Space>
                  ) : (
                    <Alert message="该交易是区块中唯一的交易，无需Proof路径" type="info" />
                  )}
                </Card>
              </div>

              {/* Merkle树可视化 */}
              {treeData.length > 0 && (
                <div style={{ marginTop: 24 }}>
                  <h3>Merkle树结构</h3>
                  <Card>
                    <Tree
                      treeData={treeData}
                      defaultExpandAll
                      showLine
                    />
                  </Card>
                </div>
              )}
            </Card>

            {/* 审计报告 */}
            {auditReport && (
              <Card title="可信审计报告">
                <Alert
                  message={auditReport.conclusion}
                  type={proof.verified ? 'success' : 'error'}
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                <Descriptions bordered column={1}>
                  <Descriptions.Item label="报告标题">
                    {auditReport.title}
                  </Descriptions.Item>
                  <Descriptions.Item label="生成时间">
                    {new Date(auditReport.timestamp).toLocaleString('zh-CN')}
                  </Descriptions.Item>
                  <Descriptions.Item label="交易哈希">
                    <code>{auditReport.transactionHash}</code>
                  </Descriptions.Item>
                  <Descriptions.Item label="Merkle根">
                    <code>{auditReport.merkleRoot}</code>
                  </Descriptions.Item>
                  <Descriptions.Item label="验证结果">
                    <Tag color={proof.verified ? 'green' : 'red'}>
                      {auditReport.verificationResult}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="结论">
                    {auditReport.conclusion}
                  </Descriptions.Item>
                </Descriptions>
                <div style={{ marginTop: 16, textAlign: 'right' }}>
                  <Button
                    type="primary"
                    onClick={() => {
                      const reportText = JSON.stringify(auditReport, null, 2)
                      const blob = new Blob([reportText], { type: 'application/json' })
                      const url = URL.createObjectURL(blob)
                      const a = document.createElement('a')
                      a.href = url
                      a.download = `audit-report-${proof.transaction_hash.substring(0, 16)}.json`
                      a.click()
                      URL.revokeObjectURL(url)
                      message.success('审计报告已下载')
                    }}
                  >
                    下载审计报告
                  </Button>
                </div>
              </Card>
            )}
          </>
        )}
      </Space>
    </div>
  )
}

export default AuditView

