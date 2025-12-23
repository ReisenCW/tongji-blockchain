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
- **交互控制**: 支持一键生成测试数据（模拟故障场景或健康检查）和重置系统状态。

### 2. 🔍 区块链浏览器 (Explorer)
提供完整的区块链数据浏览和查询功能，类似于 Etherscan。
- **区块可视化**:
  - 以卡片形式展示区块链的链式结构
  - 显示区块高度、区块哈希、Merkle 根、时间戳
  - 支持分页浏览历史区块
  - 点击区块可展开查看包含的交易详情
- **交易追踪**:
  - **交易搜索**: 支持根据交易哈希 (TxHash) 精确搜索交易
  - **交易详情**: 展示发送方 (Sender)、接收方 (Receiver)、交易类型 (Transfer/Stake) 及 Payload 数据
  - **状态监控**: 区分已上链交易和待处理交易 (Pending)
- **待处理交易池 (Mempool)**:
  - 实时显示当前网络中等待打包的 Pending 交易列表

### 3. ✅ 审计验证 (Audit)
提供基于 Merkle Tree 的轻节点验证功能，确保数据的不可篡改性。
- **Merkle Proof 可视化**: 图形化展示 Merkle 路径，直观理解交易如何被包含在 Merkle Root 中
- **可信审计报告**: 自动生成审计报告，包含验证结果、交易哈希和 Merkle 路径
- **报告导出**: 支持将审计结果导出为 JSON 格式文件，用于离线验证或存档

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

### 1. 自动根因分析 (Auto Analysis)

页面加载后，系统会自动调用后端接口 `/api/run-agents`，由 **七个智能体**（AlertReceiver、ProcessScheduler、DataDetective、DependencyExplorer、ProbabilityOracle、FaultMapper、SolutionEngineer）联合读取 `mABC/data/metric/endpoint_stats.json` 与 `mABC/data/topology/endpoint_maps.json` 进行根因分析与链上投票。

- **数据来源**: 仅使用 `mABC/data` 目录中的真实数据文件进行分析；若缺失会返回错误提示。
- **合约协同**: SOP 合约驱动状态机与事件，治理合约执行投票与共识，Token 合约处理质押与转账。
- **前端联动**: 成功后自动刷新 SOP 状态、投票统计与经济看板。

### 2. 操作方式
- 无需手动点击“生成数据”或“重置系统”，页面加载即自动执行分析。
- 若需要重新分析，请刷新页面。

### 3. 工作原理
- **合约协同**: 自动分析通过 `/api/run-agents` 触发七智能体执行，最终由区块链执行层分发到各合约：
  - `ops_contract` 负责 SOP 状态机推进与事件发射（如 `DataCollected`、`RootCauseProposed`）。参考 `mABC/contracts/ops_contract.py:56`、`mABC/contracts/ops_contract.py:77`。
  - `governance_contract` 负责投票与共识判定，计算权重并推进到共识阶段。参考 `mABC/contracts/governance_contract.py:13`。
  - `token_contract` 负责 `transfer` 和 `stake` 等经济操作。参考 `mABC/contracts/token_contract.py:13`、`mABC/contracts/token_contract.py:40`。
- **交易执行**: 所有动作由 `ChainClient` 创建交易并上链，执行由 `StateProcessor` 分发。参考 `mABC/core/client.py:182` 与 `mABC/core/state.py:157`。
- **数据来源**: 仅读取 `mABC/data/metric/endpoint_stats.json` 与 `mABC/data/topology/endpoint_maps.json`；缺失将提示错误。
- **前端联动**: 成功后刷新 `SOP`、`Voting`、`Economy` 三块数据面板。

### 4. 如何更换数据集
- 将真实数据文件放入：
  - 指标：`mABC/data/metric/endpoint_stats.json`
  - 拓扑：`mABC/data/topology/endpoint_maps.json`
- 建议保持时间键格式为 `YYYY-MM-DD HH:MM:SS`，并包含 `calls`、`error_rate`、`average_duration` 等字段，便于概率推理。

### 5. 常见问题
- **分析失败**：请确认 `mABC/data/metric/endpoint_stats.json` 与 `mABC/data/topology/endpoint_maps.json` 文件存在且格式正确。
- **端口占用**：若 `5173` 或 `8000` 已被占用，请修改启动脚本或更换端口后重试。

### 3.查看区块
在"区块浏览器"标签页中，可以浏览所有区块，点击"查看详情"按钮查看区块的详细信息。

### 4.搜索交易
在"交易追踪"标签页中，输入交易哈希进行搜索，或浏览所有交易列表。

### 5.验证交易
在"审计视图"标签页中，输入区块索引和交易索引，系统将生成并验证Merkle Proof，生成可信审计报告。

### 6.查看博弈
在“经济看板”中查看 Agent 们如何基于自身的权益（Stake + Reputation）对提案进行投票表决。

### 7.审计交易
在“审计视图”中输入区块高度和交易索引，系统将计算并展示 Merkle Proof 路径，验证该交易的有效性。

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

## ⚠️ 注意事项与常见问题

### 1. 数据持久化
- 本地数据库文件位于项目根目录的 `state.db`。
- 该文件在 `.gitignore` 中已被忽略，**请勿上传到代码仓库**。
- 如果遇到数据异常或想要从头开始，请直接点击前端的 **"重置"** 按钮，系统会自动清理数据库并重置内存状态。

### 2. 端口占用
- 后端默认占用 **8000** 端口，前端默认占用 **5173** 端口。
- 启动前请确保这些端口未被其他程序占用。
- 如果启动失败，请检查命令行窗口中的报错信息。

### 3. 生成数据失败？
- 请确保后端服务 (`api_server.py`) 正在运行。
- 如果点击“生成数据”后无反应或报错，请尝试刷新页面。
- 如果后端控制台显示 500 错误，请尝试点击 **"重置"** 按钮修复状态。

### 4. 浏览器兼容性
- 推荐使用最新版的 Chrome, Edge 或 Firefox 浏览器以获得最佳体验。
