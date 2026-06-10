from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_verification_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подтвердить человечность", callback_data=f"verify_user:{user_id}")]
    ])
