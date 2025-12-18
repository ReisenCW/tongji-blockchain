# 执行一段字符串形式的代码，并返回结果
# eg. act_eval("1 + 1", {}) 返回 2
def act_eval(action, tool_env):
    try:
        action_result = eval(action, tool_env)
    except Exception as e:
        action_result = str(e)
    return action_result