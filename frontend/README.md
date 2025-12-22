# mABC Blockchain Explorer

区块链浏览器前端应用，用于可视化展示区块链数据、交易追踪和审计验证。

## 功能特性

### 1. 区块可视化
- 展示区块链的链式结构
- 显示区块高度、哈希值、Merkle根
- 支持分页浏览区块列表
- 点击区块查看详细信息

### 2. 交易追踪
- 根据交易哈希搜索交易
- 展示交易的发送方、接收方、Payload数据
- 显示交易执行结果（已上链/待处理）
- 实时显示待处理交易列表

### 3. 审计视图
- Merkle Proof可视化验证
- 生成可信审计报告
- 支持下载JSON格式的审计报告

## 技术栈

- **前端框架**: React 18
- **UI组件库**: Ant Design 5
- **构建工具**: Vite
- **HTTP客户端**: Axios
- **时间处理**: Day.js

## 安装和运行

### 前置要求

- Node.js 16+ 
- npm 或 yarn
- Python 3.9+ (用于运行后端API)

### 安装依赖

```bash
cd frontend
npm install
pip install -r requirements.txt
```

### 启动服务

#### 方法1: 先启动API服务器，再生成测试数据

```bash
# 1. 启动后端API服务器
python frontend/api_server.py

# 2. 在另一个终端，运行测试数据生成脚本
# （注意：需要先停止API服务器，运行脚本，再重启）
python frontend/generate_test_data.py
```

#### 方法2: 先生成测试数据，再启动API服务器（推荐）

```bash
# 1. 生成测试数据（这会创建blockchain实例）
python frontend/generate_test_data.py

# 2. 启动后端API服务器（使用同一个blockchain实例）
python frontend/api_server.py
```

#### 方法3: 使用主程序生成数据

```bash
# 运行主程序，会自动生成区块和交易
python mABC/main/main.py
```

### 启动前端开发服务器

```bash
cd frontend
npm run dev
```

前端应用将在 `http://localhost:3000` 启动。

### 构建生产版本

```bash
npm run build
```

构建产物将输出到 `dist/` 目录。

## 重要提示

⚠️ **数据持久化说明**：
- 当前blockchain实例存储在内存中，重启后会丢失
- 如果需要持久化数据，需要：
  1. 先运行测试数据生成脚本创建数据
  2. 然后启动API服务器（使用同一个blockchain实例）
  3. 或者使用主程序生成数据

## 项目结构

```
frontend/
├── api_server.py          # FastAPI后端服务器
├── generate_test_data.py  # 测试数据生成脚本
├── src/
│   ├── components/
│   │   ├── Explorer.jsx    # 主浏览器组件
│   │   ├── BlockChainView.jsx    # 区块可视化组件
│   │   ├── TransactionView.jsx   # 交易追踪组件
│   │   └── AuditView.jsx         # 审计视图组件
│   ├── utils/
│   │   └── api.js         # API调用封装
│   ├── App.jsx            # 根组件
│   └── main.jsx           # 入口文件
├── package.json
└── vite.config.js
```

## API接口

后端提供以下REST API接口：

- `GET /api/blocks` - 获取区块列表
- `GET /api/block/{index}` - 获取指定区块详情
- `GET /api/transaction/{hash}` - 获取交易详情
- `GET /api/blockchain/info` - 获取区块链整体信息
- `GET /api/merkle-proof/{block_index}/{tx_index}` - 获取Merkle Proof
- `GET /api/pending-transactions` - 获取待处理交易

## 使用说明

1. **查看区块**: 在"区块浏览器"标签页中，可以浏览所有区块，点击"查看详情"按钮查看区块的详细信息。

2. **搜索交易**: 在"交易追踪"标签页中，输入交易哈希进行搜索，或浏览所有交易列表。

3. **验证交易**: 在"审计视图"标签页中，输入区块索引和交易索引，系统将生成并验证Merkle Proof，生成可信审计报告。

## 注意事项

- 确保后端API服务器已启动并可以访问区块链数据
- 前端通过代理访问后端API，配置在 `vite.config.js` 中
- 生产环境部署时，需要修改CORS配置和API地址
- 如果看不到数据，请先运行测试数据生成脚本
