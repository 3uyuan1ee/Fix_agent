"""使用LangChain model进行精确token计数的实用工具。"""

from pathlib import Path

from langchain_core.messages import SystemMessage

from ..config.config import console


def calculate_baseline_tokens(model, agent_dir: Path, system_prompt: str) -> int:
    """使用模型的官方分词器计算基线上下文token数。

    这使用模型的get_num_tokens_from_messages()方法来获取初始上下文（系统提示+agent.md）的精确token计数。

    注意：由于LangChain限制，工具定义无法在第一次API调用之前准确计数。
    它们将在第一条消息发送后包含在总数中（约5000个token）。

    Args:
        model: LangChain模型实例 (ChatAnthropic或ChatOpenAI)
        agent_dir: 包含agent.md的代理目录路径
        system_prompt: 基础系统提示字符串

    Returns:
        系统提示+agent.md的token计数（不包括工具）
    """
    # Load agent.md content
    agent_md_path = agent_dir / "agent.md"
    agent_memory = ""
    if agent_md_path.exists():
        agent_memory = agent_md_path.read_text()

    # Build the complete system prompt as it will be sent
    # This mimics what AgentMemoryMiddleware.wrap_model_call() does
    memory_section = f"<agent_memory>\n{agent_memory}\n</agent_memory>"

    # Get the long-term memory system prompt
    memory_system_prompt = get_memory_system_prompt()

    # Combine all parts in the same order as the middleware
    full_system_prompt = (
        memory_section + "\n\n" + system_prompt + "\n\n" + memory_system_prompt
    )

    # Count tokens using the model's official method
    messages = [SystemMessage(content=full_system_prompt)]

    try:
        # Note: tools parameter is not supported by LangChain's token counting
        # Tool tokens will be included in the API response after first message
        token_count = model.get_num_tokens_from_messages(messages)
        return token_count
    except Exception as e:
        # Fallback if token counting fails
        console.print(
            f"[yellow]Warning: Could not calculate baseline tokens: {e}[/yellow]"
        )
        return 0


def get_memory_system_prompt() -> str:
    """获取长期记忆系统提示文本"""
    # Import from agent_memory middleware
    from ..midware.agent_memory import LONGTERM_MEMORY_SYSTEM_PROMPT

    return LONGTERM_MEMORY_SYSTEM_PROMPT.format(memory_path="/memories/")
