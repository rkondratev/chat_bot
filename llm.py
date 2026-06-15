import asyncio
import logging
from openrouter import OpenRouter
from env import LLM_API_KEY

logger = logging.getLogger(__name__)

LLM_TIMEOUT = 8

async def check_with_llm(message_text: str) -> bool:
    prompt = (
        "Является ли следующее сообщение спамом или вредоносным? "
        'Ответь только "да" или "нет". '
        f"Сообщение: {message_text}"
    )

    def _call_llm():
        with OpenRouter(api_key=LLM_API_KEY) as client:
            response = client.chat.send(
                model="openrouter/owl-alpha",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            return (
                response.choices[0]
                .message.content
                .strip()
                .lower()
            )

    try:
        answer = await asyncio.wait_for(
            asyncio.to_thread(_call_llm),
            timeout=LLM_TIMEOUT
        )

        logger.info(f"LLM response: {answer}")
        return "да" in answer

    except asyncio.TimeoutError:
        logger.error(f"LLM timeout after {LLM_TIMEOUT}s. Fallback to spam.")
        return True

    except Exception as e:
        logger.error(f"OpenRouter API error: {e}. Fallback to spam.")
        return True
