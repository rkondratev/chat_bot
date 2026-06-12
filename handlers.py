import asyncio
import logging
import time

from aiogram import Router, F
from aiogram.types import ChatMemberUpdated, CallbackQuery
from aiogram.filters import ChatMemberUpdatedFilter
from aiogram.filters.chat_member_updated import IS_MEMBER, IS_NOT_MEMBER
from aiogram.exceptions import TelegramBadRequest

from config import VERIFICATION_TIMEOUT
from keyboards import get_verification_keyboard

router = Router()
logger = logging.getLogger(__name__)

pending_verifications = {}
verified_users = set()

@router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def on_user_join(event: ChatMemberUpdated):
    user = event.new_chat_member.user
    chat_id = event.chat.id
    
    msg_obj = getattr(event, 'message', None)
    thread_id = getattr(msg_obj, 'message_thread_id', None) if msg_obj else None

    if user.id in verified_users:
        return

    keyboard = get_verification_keyboard(user.id)
    mention = f"@{user.username}" if user.username else user.first_name
    text = f"{mention}, у вас есть 3 минуты для верификации, иначе вы будете аннигилированы."
    
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
            await callback.bot.delete_message(chat_id=pending_info["chat_id"], message_id=pending_info["message_id"])
        except TelegramBadRequest:
            pass

        await callback.answer("Вы верифицированы.", show_alert=True)
        verified_users.add(user_id_to_verify)
