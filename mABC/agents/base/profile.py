from ecdsa import SigningKey, SECP256k1
from core.blockchain import PublicKeyRegistry
from core.types import generate_address
from utils.prompts import system_prompt, tool_prompt, poll_prompt, vote_prompt, base_prompt


class AgentWorkflow():
    def __init__(self) -> None:
        self.role_name = "Agent"
        self.role_desc = f"You are a {self.role_name}. {system_prompt}"
        self.tool_path = "agents/tools/base_tools.py"
        self.base_prompt = base_prompt
        # DAO功能：生成钱包
        self._initialize_wallet()
        self.tool_prompt = tool_prompt
        self.poll_prompt = poll_prompt
        self.vote_prompt = vote_prompt
    
    def _initialize_wallet(self) -> None:
        """初始化Agent的区块链钱包"""
        # 生成私钥和公钥
        self.private_key = SigningKey.generate(curve=SECP256k1)
        self.public_key = self.private_key.get_verifying_key()
        
        # 生成地址
        self.wallet_address = generate_address(self.public_key.to_string())
        
        # 注册公钥（供区块链验证签名使用）
        PublicKeyRegistry.register_public_key(
            self.wallet_address, 
            self.public_key.to_string().hex()
        )
        
        # 初始化投票权重（用于共识计算）
        self.weight = 1.0
        self.contribution_index = 1.0
        self.expertise_index = 1.0

class DataDetective(AgentWorkflow):
    def __init__(self) -> None:
        super(DataDetective, self).__init__()
        self.role_name = "Data Detective"
        self.role_desc = f"You are a {self.role_name}. You are adept at collecting and analyzing data from various nodes within a specific time window, and you use tools like the Data Collection Tool and Data Analysis Tool to exclude non-essential data and apply fuzzy matching to focus on critical parameters. {system_prompt}"
        self.tool_path = "agents/tools/data_detective_tools.py"

class DependencyExplorer(AgentWorkflow):
    def __init__(self) -> None:
        super(DependencyExplorer, self).__init__()
        self.role_name = "Dependency Explorer"
        self.role_desc = f"You are a {self.role_name}. You specialize in analyzing the dependencies among internal nodes of the micro-services architecture. You use tools to identify direct and indirect dependent nodes for a specific node, which is vital for identifying fault paths and impacted nodes. {system_prompt}"
        self.tool_path = "agents/tools/dependency_explorer_tools.py"

class ProbabilityOracle(AgentWorkflow):
    def __init__(self) -> None:
        super(ProbabilityOracle, self).__init__()
        self.role_name = "Probability Oracle"
        self.role_desc = f"You are a {self.role_name}. You assess the probability of faults across different nodes within the micro-services architecture. You use computational models to evaluate fault probabilities based on performance metrics and data correlations. {system_prompt}"
        self.tool_path = "agents/tools/probability_oracle_tools.py"

class FaultMapper(AgentWorkflow):
    def __init__(self) -> None:
        super(FaultMapper, self).__init__()
        self.role_name = "Fault Mapper"
        self.role_desc = f"You are a {self.role_name}. You are responsible for visualizing and updating the Fault Web with fault probability information. You create or renew the Fault Web to visually represent the fault probabilities between different nodes. {system_prompt}"
        self.tool_path = "agents/tools/fault_mapper_tools.py"

class SolutionEngineer(AgentWorkflow):
    def __init__(self) -> None:
        super(SolutionEngineer, self).__init__()
        self.role_name = "Solution Engineer"
        self.role_desc = f"You are a {self.role_name}. You are responsible for generating actionable repair solutions based on the identified root cause. Do NOT repeat the root cause analysis. Focus on providing specific steps to fix the issue, referencing historical cases if applicable. {system_prompt}"
        self.tool_path = "agents/tools/solution_engineer_tools.py"

class AlertReceiver(AgentWorkflow):
    def __init__(self) -> None:
        super(AlertReceiver, self).__init__()
        self.role_name = "Alert Receiver"
        self.role_desc = f"You are a {self.role_name}. You prioritize incoming alerts based on time, urgency, and scope of impact and dispatch the most urgent and impacting alerts to the Process Scheduler for further processing. {system_prompt}"
        self.tool_path = "agents/tools/alert_receiver_tools.py"

class ProcessScheduler(AgentWorkflow):
    def __init__(self) -> None:
        super(ProcessScheduler, self).__init__()
        self.role_name = "Process Scheduler"
        self.role_desc = f"You are a {self.role_name}. You orchestrate various sub-tasks to resolve alert events efficiently, engaging with specialized agents for each task. You are responsible for collecting data, coordinating analysis, and identifying the root cause. Once the root cause is identified, you MUST delegate the task of generating a fix solution to the Solution Engineer. {system_prompt}"
        self.tool_path = "agents/tools/process_scheduler_tools.py"