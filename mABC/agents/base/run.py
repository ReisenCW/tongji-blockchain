from random import uniform
from utils.llm import llm_chat
from utils.generate_tools import get_agent_tool_list_prompt
from utils.act_eval import act_eval
from agents.base.profile import AgentWorkflow

STOP_WORDS_NONE = ""
STOP_WORDS_REACT = "\nObservation"

REACT_STATUS_RE = "Reason"
REACT_STATUS_ACT = "Act"
REACT_STATUS_FINISH = "Finish"

TOT_CHILDREN_NUM = 1 # 多轮采样的子节点数量

# agent基类, 定义了基本的运行框架和方法
class BaseRun:
    def __init__(self):
        pass

    def qa(self, messages, stop_words=STOP_WORDS_NONE):
        answer = llm_chat(messages, stop_words=stop_words)
        print("*" * 50)
        print(messages)
        print("*" * 50)
        print(f"A: {answer}")
        print("*" * 50, end="\n\n")
        return answer

    def run(self, agent: AgentWorkflow, question: str):
        messages = [
            {"role": "system", "content": f"{agent.role_desc}{agent.base_prompt}"},
            {"role": "user", "content": question},
        ]
        answer = self.qa(messages, stop_words=STOP_WORDS_NONE)
        messages.append({"role": "assistant", "content": answer})
        return messages

# 多轮投票运行类, 继承自BaseRun, 实现了多轮投票机制
class ThreeHotCotRun(BaseRun):
    def __init__(self, alpha=-1, beta=-1):
        self.alpha = alpha      # 支持率阈值
        self.beta = beta        # 参与率阈值
        self.w_c_max = 1.5      # 最大贡献指数
        self.w_e_max = 1.5      # 最大专业指数
        self.delta = 0.03       # 贡献指数的最大衰减率

    def run(self, agents, poll_role, poll_problem, poll_content):
        poll_initiator = ""
        poll_reason = ""
        total_weight = sum(agent.weight for agent in agents)
        # 遍历agent, 进行投票, 直到有agent发起投票
        for agent in agents:
            poll_result = self.poll(agent, poll_role, poll_problem, poll_content)
            # 找到第一个发起投票的agent
            if poll_result['poll'] == "Yes":
                poll_initiator = agent.role_name
                poll_reason = poll_result['reason']
                break
        # 如果禁用了投票, 则直接返回True
        if self.alpha == -1 and self.beta == -1:
            return True
        # 如果没有agent发起投票, 则无异议, 默认通过, 返回True
        if poll_initiator == "":
            run_result = True
        else:
            # 进行投票统计和结果计算
            vote_results = []
            vote_weights = {"For": 0, "Against": 0, "Abstain": 0}
            for agent in agents:
                vote_result = self.submit_vote(agent, poll_initiator, poll_reason, poll_role, poll_problem, poll_content)
                vote_results.append(vote_result)
                vote_weights[vote_result] += agent.weight
            support_rate = vote_weights["For"] / total_weight
            participation_rate = (vote_weights["For"] + vote_weights["Against"]) / total_weight
            run_result = support_rate >= self.alpha and participation_rate >= self.beta
        # 更新权重
        self.update_weights(agents, vote_results, run_result)
        return run_result
    
    # 根据投票结果和运行结果更新agent的权重
    def update_weights(self, agents, vote_results, run_result):
        """
        Update the voting weights of agents based on their participation and decision accuracy.

        Args:
            agents (list): List of AgentWorkflow instances.
            vote_results (list): List of voting results from agents.
            run_result (bool): The outcome of the voting process.
        """
        # 遍历每个agent和对应的投票结果
        for agent, vote in zip(agents, vote_results):
            # 贡献指数自动衰减, 鼓励持续参与投票
            agent.contribution_index = min(agent.contribution_index * (1 - uniform(0, self.delta)), self.w_c_max)
            # 如果没有弃权, 则增加贡献指数
            if vote != "Abstain":
                agent.contribution_index += 0.1  # Active participation increment
                agent.contribution_index = min(agent.contribution_index, self.w_c_max)

            # 更新专业指数
            # 如果投票与运行结果一致, 则增加专业指数, 否则减少专业指数
            if ((vote == "For" and run_result) or (vote == "Against" and not run_result)):
                agent.expertise_index += 0.01  # Correct decision increment
            else:
                agent.expertise_index -= 0.01  # Incorrect decision decrement
            agent.expertise_index = max(min(agent.expertise_index, self.w_e_max), 1.0)

            # 更新agent的整体权重(贡献指数 * 专业指数)
            agent.weight = agent.contribution_index * agent.expertise_index
    
    # 进行投票, 返回投票结果和理由
    def poll(self, agent: AgentWorkflow, poll_role, poll_problem, poll_content):
        messages = [
            {"role": "system", "content": f"{agent.role_desc}{agent.base_prompt}"},
            {"role": "user", "content": f"{agent.poll_prompt}".format(poll_role=poll_role, poll_problem=poll_problem, poll_content=poll_content)},
        ]
        answer = self.qa(messages, stop_words=STOP_WORDS_NONE)
        result = self.parse_in_poll(answer)
        return result
    
    # 解析投票结果
    def parse_in_poll(self, answer):
        result = {
            "poll": None,
            "reason": None,
        }
        # 提取投票结果和理由
        if "Poll:" in answer and "Reason:" in answer:
            result["poll"] = answer.split("Poll:")[1].split("\n")[0].strip()
            result["reason"] = answer.split("Reason:")[1].strip()
        # 处理可能的格式问题
        if result["poll"] not in ["Yes", "No"]:
            if "Yes" in answer:
                result["poll"] = "Yes"
            elif "No" in answer:
                result["poll"] = "No"
        return result

    # 提交投票, 返回投票结果(赞同/反对/弃权)
    def submit_vote(self, agent: AgentWorkflow, poll_initiator, poll_reason, poll_role, poll_problem, poll_content):
        messages = [
            {"role": "system", "content": f"{agent.role_desc}{agent.base_prompt}"},
            {"role": "user", "content": f"{agent.vote_prompt}".format(poll_initiator=poll_initiator, poll_reason=poll_reason, poll_role=poll_role, poll_problem=poll_problem, poll_content=poll_content)},
        ]
        answer = self.qa(messages, stop_words=STOP_WORDS_NONE)
        result = self.parse_in_vote(answer)
        return result
    
    # 解析投票结果
    def parse_in_vote(self, answer):
        result = {
            "option": None
        }
        if "Option: " in answer:
            result["option"] = answer.split("Option:")[1].split("\n")[0].strip()
        if result["option"] not in ["For", "Against", "Abstain"]:
            if "For" in answer:
                result["option"] = "For"
            elif "Against" in answer:
                result["option"] = "Against"
            elif "Abstain" in answer:
                result["option"] = "Abstain"
        return result

