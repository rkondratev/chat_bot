import asyncio
import logging
import time

from aiogram import Router, F
from aiogram.types import ChatMemberUpdated, CallbackQuery, Message
from aiogram.filters import ChatMemberUpdatedFilter
from aiogram.filters.chat_member_updated import IS_MEMBER, IS_NOT_MEMBER
from aiogram.exceptions import TelegramBadRequest

from config import (
    VERIFICATION_TIMEOUT,
    ACTION_MODE,
    ADMIN_USERNAME,
    STOP_WORDS
)
from keyboards import get_verification_keyboard
from llm import check_with_llm
from database import (
    add_user_if_not_exists,
    set_user_verified,
    is_user_verified
)

router = Router()
logger = logging.getLogger(__name__)

spam_logger = logging.getLogger("spam")
if not spam_logger.handlers:
    file_handler = logging.FileHandler("spam.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
    spam_logger.addHandler(file_handler)
    spam_logger.setLevel(logging.WARNING)

pending_verifications = {}


@router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def on_user_join(event: ChatMemberUpdated):
    user = event.new_chat_member.user
    chat_id = event.chat.id
    
    msg_obj = getattr(event, 'message', None)
    thread_id = getattr(msg_obj, 'message_thread_id', None) if msg_obj else None

    await add_user_if_not_exists(user.id, user.username, user.first_name)

    if await is_user_verified(user.id):
        return

    keyboard = get_verification_keyboard(user.id)
    mention = f"@{user.username}" if user.username else user.first_name
    text = f"{mention}, у вас есть 3 минуты для верификации, иначе вы будете исключены."
    
    try:
        msg = await event.bot.send_message(
            chat_id=chat_id, text=text, reply_markup=keyboard, message_thread_id=thread_id
        )
    except Exception as e:
        logger.error(f"Failed to send verification message: {e}")
        return

    task = asyncio.create_task(schedule_ban(event.bot, chat_id, user.id, msg.message_id))
    pending_verifications[user.id] = {"task": task, "chat_id": chat_id, "message_id": msg.message_id}


async def schedule_ban(bot, chat_id: int, user_id: int, message_id: int):
    await asyncio.sleep(VERIFICATION_TIMEOUT)
    if user_id in pending_verifications:
        del pending_verifications[user_id]
        
        try:
            until_date = int(time.time()) + 60 
            await bot.ban_chat_member(chat_id=chat_id, user_id=user_id, until_date=until_date)
            logger.info(f"User {user_id} banned for failing verification.")
        except Exception as e:
            logger.error(f"Failed to ban user {user_id}: {e}")
        
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except TelegramBadRequest:
            pass


@router.callback_query(F.data.startswith("verify_user:"))
async def on_verify_callback(callback: CallbackQuery):
    user_id_to_verify = int(callback.data.split(":")[1])
    
    if callback.from_user.id != user_id_to_verify:
        await callback.answer("Эта кнопка не для вас!", show_alert=True)
        return

    if user_id_to_verify in pending_verifications:
        pending_info = pending_verifications.pop(user_id_to_verify)
        pending_info["task"].cancel()

        try:
            await callback.bot.delete_message(
                chat_id=pending_info["chat_id"], 
                message_id=pending_info["message_id"]
            )
        except TelegramBadRequest:
            pass

        await callback.answer("Вы верифицированы.", show_alert=True)
        await set_user_verified(user_id_to_verify)


@router.message(F.text)
async def check_message(message: Message):
    user_id = message.from_user.id

    if message.from_user.is_bot:
        return

    await add_user_if_not_exists(
        user_id, 
        message.from_user.username, 
        message.from_user.first_name
    )

    text = message.text.lower()

    found_keyword = next(
        (word for word in STOP_WORDS if word.lower() in text),
        None
    )

    if found_keyword:
        logger.warning(f"Suspicious message from {user_id}. Keyword: {found_keyword}")

        is_spam = await check_with_llm(message.text)

        if is_spam:
            username = f"@{message.from_user.username}" if message.from_user.username else str(user_id)
            
            spam_logger.warning(f"ID пользователя: {user_id} | Текст: {message.text}")

            if ACTION_MODE == "delete":
                try:
                    await message.delete()
                    
                    await message.bot.ban_chat_member(
                        chat_id=message.chat.id, 
                        user_id=user_id
                    )
                    await message.bot.unban_chat_member(
                        chat_id=message.chat.id, 
                        user_id=user_id, 
                        only_if_banned=True
                    )

                except Exception as e:
                    logger.error(f"Failed to remove spammer: {e}")
                return

            elif ACTION_MODE == "notify_admin":
                msg_link = message.link if message.link else f"https://t.me/c/{message.chat.id}/{message.message_id}"
                await message.answer(
                    f"@{ADMIN_USERNAME}, обнаружен спам от пользователя {username}: {msg_link}"
                )
                return
