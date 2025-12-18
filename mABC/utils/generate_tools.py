import inspect
import re

# 从文件内容中提取函数信息
def extract_functions(file_content):
    pattern = re.compile(
        r"def\s+(\w+)\s*\(([^)]*)\)\s*->\s*([^:]+):\s*('''(.*?)'''|\"\"\"(.*?)\"\"\")",
        re.DOTALL  # DOTALL让 . 匹配包括换行符在内的所有字符
    )
    matches = pattern.findall(file_content)
    functions = []
    for match in matches:
        function_name = match[0]               # 函数名
        parameters = match[1]                  # 参数列表
        return_type = match[2].strip()         # 返回值类型
        doc = (match[4] or match[5]).strip()   # 文档字符串
        functions.append((function_name, parameters, return_type, doc))
    return functions

# 接收 extract_functions 提取的单个函数信息元组，将参数格式化，并按照固定模板生成标准化的函数定义字符串
def get_function_info(func_info):
    function_name, parameters_str, return_type, doc = func_info  # 解包元组
    # 处理参数字符串，转换为期望的格式
    # 假设parameters_str是以逗号分隔的参数列表
    parameters = parameters_str.split(',') if parameters_str else []
    formatted_parameters = []
    for param in parameters:
        # 按冒号分割参数名和参数类型（如 "action: str" → ["action", " str"]）
        param_name, _, param_type = param.partition(':')
        param_name = param_name.strip()
        param_type = param_type.strip() or 'Any'  # 如果没有指定类型，则使用'Any'
        formatted_parameters.append(f"{param_name}: {param_type}")
    # 生成并返回函数定义字符串
    template = '''
    def {function_name}({parameters}) -> {return_type}:
    """
    {doc}
    """
    '''
    return template.format(
        function_name=function_name,
        parameters=', '.join(formatted_parameters),
        return_type=return_type or 'None',  # 如果没有指定返回类型，则使用'None'
        doc=doc
    ), function_name

def get_agent_tool_list_prompt(file_path):
    """
    根据 file_path 中的tool函数自动生成 tool_list_prompt
    """
    with open(file_path, "r") as file:
        file_content = file.read()
    # 提取文件中的所有函数信息
    tool_list = extract_functions(file_content)
    # 对每个函数信息格式化，得到(格式化字符串, 函数名)的列表
    tool_and_tool_name_pair_list = [get_function_info(func) for func in tool_list]
    # 提取所有格式化函数字符串
    tools = [i[0] for i in tool_and_tool_name_pair_list]
    # 提取所有函数名
    tool_names = [i[1] for i in tool_and_tool_name_pair_list]
    # 返回值1: 拼接后的所有函数定义字符串
    # 返回值2: 逗号分隔的所有函数名字符串
    return "".join(tools), ", ".join(tool_names)

# 示例:
# 测试代码片段:
# def act_eval(action: str, tool_env: dict) -> str:
#     '''
#     安全执行字符串形式的代码，返回执行结果或异常信息
#     '''
#     try:
#         return eval(action, tool_env)
#     except Exception as e:
#         return str(e)

# def get_file_size(file_path: str) -> int:
#     """
#     获取文件大小（字节）
#     """
#     import os
#     return os.path.getsize(file_path)

# output:
# 返回值1:
# def act_eval(action: str, tool_env: dict) -> str:
# """
# 安全执行字符串形式的代码，返回执行结果或异常信息
# """

# def get_file_size(file_path: str) -> int:
# """
# 获取文件大小（字节）
# """
#
# 返回值2: act_eval, get_file_size