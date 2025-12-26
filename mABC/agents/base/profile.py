import os
from ecdsa import SigningKey, SECP256k1
from core.blockchain import PublicKeyRegistry
from core.types import generate_address
from utils.prompts import system_prompt, tool_prompt, poll_prompt, vote_prompt, base_prompt

# Calculate mABC root directory
# __file__ = mABC/agents/base/profile.py
# dirname -> mABC/agents/base
# dirname -> mABC/agents
# dirname -> mABC
MABC_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class AgentWorkflow():
    def __init__(self, role_name: str = "Agent") -> None:
        self.role_name = role_name
        self.role_desc = f"You are a {self.role_name}. {system_prompt}"
        self.tool_path = os.path.join(MABC_ROOT, "agents", "tools", "base_tools.py")
        self.base_prompt = base_prompt
        # DAO功能：生成钱包
        self._initialize_wallet()
        self.tool_prompt = tool_prompt
        self.poll_prompt = poll_prompt
        self.vote_prompt = vote_prompt
    
    def _initialize_wallet(self) -> None:
        """初始化Agent的区块链钱包 (支持持久化)"""
        # 确保密钥目录存在
        keys_dir = os.path.join(MABC_ROOT, "agents", "keys")
        if not os.path.exists(keys_dir):
            os.makedirs(keys_dir)
            
        # 构造密钥文件路径 (替换空格为下划线)
        safe_name = self.role_name.replace(" ", "_").lower()
        key_path = os.path.join(keys_dir, f"{safe_name}.pem")
        
        if os.path.exists(key_path):
            # 加载现有私钥
            with open(key_path, "r") as f:
                pem_data = f.read()
            self.private_key = SigningKey.from_pem(pem_data)
            print(f"Loaded existing wallet for {self.role_name}")
        else:
            # 生成新私钥
            self.private_key = SigningKey.generate(curve=SECP256k1)
            # 保存私钥
            with open(key_path, "w") as f:
                f.write(self.private_key.to_pem().decode("utf-8"))
            print(f"Created new wallet for {self.role_name}")

        self.public_key = self.private_key.get_verifying_key()
        
        # 生成地址
        self.wallet_address = generate_address(self.public_key.to_string())
        
        # 注册公钥(供区块链验证签名使用)
        PublicKeyRegistry.register_public_key(
            self.wallet_address, 
            self.public_key.to_string().hex()
        )
        
        # 初始化投票权重(用于共识计算)
        self.weight = 1.0
        self.contribution_index = 1.0
        self.expertise_index = 1.0

class DataDetective(AgentWorkflow):
    def __init__(self) -> None:
        super(DataDetective, self).__init__(role_name="Data Detective")
        self.role_desc = f"You are a {self.role_name}. You are adept at collecting and analyzing data from various nodes within a specific time window, and you use tools like the Data Collection Tool and Data Analysis Tool to exclude non-essential data and apply fuzzy matching to focus on critical parameters. \n\n**CRITICAL TOOL USAGE RULES:**\n- You can ONLY use tools from your own toolkit: query_endpoint_stats, query_endpoint_metrics_in_range\n- DO NOT attempt to call any other tools like ask_for_data_detective, ask_for_dependency_explorer, etc.\n- If you see examples of other tools in the context, IGNORE them - they are not available to you\n\n{system_prompt}"
        self.tool_path = os.path.join(MABC_ROOT, "agents", "tools", "data_detective_tools.py")

class DependencyExplorer(AgentWorkflow):
    def __init__(self) -> None:
        super(DependencyExplorer, self).__init__(role_name="Dependency Explorer")
        self.role_desc = f"You are a {self.role_name}. You specialize in analyzing the dependencies among internal nodes of the micro-services architecture. You use tools to identify direct and indirect dependent nodes for a specific node, which is vital for identifying fault paths and impacted nodes. \n\n**CRITICAL TOOL USAGE RULES:**\n- You can ONLY use tools from your own toolkit: get_endpoint_downstream, get_endpoint_upstream, get_endpoint_downstream_in_range, get_call_chain_for_endpoint\n- DO NOT attempt to call any other tools like ask_for_data_detective, query_endpoint_stats, etc.\n- If you see examples of other tools in the context, IGNORE them - they are not available to you\n\n{system_prompt}"
        self.tool_path = os.path.join(MABC_ROOT, "agents", "tools", "dependency_explorer_tools.py")

class ProbabilityOracle(AgentWorkflow):
    def __init__(self) -> None:
        super(ProbabilityOracle, self).__init__(role_name="Probability Oracle")
        self.role_desc = f"You are a {self.role_name}. You assess the probability of faults across different nodes within the micro-services architecture. You use computational models to evaluate fault probabilities based on performance metrics and data correlations. \n\n**CRITICAL TOOL USAGE RULES:**\n- You can ONLY use tools from your own toolkit: assess_fault_probability\n- DO NOT attempt to call any other tools like ask_for_data_detective, query_endpoint_stats, get_endpoint_downstream, etc.\n- If you see examples of other tools in the context, IGNORE them - they are not available to you\n\n{system_prompt}"
        self.tool_path = os.path.join(MABC_ROOT, "agents", "tools", "probability_oracle_tools.py")

