import os

FLASH_API = os.getenv("BIG_MODEL_API_KEY")
FLASH_URL = "https://open.bigmodel.cn/api/paas/v4/"
# DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
# DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DASHSCOPE_API_KEY = FLASH_API
DASHSCOPE_BASE_URL = FLASH_URL

OPENAI_MAX_RETRIES = 10
OPENAI_RETRY_SLEEP = 30
# OPENAI_MODEL = "gpt-3.5-turbo"
# OPENAI_MODEL = "gpt-4"
# OPENAI_MODEL = "qwen-turbo"
# OPENAI_MODEL = "qwen-plus"
OPENAI_MODEL = "glm-4.6v-flash"

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
    print("api_key: " ,DASHSCOPE_API_KEY)
    from openai import OpenAI
    client = OpenAI(
        api_key=DASHSCOPE_API_KEY,
        base_url=DASHSCOPE_BASE_URL,
    )
    question = "what is 1 + 1 ?"
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "user", "content": question}
        ]
    )
    print(response)
