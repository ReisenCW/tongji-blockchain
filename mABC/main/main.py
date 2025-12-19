
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base.profile import DataDetective, DependencyExplorer, ProbabilityOracle, FaultMapper, AlertReceiver, ProcessScheduler, SolutionEngineer
from agents.base.run import ReActTotRun, ThreeHotCotRun, BaseRun
from agents.tools import process_scheduler_tools, alert_receiver_tools, solution_engineer_tools
import json

def extract_final_answer(text):
    if "Final Answer:" in text:
        return text.split("Final Answer:")[-1].strip()
    return text

if __name__ == "__main__":
    i = 0
    results = []
    
    log_file = open("output.log", "w", encoding="utf-8")
    original_stdout = sys.stdout
    sys.stdout = log_file

    try:
        with(open("data/label/label.json", "r")) as f:
            data = json.load(f)
        for t, v in data.items():
            for endpoint, path in v.items():
                print("@" * 30, "Decision Maker", "@" * 30)
                question = f"""Backgroud: In a distributed microservices system, there is a lot of traces across endpoints which represent the dependency relationship between endpoints. A trace consists of a sequence of spans, each representing a call from one endpoint to another when ignore the service level. 
                
Alert generally occurs on the top endpoint at time T for a significant anomaly when the root cause endpoint at time T' is the downstream endpoint of the alerting endpoint. Endpoint A(TA) -> Endpoint B(TB) -> Endpoint C(TC) -> Endpoint D(TD), if the alert occurs on the Endpoint A at time TA, the root cause endpoint is the Endpoint C at time TC when the metric of Endpoint C is abnormal but the metric of Endpoint D at time TD is normal.

Alert: Endpoint {endpoint} experiencing a significant increase in response time {t}. 
Task: Please find the root cause endpoint behind the alerting endpoint {endpoint} by analyzing the metric of endpoint and the call trace. 
Format: Root Cause Endpoint: XXX, Root Cause Reason: XXX
"""
                
                print(f"Q: {question}")
                agent = ProcessScheduler()
                run = ReActTotRun()
                eval_run = ThreeHotCotRun(0, 0)
                agents = [DataDetective(), DependencyExplorer(), ProbabilityOracle(), FaultMapper(), AlertReceiver(), ProcessScheduler(), SolutionEngineer()]
                answer1 = run.run(agent=agent, question=question, agent_tool_env=vars(process_scheduler_tools), eval_run=eval_run, agents=agents)
                print(f"A: {answer1}")
                question2 = "Based on the analysis, please provide a detailed repair solution for the identified root cause. Do NOT repeat the analysis, focus on the fix.\n\nAnalysis:\n" + answer1
                print(f"Q: {question2}")
                
                agent = SolutionEngineer()
                agents = [SolutionEngineer()]
                answer2 = ReActTotRun().run(agent=agent, question=question2, agent_tool_env=vars(solution_engineer_tools), eval_run=ThreeHotCotRun(), agents=agents)
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
                if i >= 5 :
                    break
    finally:
        sys.stdout = original_stdout
        log_file.close()
    
    with open("answer.json", "w") as f:
        json.dump(results, f, indent=4)
    print("completed")
