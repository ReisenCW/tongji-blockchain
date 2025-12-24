# mABC 区块链运维控制台与浏览器

这是一个基于 React 的区块链前端应用，集成了**多智能体（Multi-Agent）运维控制台**和**区块链浏览器**。它不仅展示底层的区块链数据（区块、交易、审计），还可视化呈现了多智能体协作运维（SOP）的全过程，包括状态流转、投票博弈和经济激励。

## ✨ 核心功能

### 1. 🛡️ 运维控制台 (Ops Console)
可视化展示 mABC 系统中多个智能体如何协作处理系统故障。
- **实时日志流 (Log Stream)**: 实时滚动显示系统的运行日志，包括故障检测、Agent 的思考过程 (Thought) 和采取的行动 (Action)。支持模拟“健康巡检”和“故障修复”多种场景。
- **SOP 状态机视图**: 动态展示运维 SOP 的当前流转阶段 (`Init` -> `Data_Collected` -> `Root_Cause_Proposed` -> `Consensus` -> `Solution`)，高亮当前活跃状态。
- **经济看板 (Economy Dashboard)**:
  - **Agent 排行榜**: 根据 Token 余额、信誉分 (Reputation) 和质押量 (Stake) 对 Agent 进行实时排名。
  - **博弈可视化**: 使用环形图展示共识达成情况，显示每个 Agent 的投票权重（质押 × 信誉）和态度（赞成/反对/弃权）。
- **交互控制**: 支持一键重置agent状态。

### 2. 🔍 区块链浏览器 (Explorer)
提供完整的区块链数据浏览和查询功能，类似于 Etherscan。
- **区块可视化**:
  - 显示区块高度、区块哈希、Merkle 根、时间戳
  - 支持分页浏览历史区块
  - 点击区块可展开查看包含的交易详情
- **交易追踪**:
  - **交易搜索**: 支持根据交易哈希 (TxHash) 精确搜索交易
  - **交易详情**: 展示发送方 (Sender)、接收方 (Receiver)、交易类型 (Transfer/Stake) 及 Payload 数据


## 🛠️ 技术栈

- **前端框架**: React 18
- **UI 组件库**: Ant Design 5
- **数据可视化**: Recharts (用于绘制博弈环图、统计图表)
- **构建工具**: Vite
- **网络请求**: Axios (配置了缓存控制和超时处理)
- **后端接口**: Python FastAPI (提供区块链核心逻辑与模拟数据接口)

## 🚀 快速启动

本项目提供了 Windows 批处理脚本，可一键启动服务。

### 1. 启动后端 (API Server)
在项目根目录下双击运行：
```
start_backend.bat
```
*这会自动激活虚拟环境并启动 FastAPI 服务 (http://localhost:8000)*

### 2. 启动前端 (Frontend)
在项目根目录下双击运行：
```
start_frontend.bat
```
*这会自动安装依赖（如果需要）并启动开发服务器 (http://localhost:5173)*

---

## 🔧 手动安装与运行

如果你需要手动分步操作，请参考以下步骤：

### 后端环境准备

确保根目录下已创建虚拟环境并安装了依赖：

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

启动后端 API：
```bash
python frontend/api_server.py
```

### 前端环境准备

确保已安装 Node.js (v16+)。

```bash
cd frontend

# 安装依赖 (推荐使用国内镜像)
npm config set registry https://registry.npmmirror.com
npm install

# 启动开发服务器
npm run dev
```

## 📝 使用指南

### 1. 重置系统

如果你希望重新开始，可以点击右上角的 **"重置系统"** 按钮。这将：
- 清空所有区块链数据（区块、交易）。
- 重置世界状态（删除所有 Agent 账户）。
- 重置 SOP 状态机。

### 2.查看区块
在"区块浏览器"标签页中，可以浏览所有区块，点击"查看详情"按钮查看区块的详细信息。

### 3.搜索交易
在"交易追踪"标签页中，输入交易哈希进行搜索，或浏览所有交易列表。

### 4.查看博弈
在“经济看板”中查看 Agent 们如何基于自身的权益（Stake + Reputation）对提案进行投票表决。


## 📁 目录结构

```
frontend/
├── src/
│   ├── components/
│   │   ├── Dashboard.jsx       # 核心：运维控制台（含日志、SOP、经济看板）
│   │   ├── BlockChainView.jsx  # 区块链列表视图
│   │   ├── TransactionView.jsx # 交易详情视图
│   │   └── AuditView.jsx       # 审计验证视图
│   ├── utils/
│   │   └── api.js              # API 接口封装
│   ├── App.jsx                 # 路由配置
│   ├── main.jsx                # 入口文件
│   └── index.css               # 全局样式
├── api_server.py               # FastAPI 后端入口（提供区块链核心逻辑与模拟数据接口）
├── requirements.txt            # 后端依赖列表
├── package.json                # 前端依赖配置
├── vite.config.js              # Vite 构建配置
└── README.md                   # 说明文档
```
