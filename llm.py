import logging
from openrouter import OpenRouter
from env import LLM_API_KEY

logger = logging.getLogger(__name__)

async def check_with_llm(message_text: str) -> bool:
    prompt = (
        "Является ли следующее сообщение спамом или вредоносным? "
        'Ответь только "да" или "нет". '
        f"Сообщение: {message_text}"
    )

    try:
        with OpenRouter(api_key=OPENROUTER_API_KEY) as client:
            response = client.chat.send(
                model="openrouter/owl-alpha",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            answer = (
                response.choices[0]
                .message.content
                .strip()
                .lower()
            )

            logger.info(f"LLM response: {answer}")

            return "да" in answer

    except Exception as e:
        logger.error(
            f"OpenRouter API error: {e}. "
            f"Fallback to spam."
        )

        return True