# ReAct-TOT多轮运行类
class ReActTotRun(BaseRun):
    def __init__(self):
        self.max_history_length = 5000  # 设置历史记录最大长度

    def check_and_summarize(self, history, question):
        """
        Check if history is too long and summarize it if necessary.
        Always keep the 'Question' (Task Goal/Key Facts) at the beginning.
        """
        if len(history) < self.max_history_length:
            return history
        
        prefix = f"Question: {question}"
        # 如果历史记录以问题开头（通常都是），则保留问题，压缩中间部分
        if history.startswith(prefix):
            content_to_summarize = history[len(prefix):]
            
            # 保留最近的 1500 个字符，防止丢失最近的上下文
            keep_length = 1500
            if len(content_to_summarize) > keep_length:
                context_to_keep = content_to_summarize[-keep_length:]
                to_summarize = content_to_summarize[:-keep_length]
                
                summary_prompt = [
                    {"role": "system", "content": "You are a helpful assistant. Summarize the following history of thoughts, actions and observations. Keep important facts, the sequence of events, and the current state of investigation. Be concise."},
                    {"role": "user", "content": to_summarize}
                ]
                print("--- Summarizing History ---")
                summary = self.qa(summary_prompt)
                print("--- Summary Complete ---")
                
                new_history = f"{prefix}\n\n[Summary of previous steps]: {summary}\n\n[Recent actions]:\n{context_to_keep}"
                return new_history
        
        return history

    def run(self, agent: AgentWorkflow, question: str, agent_tool_env, eval_run, agents, history="", index=0):
        # 获取历史记录, 如果没有则初始化
        history = f"Question: {question}" if history == "" else history
        
        # 检查并总结历史记录，防止 Lost in the Middle
        history = self.check_and_summarize(history, question)

        # 进行多轮采样下一步
        step_status_record_list = self.sample_multi_next_step(agent, question, agent_tool_env, eval_run, agents, history)
        # 选择最佳步骤记录
        index = 0
        best_step_status_record = step_status_record_list[index]
        history = history + best_step_status_record["record"]
        # 如果没有完成, 则继续下一轮
        if best_step_status_record["status"] != REACT_STATUS_FINISH:
            return self.run(agent, question, agent_tool_env, eval_run, agents, history, index + 1)
        else:
            # return history.split("Final Answer:")[1].strip()
            return history

    # 多轮采样下一步
    def sample_multi_next_step(self, agent: AgentWorkflow, question, agent_tool_env, eval_run, agents, history="", num=TOT_CHILDREN_NUM):
        step_status_record_list = []
        for _ in range(num):
            status, step_record = self.eval_and_run_one_step(agent, question, agent_tool_env, eval_run, agents, history)
            step_status_record_list.append(
                {
                    "status": status,
                    "record": step_record,
                }
            )
        return step_status_record_list
    
    def eval_and_run_one_step(self, agent: AgentWorkflow, question, agent_tool_env, eval_run: ThreeHotCotRun, agents, history=""):
        status, step_record = self.run_one_step(agent, question, agent_tool_env, history)
        
        # 只在得出最终答案时才触发投票验证，中间步骤不投票
        if status == REACT_STATUS_FINISH:
            # 启用投票验证机制 - 仅对最终答案投票
            result = eval_run.run(agents, agent.role_name, question, history + step_record)
            # 如果投票结果为True，代表最终答案通过
            if result:
                return status, step_record
            # 否则，重新执行整个流程
            else:
                print("❌ 最终答案未通过投票，重新分析...")
                return self.eval_and_run_one_step(agent, question, agent_tool_env, eval_run, agents, history)
        else:
            # 中间步骤（Action/Thought）直接通过，不触发投票
            return status, step_record

    # 进行一步运行, 状态变化如下:
    # REACT_STATUS_RE => REACT_STATUS_ACT/REACT_STATUS_FINISH
    # REACT_STATUS_ACT => REACT_STATUS_RE
    def run_one_step(self, agent: AgentWorkflow, question, agent_tool_env, history=""):
        # history  保存过去的所有操作和思考
        history = f"Question: {question}" if history == "" else history
        status = REACT_STATUS_RE
        step_record = ""
        reason_loop_count = 0
        consecutive_no_data = 0  # 追踪连续获得无数据结果的次数
        previous_action = None  # 追踪上一个执行的动作
        
        # 根据Agent类型设置不同的最大循环次数
        # ProcessScheduler需要更多步骤（查询多个端点+分析）
        if "Process Scheduler" in agent.role_name:
            max_reason_loops = 15  # ProcessScheduler需要更多步骤
        else:
            max_reason_loops = 5   # 其他Agent保持5次
        
        while status == REACT_STATUS_RE:
            reason_loop_count += 1
            print(f"🔍 DEBUG: Reason循环次数 {reason_loop_count}/{max_reason_loops}")
            
            if reason_loop_count > max_reason_loops:
                print(f"❌ ERROR: Reason循环超过最大次数({max_reason_loops})，强制退出")
                final_answer = "Unable to determine root cause after multiple reasoning steps."
                step_record += f"\nFinal Answer: {final_answer}"
                return REACT_STATUS_FINISH, step_record
            
            # 当在Reason状态时，将上一步的输出（如有）和历史记录累积作为新的输入
            step_input = history
            result = self.reason(agent, step_input)
            status = result["status"]
            thought = result["thought"]
            step_record += f"\nThought: {thought}"  # 将这一步的输出Thought加入历史记录
            print(f"🔍 DEBUG: Reason完成，返回状态: {status}")
            
        if status == REACT_STATUS_ACT:
            # 如果我们处于ACT状态，则执行相应的操作，并更新状态
            action_tool_name = result["action_tool_name"]
            action_tool_input = result["action_tool_input"]
            step_record += f"\nAction Tool Name: {action_tool_name}"
            step_record += f"\nAction Tool Input: {action_tool_input}"
            action = f"{action_tool_name}({action_tool_input})"
            
            # 检查是否重复执行相同的动作
            if action == previous_action:
                print(f"⚠️  WARNING: 重复执行相同的动作，这可能导致无限循环")
                consecutive_no_data += 1
                if consecutive_no_data >= 3:
                    print(f"❌ ERROR: 连续{consecutive_no_data}次执行相同动作且无结果，强制退出")
                    final_answer = "Unable to determine root cause - repeated queries returned no data. The required endpoint data is not available."
                    step_record += f"\nFinal Answer: {final_answer}"
                    return REACT_STATUS_FINISH, step_record
            else:
                consecutive_no_data = 0  # 重置计数器
            
            previous_action = action
            status, step_output = self.act(action, agent_tool_env)  # 执行动作
            
            # 检查是否返回了无数据标志
            if isinstance(step_output, str) and "[NO_DATA]" in step_output:
                consecutive_no_data += 1
                print(f"⚠️  WARNING: 查询返回无数据 ({consecutive_no_data} times)")
                if consecutive_no_data >= 3:
                    print(f"❌ ERROR: 连续{consecutive_no_data}次查询无数据，可能该端点在该时间段无活动")
                    final_answer = "Unable to determine root cause - the endpoint has no data at the specified time. Please verify the endpoint name or time period."
                    step_record += f"\nFinal Answer: {final_answer}"
                    return REACT_STATUS_FINISH, step_record
            else:
                consecutive_no_data = 0  # 重置计数器
            
            step_record += f"\nObservation: the result of {action} is {step_output}"  # 将这一步的输出加入历史记录
        elif status == REACT_STATUS_FINISH:
            final_answer = result["final_answer"]
            step_record += f"\nFinal Answer: {final_answer}"  # 记录最终答案到历史
        return status, step_record

    # 进行推理, 返回状态和结果
    def reason(self, agent: AgentWorkflow, question):
        print(f"🔍 DEBUG: 进入 reason 方法")
        tools, tool_names = get_agent_tool_list_prompt(agent.tool_path)
        # 先单独格式化 tool_prompt，避免与 role_desc 中的占位符冲突
        formatted_tool_prompt = agent.tool_prompt.format(tools=tools, tool_names=tool_names)
        # 组合所有内容
        system_content = f"{agent.role_desc}{formatted_tool_prompt}{agent.base_prompt}"
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": question},
        ]
        print(f"🔍 DEBUG: 准备调用 llm_chat")
        answer = self.qa(messages, stop_words=STOP_WORDS_REACT)
        print(f"🔍 DEBUG: llm_chat 返回，开始解析")
        result = self.parse(answer)
        print(f"🔍 DEBUG: parse 完成，结果状态: {result['status']}")
        return result

    # 解析推理结果, 返回状态和内容
    def parse(self, answer):
        # 检查是否含有思考过程
        result = {
            "status": REACT_STATUS_RE,
            "thought": None,
            "final_answer": None,
            "action_tool_name": None,
            "action_tool_input": None,
        }
        
        print(f"🔍 DEBUG: 开始解析回复，长度: {len(answer)}")
        print(f"🔍 DEBUG: 回复内容前100字: {answer[:100]}")
        
        if "Thought:" in answer:
            # 提取思考内容
            result["thought"] = (
                answer.split("Thought:")[1]
                .split("Action")[0]
                .split("Final Answer:")[0]
                .strip()
            )
            # 提取Thought部分，假设它出现在Action或Final Answer之前
            print(f"🔍 DEBUG: 检测到 Thought")
        
        # 检查是否含有最终答案
        if "Final Answer:" in answer:
            # 提取最终答案并返回完成状态
            result["final_answer"] = answer.split("Final Answer:")[1].strip()
            result["status"] = REACT_STATUS_FINISH
            print(f"🔍 DEBUG: 检测到 Final Answer，返回完成状态")
            return result
        
        # 检查是否需要执行某个操作
        elif "Action Tool Name:" in answer and "Action Tool Input:" in answer:
            # 提取行动指令并返回行动状态
            action_tool_name = (
                answer.split("Action Tool Name:")[1]
                .split("Action Tool Input:")[0]
                .strip()
            )
            action_tool_input = (
                answer.split("Action Tool Input:")[1].split("Observation:")[0].strip()
            )
            result["action_tool_name"] = action_tool_name
            result["action_tool_input"] = action_tool_input
            result["status"] = REACT_STATUS_ACT
            print(f"🔍 DEBUG: 检测到 Action Tool: {action_tool_name}")
            return result
        
        # 如果没有最终答案也没有行动指令，返回思考状态（重新思考）
        else:
            print(f"🔍 DEBUG: 未检测到 Final Answer 或 Action Tool，继续思考")
            return result

    # 执行行动, 返回新的状态和输出结果
    def act(self, action, agent_tool_env):
        # 执行一个函数, 返回结果
        action_result = act_eval(action, agent_tool_env)
        return REACT_STATUS_RE, action_result  # 行动后返回到重新思考状态

