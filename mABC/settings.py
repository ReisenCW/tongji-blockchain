import os

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

OPENAI_MAX_RETRIES = 10
OPENAI_RETRY_SLEEP = 30
# OPENAI_MODEL = "gpt-3.5-turbo"
# OPENAI_MODEL = "gpt-4"
OPENAI_MODEL = "qwen-turbo"
# OPENAI_MODEL = "qwen-plus"

# AGENT_STATUS_START = "Start"
# AGENT_STATUS_RE = "Reason"
# AGENT_STATUS_ACT = "Act"
# AGENT_STATUS_FINISH = "Finish"

# STOP_WORDS_REACT = "\nObservation"
# STOP_WORDS_NONE = ""

# ACTION_FAILURE = "action执行失败"
# DEBUG = False


# TOT_CHILDREN_NUM = 1

# TOT_MAX_DEPTH = 15

# # DEFAULT_MODEL = "gpt-3.5-turbo"  # gpt-3.5 -turbo-16k-0613
# # DEFAULT_MODEL = "gpt-4"  # gpt-3.5-turbo-16k-0613
# DEFAULT_MODEL = "gpt-3.5-turbo-0125"

if __name__ == "__main__":
    print(DASHSCOPE_API_KEY)
