from settings import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, OPENAI_MAX_RETRIES, OPENAI_RETRY_SLEEP, OPENAI_MODEL
from openai import OpenAI
import time

def llm_chat(shared_messages, stop_words):
    for i in range(OPENAI_MAX_RETRIES):
        try:
            client = OpenAI(
                api_key=DASHSCOPE_API_KEY,
                base_url=DASHSCOPE_BASE_URL,
            )
            completion = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=shared_messages,
                stop=stop_words,
                # max_tokens=4096,
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

