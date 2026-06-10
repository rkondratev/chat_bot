import asyncio
import logging
from aiogram import Router, F
from aiogram.types import ChatMemberUpdated, CallbackQuery
from aiogram.filters import ChatMemberUpdatedFilter
from aiogram.filters.chat_member_updated import IS_MEMBER, IS_NOT_MEMBER

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
    
    msg = getattr(event, 'message', None)
    thread_id = getattr(msg, 'message_thread_id', None) if msg else None

    if user.id in verified_users:
        return

    keyboard = get_verification_keyboard(user.id)
    mention = f"@{user.username}" if user.username else user.first_name
    text = f"{mention}, у вас 3 минуты, иначе вы будете аннигилированы."
    
    try:
        msg = await event.bot.send_message(
            chat_id=chat_id, text=text, reply_markup=keyboard, message_thread_id=thread_id
        )
    except Exception as e:
        logger.error(f"Failed to send verification message: {e}")
        return

    task = asyncio.create_task(schedule_ban(event.bot, chat_id, user.id, msg.message_id))
    pending_verifications[user.id] = {task: task, chat_id: chat_id, message_id: msg.message_id}

async def schedule_ban(bot, chat_id: int, user_id: int, message_id: int):
    pass

@router.callback_query(F.data.startswith("verify_user:"))
async def on_verify_callback(callback: CallbackQuery):
    pass
