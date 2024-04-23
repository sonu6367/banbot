from uvloop import install

install()
from telegram.error import BadRequest
from telegram import Chat, Update, ChatMember, ChatMemberUpdated, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, Defaults, CommandHandler, ChatMemberHandler, ContextTypes, MessageHandler, filters
from redis.asyncio.client import Redis
from redis.exceptions import RedisError

REDIS = Redis.from_url(
    "redis://default:ovBeAYcxUUUlfg0pyDXlo4oGtAvm79Rb@redis-15621.c301.ap-south-1-1.ec2.redns.redis-cloud.com:15621",
    decode_responses=True)


async def extract_status_change(chat_member_update: ChatMemberUpdated):
    status_change = chat_member_update.difference().get("status")
    if not status_change:
        return None
    old_is_member, new_is_member = chat_member_update.difference().get("is_member", (None, None))
    old_status, new_status = status_change
    return old_status in (
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR,
    ) or old_is_member, new_status in (
               ChatMember.MEMBER,
               ChatMember.OWNER,
               ChatMember.ADMINISTRATOR,
           ) or new_is_member


async def greetnimba(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, bot = update.effective_chat, context.bot
    if chat.type not in (Chat.CHANNEL, Chat.GROUP, Chat.SUPERGROUP):
        return
    if data := await extract_status_change(update.chat_member):
        was_member, is_member = data
        if not was_member and is_member:
            chat_id = chat.id
            newmem = update.chat_member.new_chat_member.user.id
            try:
                await bot.ban_chat_member(chat_id, newmem)
            except BadRequest:
                return
            if await REDIS.get(f"dounban_{chat_id}"):
                try:
                    await bot.unban_chat_member(chat_id, newmem, only_if_banned=True)
                except BadRequest:
                    return
    return


async def dounban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, bot = update.effective_chat, context.bot
    msg = update.effective_message
    if chat.type in (Chat.CHANNEL, Chat.GROUP, Chat.SUPERGROUP):
        await msg.reply_text("This command can only be used in PM.")
        return
    if msg.from_user.id not in (1594433798, 1092802988):
        return
    args = msg.text.split()[1:]
    if args:
        try:
            chat = await bot.get_chat(args[0])
            if chat.type not in (Chat.CHANNEL, Chat.GROUP, Chat.SUPERGROUP):
                await msg.reply_text("Chat type invalid!")
                return
            chat_id = chat.id
        except BadRequest:
            await msg.reply_text("Chat not found!")
            return
        try:
            opti = args[1].lower()
        except Exception:
            opti = ""
        if opti == "on":
            await REDIS.set(f"dounban_{chat_id}", 1)
            await msg.reply_text("Done!")
        elif opti == "off":
            await REDIS.delete(f"dounban_{chat_id}")
            await msg.reply_text("Deleted!")
        else:
            await msg.reply_text(f"Current setting: {bool(await REDIS.get(f'dounban_{chat_id}'))}")
    else:
        await msg.reply_text("Usage: /dounban chat_id on/off")
    return


async def getpjson(update: Update, _: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    msg = update.effective_message
    await msg.reply_text(f"Chat ID: {chat.id}")
    return


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    await msg.reply_text(
        "I'm alive!\nCmmands:\n- /dounban chat_id on/off\n- /id\n\n (Make sure to promote me before using me with the below buttons!)\n\nMade by @annihilatorrrr !",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    text="➕ Add me to a channel",
                    url=
                    f"https://t.me/{context.bot.username}?startchannel=new&admin=post_messages+delete_messages+edit_messages+change_info+invite_users",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="➕ Add me to a Group",
                    url=
                    f"https://t.me/{context.bot.username}?startgroup=new&admin=change_info+invite_users+restrict_members",
                ),
            ],
        ]))
    return


async def pinredis(app: Application):
    try:
        await REDIS.ping()
    except RedisError:
        exit("Redis is down!")
    application.add_handler(MessageHandler(
        filters.Regex(fr"^/id(@{app.bot.username})?(?: |$)(.*)"),
        getpjson,
        False,
    ), group=2)
    return


async def onclose(_: Application):
    await REDIS.aclose()
    return


builder = (Application.builder().token("6332448525:AAHjBfaEDraU3EO0b5PhK7RpqZAChyueNZc").defaults(Defaults(allow_sending_without_reply=True, block=False, do_quote=True)).concurrent_updates(True).post_init(pinredis).post_shutdown(onclose))
application = builder.build()


if __name__ == "__main__":
    application.add_handlers((
        CommandHandler("dounban", dounban, block=False),
        CommandHandler("start", start, block=False),
        ChatMemberHandler(greetnimba, ChatMemberHandler.CHAT_MEMBER, False),
    ))
    print("Started!")
    application.run_polling(
        poll_interval=0.1,
        allowed_updates=["channel_post", "message", "chat_member"],
        bootstrap_retries=3,
        drop_pending_updates=True,
    )
