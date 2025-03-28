import os
import time
import logging
from openai import OpenAI
from dotenv import load_dotenv
from dataclasses import dataclass
import backoff

# 设置日志记录
logger = logging.getLogger('api_calls')
logger.setLevel(logging.DEBUG)

# 移除所有现有的处理器
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# 创建日志目录
log_dir = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), 'logs')
os.makedirs(log_dir, exist_ok=True)

# 设置文件处理器
log_file = os.path.join(log_dir, f'api_calls_{time.strftime("%Y%m%d")}.log')
print(f"Creating log file at: {log_file}")

try:
    file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='a')
    file_handler.setLevel(logging.DEBUG)
    print("Successfully created file handler")
except Exception as e:
    print(f"Error creating file handler: {str(e)}")

# 设置控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# 设置日志格式
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# 添加处理器
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# 立即测试日志记录
logger.debug("Logger initialization completed")
logger.info("API logging system started")

# 状态图标
SUCCESS_ICON = "✓"
ERROR_ICON = "✗"
WAIT_ICON = "⟳"


@dataclass
class ChatMessage:
    content: str


@dataclass
class ChatChoice:
    message: ChatMessage


@dataclass
class ChatCompletion:
    choices: list[ChatChoice]


# 获取项目根目录
project_root = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(project_root, '.env')

# 加载环境变量
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)
    logger.info(f"{SUCCESS_ICON} 已加载环境变量: {env_path}")
else:
    logger.warning(f"{ERROR_ICON} 未找到环境变量文件: {env_path}")

# 验证环境变量
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")
model = os.getenv("OPENAI_MODEL")

if not api_key:
    logger.error(f"{ERROR_ICON} 未找到 OPENAI_API_KEY 环境变量")
    raise ValueError("OPENAI_API_KEY not found in environment variables")
if not model:
    model = "gpt-3.5-turbo"
    logger.info(f"{WAIT_ICON} 使用默认模型: {model}")

# 初始化 OpenAI 客户端
client = OpenAI(api_key=api_key, base_url=base_url)
logger.info(f"{SUCCESS_ICON} OpenAI 客户端初始化成功")


@backoff.on_exception(
    backoff.expo,
    (Exception),
    max_tries=5,
    max_time=300,
    giveup=lambda e: "rate limit" not in str(e).lower()
)
def generate_content_with_retry(model, messages, config=None, tools=None, tool_choice=None):
    """带重试机制的内容生成函数"""
    try:
        logger.info(f"{WAIT_ICON} 正在调用 OpenAI API...")
        logger.info(f"请求内容: {messages[:500]}..." if len(
            str(messages)) > 500 else f"请求内容: {messages}")
        logger.info(f"请求配置: {config}")

        # 准备API调用参数
        api_params = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4096
        }

        # 如果提供了工具，添加到参数中
        if tools:
            logger.info(f"使用工具: {tools}")
            api_params["tools"] = tools

        # 如果提供了工具选择，添加到参数中
        if tool_choice:
            logger.info(f"工具选择: {tool_choice}")
            api_params["tool_choice"] = tool_choice

        response = client.chat.completions.create(**api_params)

        logger.info(f"{SUCCESS_ICON} API 调用成功")

        # 检查是否有工具调用
        if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
            logger.info(f"检测到工具调用: {response.choices[0].message.tool_calls}")
            # 返回完整的消息对象，包括工具调用
            result = {
                "content": response.choices[0].message.content,
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": tool_call.type,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    }
                    for tool_call in response.choices[0].message.tool_calls
                ]
            }
            # logger.info(f"响应内容: {result}")
            return result
        else:
            # 如果没有工具调用，只返回内容
            content = response.choices[0].message.content
            # logger.info(f"响应内容: {content[:500]}..." if len(
                # str(content)) > 500 else f"响应内容: {content}")
            return content
    except Exception as e:
        if "rate limit" in str(e).lower():
            logger.warning(f"{ERROR_ICON} 触发 API 限制，等待重试... 错误: {str(e)}")
            time.sleep(5)
            raise e
        logger.error(f"{ERROR_ICON} API 调用失败: {str(e)}")
        logger.error(f"错误详情: {str(e)}")
        raise e


def get_chat_completion(messages, model=None, max_retries=3, initial_retry_delay=1, tools=None, tool_choice=None):
    """获取聊天完成结果，包含重试逻辑"""
    try:
        if model is None:
            model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

        logger.info(f"{WAIT_ICON} 使用模型: {model}")
        logger.debug(f"消息内容: {messages}")

        for attempt in range(max_retries):
            try:
                # 调用 API
                content = generate_content_with_retry(
                    model=model,
                    messages=messages,
                    tools=tools,
                    tool_choice=tool_choice
                )

                if content is None:
                    logger.warning(
                        f"{ERROR_ICON} 尝试 {attempt + 1}/{max_retries}: API 返回空值")
                    if attempt < max_retries - 1:
                        retry_delay = initial_retry_delay * (2 ** attempt)
                        logger.info(f"{WAIT_ICON} 等待 {retry_delay} 秒后重试...")
                        time.sleep(retry_delay)
                        continue
                    return None

                logger.info(f"{SUCCESS_ICON} 成功获取响应")
                return content

            except Exception as e:
                logger.error(
                    f"{ERROR_ICON} 尝试 {attempt + 1}/{max_retries} 失败: {str(e)}")
                if attempt < max_retries - 1:
                    retry_delay = initial_retry_delay * (2 ** attempt)
                    logger.info(f"{WAIT_ICON} 等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"{ERROR_ICON} 最终错误: {str(e)}")
                    return None

    except Exception as e:
        logger.error(f"{ERROR_ICON} get_chat_completion 发生错误: {str(e)}")
        return None
