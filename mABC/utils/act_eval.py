# 执行一段字符串形式的代码，并返回结果
# eg. act_eval("1 + 1", {}) 返回 2
def act_eval(action, tool_env):
    try:
        action_result = eval(action, tool_env)
        # 如果结果是空字典或空列表，提示这是无数据的结果
        if action_result == {} or action_result == []:
            action_result = f"[NO_DATA] The query returned no data. The endpoint or time period may not have data available."
    except TypeError as e:
        # 参数类型错误
        error_msg = str(e)
        if "takes" in error_msg and "positional argument" in error_msg:
            action_result = f"[PARAM_ERROR] Invalid parameters for tool call. Error: {error_msg}. Check the tool definition for correct parameter names and types."
        else:
            action_result = f"[TYPE_ERROR] {error_msg}"
    except SyntaxError as e:
        # 语法错误
        action_result = f"[SYNTAX_ERROR] Invalid tool call syntax. Check that all parameters are properly formatted with correct commas and quotes. Error: {e}"
    except NameError as e:
        # 未定义的变量或函数
        action_result = f"[NAME_ERROR] Tool or parameter not found. Make sure you are using the correct tool name. Error: {e}"
    except Exception as e:
        action_result = f"[ERROR] {type(e).__name__}: {str(e)}"
    return action_result