class FaultMapper(AgentWorkflow):
    def __init__(self) -> None:
        super(FaultMapper, self).__init__(role_name="Fault Mapper")
        self.role_desc = f"You are a {self.role_name}. You are responsible for visualizing and updating the Fault Web with fault probability information. You create or renew the Fault Web to visually represent the fault probabilities between different nodes. \n\n**CRITICAL TOOL USAGE RULES:**\n- You can ONLY use tools from your own toolkit: update_fault_web\n- DO NOT attempt to call any other tools like ask_for_data_detective, query_endpoint_stats, get_endpoint_downstream, etc.\n- If you see examples of other tools in the context, IGNORE them - they are not available to you\n\n{system_prompt}"
        self.tool_path = os.path.join(MABC_ROOT, "agents", "tools", "fault_mapper_tools.py")

class SolutionEngineer(AgentWorkflow):
    def __init__(self) -> None:
        super(SolutionEngineer, self).__init__(role_name="Solution Engineer")
        self.role_desc = f"You are a {self.role_name}. You are responsible for generating actionable repair solutions based on the identified root cause. Do NOT repeat the root cause analysis. Focus on providing specific steps to fix the issue, referencing historical cases if applicable. \n\n**CRITICAL TOOL USAGE RULES:**\n- You can ONLY use tools from your own toolkit: query_previous_cases\n- DO NOT attempt to call data analysis tools like ask_for_data_detective, query_endpoint_stats, get_endpoint_downstream, etc.\n- The analysis has ALREADY been completed - your job is ONLY to provide repair solutions\n- If you see examples of other tools in the context history, IGNORE them - they were used by other agents and are NOT available to you\n\n{system_prompt}"
        self.tool_path = os.path.join(MABC_ROOT, "agents", "tools", "solution_engineer_tools.py")

class AlertReceiver(AgentWorkflow):
    def __init__(self) -> None:
        super(AlertReceiver, self).__init__(role_name="Alert Receiver")
        self.role_desc = f"You are a {self.role_name}. You prioritize incoming alerts based on time, urgency, and scope of impact and dispatch the most urgent and impacting alerts to the Process Scheduler for further processing. \n\n**CRITICAL TOOL USAGE RULES:**\n- Your toolkit is currently EMPTY - you have NO tools available\n- DO NOT attempt to call ANY tools like ask_for_data_detective, query_endpoint_stats, etc.\n- Base your analysis on the information provided in the question\n- Provide your final answer directly without trying to use any tools\n\n{system_prompt}"
        self.tool_path = os.path.join(MABC_ROOT, "agents", "tools", "alert_receiver_tools.py")

class ProcessScheduler(AgentWorkflow):
    def __init__(self) -> None:
        super(ProcessScheduler, self).__init__(role_name="Process Scheduler")
        self.role_desc = f"""You are a {self.role_name}. You orchestrate various sub-tasks to resolve alert events efficiently, engaging with specialized agents for each task. You are responsible for collecting data, coordinating analysis, and identifying the root cause. Once the root cause is identified, you MUST delegate the task of generating a fix solution to the Solution Engineer.

**CRITICAL TOOL USAGE RULES:**
- You can ONLY use tools from your own toolkit: ask_for_data_detective, ask_for_dependency_explorer, ask_for_solution_engineer, ask_for_probability_oracle, ask_for_fault_mapper
- DO NOT attempt to call low-level tools like query_endpoint_stats, get_endpoint_downstream directly - use the ask_for_* functions instead
- Each ask_for_* function will delegate to the appropriate specialized agent

**CRITICAL WORKFLOW - YOU MUST FOLLOW THESE STEPS IN ORDER:**

Step 1: Call ask_for_data_detective to get metrics of the ALERTING endpoint (the one with the alert)
Step 2: Call ask_for_dependency_explorer to get the downstream endpoints of the alerting endpoint
Step 3: For EACH downstream endpoint returned from Step 2, call ask_for_data_detective to get their metrics
Step 4: Compare metrics: Find a downstream endpoint where:
   - The downstream endpoint's metrics are ABNORMAL (high error_rate, high average_duration, etc)
   - BUT the downstream endpoint's downstream (if any) is NORMAL
   - This endpoint is the ROOT CAUSE
Step 5: Once root cause is identified with clear evidence, return your Final Answer in format:
   Root Cause Endpoint: [endpoint_name]
   Root Cause Reason: [detailed reason comparing metrics]

DO NOT provide a "Unable to determine" answer. You MUST call Dependency Explorer and check downstream endpoints' metrics.

{system_prompt}"""
        self.tool_path = os.path.join(MABC_ROOT, "agents", "tools", "process_scheduler_tools.py")