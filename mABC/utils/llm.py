from settings import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, OPENAI_MAX_RETRIES, OPENAI_RETRY_SLEEP, OPENAI_MODEL
from openai import OpenAI
import time

client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url=DASHSCOPE_BASE_URL,
)

def llm_chat(shared_messages, stop_words, temperature=0.3):
    """
    调用 LLM 进行对话
    
    Args:
        shared_messages: 对话历史
        stop_words: 停止词
        temperature: 生成温度，越低越谨慎
    
    Returns:
        LLM 生成的内容
    """
    # Ensure stop_words is a list or None
    stop = None
    if stop_words:
        if isinstance(stop_words, str):
            stop = [stop_words]
        elif isinstance(stop_words, list):
            stop = stop_words
        else:
            stop = [str(stop_words)]
    for _ in range(OPENAI_MAX_RETRIES):
        try:
            completion = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=shared_messages,
                stop=stop,
                temperature=temperature,  # 添加 temperature 参数，默认 0.3 使 Agent 更加谨慎
            )
            print(completion)
            return completion.choices[0].message.content
        except Exception as e:
            print(e)
            time.sleep(OPENAI_RETRY_SLEEP)
            continue
    return "Connection error."

if __name__ == "__main__":
    shared_messages = [
        {"role": "system", "content": "You are a poetic assistant, skilled in explaining complex programming concepts with creative flair."},
    ]
    shared_messages.append({"role": "user", "content": "Compose a poem that explains the concept of recursion in programming."})
    answer = llm_chat(shared_messages, "")
    shared_messages.append({"role": "assistant", "content": answer})

    print(shared_messages, answer)

