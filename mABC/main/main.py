
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# os.environ['OPENAI_API_KEY'] = 'sk-6c3edf31bf214509bac30a69957b302b'

# 确保工作目录是 mABC 目录
script_dir = os.path.dirname(os.path.abspath(__file__))
mABC_dir = os.path.dirname(script_dir)
os.chdir(mABC_dir)
print(f"🔍 DEBUG: 工作目录设置为 {os.getcwd()}")

from agents.base.profile import DataDetective, DependencyExplorer, ProbabilityOracle, FaultMapper, AlertReceiver, ProcessScheduler, SolutionEngineer
from agents.base.run import ReActTotRun, ThreeHotCotRun, BaseRun
from agents.base.dao_run import DAOExecutor
from agents.tools import process_scheduler_tools, alert_receiver_tools, solution_engineer_tools
from core.vm import Blockchain
from core.state import world_state
import json

def extract_final_answer(text):
    if "Final Answer:" in text:
        return text.split("Final Answer:")[-1].strip()
    return text

if __name__ == "__main__":
    i = 0
    results = []
    
    # 初始化区块链
    print("正在初始化区块链...")
    blockchain = Blockchain()
    
    # 初始化所有Agent的账户
    print("正在初始化Agent账户...")
    all_agents = [
        DataDetective(), 
        DependencyExplorer(),

        ProbabilityOracle(), 
        FaultMapper(), 
        AlertReceiver(), 
        ProcessScheduler(), 
        SolutionEngineer()
    ]
    
    for agent in all_agents:
        account = world_state.get_account(agent.wallet_address)
        if account is None:
            account = world_state.create_account(agent.wallet_address)
        account.balance = 1000000  # 每个Agent初始1000000 Token（足以支付投票gas和质押）
        account.reputation = 100
        world_state.update_account(account)
        print(f"✅ {agent.role_name}: 余额={account.balance} Token")
    
    # 创建DAO执行器（使用区块链投票）
    # alpha=-1, beta=-1 表示禁用投票机制，直接通过
    dao_executor = DAOExecutor(blockchain, alpha=0.5, beta=0.5)
    print("✅ DAO执行器初始化完成（投票已禁用）\n")
    
    log_file = open("output.log", "w", encoding="utf-8")
    original_stdout = sys.stdout
    
    print("🔍 DEBUG: 即将重定向stdout", flush=True)

    try:
        print("🔍 DEBUG: 正在打开 data/label/label.json...", flush=True)
        with(open("data/label/label.json", "r")) as f:
            print("🔍 DEBUG: 文件已打开，正在加载JSON数据...", flush=True)
            data = json.load(f)
        
        print("🔍 DEBUG: JSON数据加载完成，即将重定向stdout到文件", flush=True)
        sys.stdout = log_file
        print(f"🔍 DEBUG: 已加载数据，总时间戳数: {len(data)}")
        original_stdout.write(f"🔍 DEBUG: 已加载数据，总时间戳数: {len(data)}\n")
        original_stdout.flush()
        
        original_stdout.write("🔍 DEBUG: 即将进入外层循环\n")
        original_stdout.flush()
        print("🔍 DEBUG: 即将进入外层循环")
        
        for t, v in data.items():
            original_stdout.write(f"🔍 DEBUG: 处理时间戳 {t}，端点数: {len(v)}\n")
            original_stdout.flush()
            print(f"🔍 DEBUG: 处理时间戳 {t}，端点数: {len(v)}")
            for endpoint, path in v.items():
                original_stdout.write(f"🔍 DEBUG: 迭代次数 {i}, 时间戳 {t}, 端点 {endpoint}\n")
                original_stdout.flush()
                print(f"🔍 DEBUG: 迭代次数 {i}, 时间戳 {t}, 端点 {endpoint}")
                print("@" * 30, "Decision Maker", "@" * 30)
                question = f"""Backgroud: In a distributed microservices system, there is a lot of traces across endpoints which represent the dependency relationship between endpoints. A trace consists of a sequence of spans, each representing a call from one endpoint to another when ignore the service level. 
                
Alert generally occurs on the top endpoint at time T for a significant anomaly when the root cause endpoint at time T' is the downstream endpoint of the alerting endpoint. Endpoint A(TA) -> Endpoint B(TB) -> Endpoint C(TC) -> Endpoint D(TD), if the alert occurs on the Endpoint A at time TA, the root cause endpoint is the Endpoint C at time TC when the metric of Endpoint C is abnormal but the metric of Endpoint D at time TD is normal.

Alert: Endpoint {endpoint} experiencing a significant increase in response time {t}. 
Task: Please find the root cause endpoint behind the alerting endpoint {endpoint} by analyzing the metric of endpoint and the call trace. 
Format: Root Cause Endpoint: XXX, Root Cause Reason: XXX
"""
                
                print(f"Q: {question}")
                original_stdout.write(f"🔍 DEBUG: 正在执行 ProcessScheduler Agent...\n")
                original_stdout.flush()
                print(f"🔍 DEBUG: 正在执行 ProcessScheduler Agent...")
                
                original_stdout.write(f"🔍 DEBUG: 创建 ProcessScheduler 实例\n")
                original_stdout.flush()
                agent = ProcessScheduler()
                original_stdout.write(f"🔍 DEBUG: ProcessScheduler 实例创建完成\n")
                original_stdout.flush()
                
                original_stdout.write(f"🔍 DEBUG: 创建 ReActTotRun 实例\n")
                original_stdout.flush()
                run = ReActTotRun()
                original_stdout.write(f"🔍 DEBUG: ReActTotRun 实例创建完成\n")
                original_stdout.flush()
                
                # 使用DAO执行器进行链上投票
                eval_run = dao_executor
                agents = all_agents  # 使用已初始化的agents
                
                original_stdout.write(f"🔍 DEBUG: 准备调用 run.run()，参数：agent={agent.role_name}, question_length={len(question)}\n")
                original_stdout.flush()
                print(f"🔍 DEBUG: 准备调用 run.run()，参数：agent={agent.role_name}, question_length={len(question)}")
                
                try:
                    original_stdout.write(f"🔍 DEBUG: 进入 run.run() 调用\n")
                    original_stdout.flush()
                    answer1 = run.run(agent=agent, question=question, agent_tool_env=vars(process_scheduler_tools), eval_run=eval_run, agents=agents)
                    original_stdout.write(f"🔍 DEBUG: run.run() 返回成功\n")
                    original_stdout.flush()
                except KeyboardInterrupt:
                    original_stdout.write(f"❌ INTERRUPTED: run.run() 被中断\n")
                    original_stdout.flush()
                    raise
                except Exception as e:
                    original_stdout.write(f"❌ ERROR in run.run(): {str(e)}\n")
                    original_stdout.write(f"❌ Exception type: {type(e).__name__}\n")
                    original_stdout.write(f"❌ Traceback: {__import__('traceback').format_exc()}\n")
                    original_stdout.flush()
                    raise
                
                original_stdout.write(f"🔍 DEBUG: ProcessScheduler Agent 执行完成\n")
                original_stdout.flush()
                print(f"🔍 DEBUG: ProcessScheduler Agent 执行完成")
                print(f"A: {answer1}")
                question2 = "Based on the analysis, please provide a detailed repair solution for the identified root cause. Do NOT repeat the analysis, focus on the fix.\n\nAnalysis:\n" + answer1
                print(f"Q: {question2}")
                
                original_stdout.write(f"🔍 DEBUG: 正在执行 SolutionEngineer Agent...\n")
                original_stdout.flush()
                print(f"🔍 DEBUG: 正在执行 SolutionEngineer Agent...")
                agent = SolutionEngineer()
                agents = [se for se in all_agents if isinstance(se, SolutionEngineer)]  # 使用已初始化的SolutionEngineer
                answer2 = ReActTotRun().run(agent=agent, question=question2, agent_tool_env=vars(solution_engineer_tools), eval_run=dao_executor, agents=agents)
                original_stdout.write(f"🔍 DEBUG: SolutionEngineer Agent 执行完成\n")
                original_stdout.flush()
                print(f"🔍 DEBUG: SolutionEngineer Agent 执行完成")
                print(f"A: {answer2}")
                print("@" * 30, "Solution Engineer", "@" * 30)
                print("\n" * 20)
                
                results.append({
                    "timestamp": t,
                    "endpoint": endpoint,
                    "decision_maker_answer": extract_final_answer(answer1),
                    "solution_engineer_answer": extract_final_answer(answer2)
                })

                i += 1
                original_stdout.write(f"🔍 DEBUG: 迭代计数器更新为 {i}\n")
                original_stdout.flush()
                print(f"🔍 DEBUG: 迭代计数器更新为 {i}")
                if i >= 5:
                    original_stdout.write(f"🔍 DEBUG: 达到限制数 5，正在跳出循环\n")
                    original_stdout.flush()
                    print(f"🔍 DEBUG: 达到限制数 5，正在跳出循环")
                    break
            if i >= 5:
                original_stdout.write(f"🔍 DEBUG: 达到限制数，跳出外层循环\n")
                original_stdout.flush()
                print(f"🔍 DEBUG: 达到限制数，跳出外层循环")
                break
    finally:
        sys.stdout = original_stdout
        log_file.close()
    
    with open("answer.json", "w") as f:
        json.dump(results, f, indent=4)
    print("completed")
