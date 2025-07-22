import os
from telethon import TelegramClient,events , Button
from database.session import get_db
from database.models import  TelegramUser , GroupMemberShipRelation ,ReplyRelationship
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import update
from dotenv import load_dotenv
import re
import asyncio

load_dotenv()

proxy = {
    'proxy_type': 'socks5',
    'addr': 'host.docker.internal',
    'port': 9052,
}


api_id = os.getenv('api_id')
api_hash = os.getenv('api_hash')
BOT_TOKEN = os.getenv('BOT_TOKEN')


async def create_or_get_user(session,user_info):
        result = await session.execute(select(TelegramUser).where(TelegramUser.id == user_info.id))
        user = result.scalars().first()
        if not user:
            print('------- We Have No User! -------')
            new_user = TelegramUser(
                id=user_info.id,
                first_name=user_info.first_name,
                last_name=user_info.last_name,
                username=user_info.username,
                total_replies_received=0,
                total_replies_sent=0,
            )
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            print(f"--------- New user created: {new_user.username or new_user.first_name} (ID: {new_user.id}) --------")
            user = new_user
            return user
        else:
            print(f"Reply_Send:{user.total_replies_sent}")
            print(f"Reply_Recive:{user.total_replies_received}")
            return user

async def create_or_get_group(session,group_id,sender_id):
    result = await session.execute(select(GroupMemberShipRelation).where(GroupMemberShipRelation.group_id == group_id,
                                                                         GroupMemberShipRelation.user_id == sender_id))
    user_group_relation = result.scalars().first()
    if not user_group_relation:
        new_user_group_relation = GroupMemberShipRelation(
            group_id=group_id,
            user_id=sender_id,
        )
        session.add(new_user_group_relation)
        await session.commit()
        await session.refresh(new_user_group_relation)
        return new_user_group_relation
    else :
        return user_group_relation



client = TelegramClient('bot', api_id, api_hash,proxy=proxy).start(bot_token=BOT_TOKEN)
@client.on(events.NewMessage())
async def new_message(event):
    sender_user = await event.get_sender()
    if not sender_user :
        print('-------- The User Not Find --------')
        return
    user_group_id = event.chat_id
    async with get_db() as session:

        # check user status in database
        user = await create_or_get_user(session,sender_user)

        # check reply in database
        replier_group = await create_or_get_group(session,user_group_id,user.id)

        if event.is_reply:
            reply_message = await event.get_reply_message()
            # ensure reply message exist
            if reply_message :
                replier_id = user.id
                replied_id = reply_message.sender_id

                if replier_id != replied_id:
                    # check replied_user in database
                    replied_user = await create_or_get_user(session,reply_message.sender)
                    # check replied group status
                    replied_group = await create_or_get_group(session,user_group_id,replied_user.id)

                    result_reply_relations = await session.execute(select(ReplyRelationship)
                                            .where(ReplyRelationship.replier_id == replier_group.id ,
                                                    ReplyRelationship.replied_to_id == replied_group.id ))

                    get_result_reply_relations = result_reply_relations.scalars().first()
                    if not get_result_reply_relations :
                        new_result_reply_relation = ReplyRelationship(
                                replier_id=replier_group.id,
                                replied_to_id=replied_group.id,
                                reply_count=1,
                            )
                        session.add(new_result_reply_relation)
                        print("--------- New reply relationship created --------")
                    else :
                        get_result_reply_relations.reply_count += 1
                        print(f"-------- This Guys already has a reply and we're increasing this reply count : {get_result_reply_relations.reply_count} -------------")


                    # update total reply for each user
                    await session.execute(update(TelegramUser).where(TelegramUser.id==replier_id).values(total_replies_sent=TelegramUser.total_replies_sent+1))
                    await session.execute(update(TelegramUser).where(TelegramUser.id==replied_user.id).values(total_replies_received=TelegramUser.total_replies_received+1))
                    await session.commit()

                    await session.refresh(user)  # Refreshes sender's TelegramUser
                    await session.refresh(replied_user)  # Refreshes replied-to's TelegramUser

                    current_reply_relation = get_result_reply_relations if get_result_reply_relations else new_result_reply_relation
                    await session.refresh(current_reply_relation)

                    print("\n--- Reply Tracking Summary (Confirmed in DB) ---")
                    print(
                        f"  Replier: {user.first_name} (@{user.username if user.username else 'N/A'}) [ID: {user.id}]")
                    print(
                        f"  Replied To: {replied_user.first_name} (@{replied_user.username if replied_user.username else 'N/A'}) [ID: {replied_user.id}]")
                    print(f"  Group Chat ID: {user_group_id}")
                    print(f"  Replies from Replier to Replied-To in this group: {current_reply_relation.reply_count}")
                    print(f"  Total Replies SENT by {user.first_name}@{user.username}: {user.total_replies_sent}")
                    print(
                        f"  Total Replies RECEIVED by {replied_user.first_name}: {replied_user.total_replies_received}")
                    print("--------------------------------------------------\n")
                else:
                    print("------- This isn't Reply to Other Person ---------")
            else :
                print("-------- can not find reply ---------")

# communicate user  with bot

main_menu_buttons = [
    [Button.inline('📘 راهنما!', b'guide'), Button.inline('👤 اطلاعات من', b'information')],
    [Button.inline('👥 گروه‌هام', b'groups'), Button.inline('🔍 جستجوی کاربر در گروه', b'search_user_in_group')],
]

async def get_guide():
    guide_message = (
        "📘 **راهنمای ربات**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "سلام! این ربات برای این ساخته شده که آمار دقیق و مفیدی از فعالیت‌هات توی گروه‌ها بهت بده.\n"
        "اینجا می‌تونی ببینی به چه کسانی ریپلای دادی، از کی‌ها جواب گرفتی و حتی فعالیت بقیه رو هم بررسی کنی.\n\n"

        "🔧 **قابلیت‌های ربات:**\n"
        "1️⃣ نمایش ریپلای‌هایی که دادی و گرفتی، با تعداد و جزئیات.\n"
        "2️⃣ مشاهده اطلاعات کاربری خودت، مثل اسم و یوزرنیم.\n"
        "3️⃣ لیست گروه‌هایی که توشون عضو هستی و من هم حضور دارم.\n"
        "4️⃣ جستجوی یوزرنیم دیگران برای دیدن آمارشون توی گروه‌های مشترک.\n\n"

        "🟢 **چطور استفاده کنم؟**\n"
        "کافیه از دکمه‌های پایین استفاده کنی و گزینه مورد نظرت رو انتخاب کنی.\n"
        "همه چیز ساده و قابل دسترس طراحی شده، فقط امتحانش کن.\n\n"

        "🎛️ **توضیح دکمه‌ها:**\n"
        "🔍 **جستجوی کاربر در گروه:**\n"
        "اگر با کسی توی یک گروه مشترک باشی، می‌تونی ببینی اون یوزر به کی ریپلای زده، چند بار زده، و اصلاً چقدر فعاله.\n"
        "همچنین می‌تونی ببینی کی بیشتر از بقیه بهش ریپلای داده.\n\n"

        "👥 **گروه های من:**\n"
        "لیست گروه‌هایی که هم تو عضو هستی هم من. از اونجا می‌تونی گروه رو انتخاب کنی و بری سراغ آمارش.\n\n"

        "👤 **اطلاعات من:**\n"
        "نمایش اطلاعات پایه مثل اسم، یوزرنیم و ... (قراره به زودی این بخش هم اپدیت باحالی بشه منتظر باشید 😎).\n\n"

        "📘 **راهنما:**\n"
        "همین متنی که الان داری می‌خونی 😄 هر وقت گم شدی، برگرد اینجا.\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━\n"
    )
    return guide_message



@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    if not event.is_private:
        return
    sender_user_to_bot = await event.get_sender()
    async with get_db() as session:
        user_bot = await create_or_get_user(session,sender_user_to_bot)
    user_db_username = user_bot.username
    giude_message = await get_guide()
    print(f"---------- username :{user_db_username}")
    buttons = main_menu_buttons
    await event.respond(giude_message,buttons=buttons)

@client.on(events.CallbackQuery(pattern=b'guide'))
async def handler_gu(event):
    if not event.is_private:
        return
    guide = await get_guide()
    await event.edit(guide,buttons=main_menu_buttons)

@client.on(events.NewMessage(pattern='/guide'))
async def handler_gui(event):
    if not event.is_private:
        return
    guide = await get_guide()
    await event.respond(guide,buttons=main_menu_buttons)


@client.on(events.CallbackQuery(pattern=b'information'))
async def handler_inf(event):
    if not event.is_private:
        return
    user = await event.get_sender()
    await event.respond(f'اسم شما: {user.first_name}\nیوزرنیم: @{user.username}', buttons=main_menu_buttons)



@client.on(events.CallbackQuery(pattern=b'groups'))
async def show_user_groups(event):
    if not event.is_private:
        return
    async with get_db() as session:
        sender_user_to_bot = await event.get_sender()
        user_bot = await create_or_get_user(session, sender_user_to_bot)
        user_groups = await session.execute(select(GroupMemberShipRelation.group_id).where(GroupMemberShipRelation.user_id == user_bot.id))

        group_ids = list(set(g_id for g_id in user_groups.scalars().all()))

        if len(group_ids) <= 1:
            await event.respond("هنوز تو هیچ گروه مشترکی با من عضو نیستی.\n✔️ مطمئن شو که من داخل گروه هستم، دسترسی پیام دارم و بعد از شروع ربات یه پیام داخل گروه فرستادی.")

        buttons = [
            [Button.inline(f"📍 {getattr(await client.get_entity(group_id), 'title', f'گروه {group_id}')}",
                           f"groupinfo_{group_id}".encode())]
            for group_id in group_ids
        ]
        await event.respond("یکی از گروه‌ها رو انتخاب کن:", buttons=buttons)

@client.on(events.CallbackQuery(pattern=b'groupinfo_'))
async def group_info(event):
    if not event.is_private:
        return
    user_to_bot = await event.get_sender()
    user_data_to_bot = event.data.decode('utf-8')
    print(user_data_to_bot)
    group_id = int(user_data_to_bot.split('_')[1])

    async with get_db() as session:
        result = await session.execute(
            select(GroupMemberShipRelation).options(

                # load replier data
                selectinload(GroupMemberShipRelation.sent_replies_through_membership)
                .selectinload(ReplyRelationship.replied_user)
                .selectinload(GroupMemberShipRelation.user),

                # load replied data
                selectinload(GroupMemberShipRelation.receive_replies_through_membership)
                .selectinload(ReplyRelationship.replier_user)
                .selectinload(GroupMemberShipRelation.user)
            ).where(
                GroupMemberShipRelation.group_id == group_id,
                GroupMemberShipRelation.user_id == user_to_bot.id
            )
        )
        get_group_user = result.scalar_one_or_none()
        print(f"--------------- > get_group_user ----------------> : {get_group_user}")

        if not get_group_user:
            await event.respond("اطلاعاتی یافت نشد.(:")
            return

        message = await group_reply_list(get_group_user)

        await event.respond(message)


@client.on(events.CallbackQuery(pattern=b'search_user_in_group'))
async def search_username(event):
    if not event.is_private:
        return
    await event.respond('یوزرنیم یا آیدی کاربری رو که میخوای رو بفرست رفیق')


@client.on(events.NewMessage(pattern=r'^@\w+'))
async def get_username(event):
    if not event.is_private:
        return
    sender_user_to_bot = await event.get_sender()
    username = event.raw_text.strip().lstrip('@')
    await event.respond('آیدی دریافت شد | در حال پردازشیم')
    async with get_db() as session:
        result = await session.execute(select(TelegramUser).where(TelegramUser.username == username))
        get_user_db = result.scalars().first()

        if get_user_db:
            print(f"----------------- user founded -------> : {get_user_db}")
            print(f"--------- About This User : {get_user_db.first_name} , {get_user_db.id},{get_user_db.username}")
            user_groups = await session.execute(select(GroupMemberShipRelation.group_id).where(GroupMemberShipRelation.user_id == get_user_db.id))
            user_group_ids = set(user_groups.scalars().all())
            sender_groups = await session.execute(select(GroupMemberShipRelation.group_id).where(GroupMemberShipRelation.user_id == sender_user_to_bot.id))
            sender_group_ids = set(sender_groups.scalars().all())


            group_ids = list(user_group_ids & sender_group_ids)

            print(f"--------------------- group {group_ids}")
            if not group_ids or not user_group_ids :
                await event.respond('هیچ گروه مشترکی ندارید رفیق | حیف ):')
                return

            buttons = []
            for group_id in group_ids:
                group_entity = await client.get_entity(group_id)
                group_title = getattr(group_entity, "title", f"گروه {group_id}")
                buttons.append(
                    [Button.inline(f"📍 {group_title}", f"find_user_group_{group_id}_{get_user_db.id}".encode())])

            print(f"button {buttons}")
            await event.respond("یکی از گروه‌ها رو انتخاب کن(گروه های مشترک شما و آیدی مورد نظر)  :", buttons=buttons)
        else :
            await event.respond('هیچ گروه مشترکی ندارید رفیق | حیف ):')
            return

@client.on(events.CallbackQuery(pattern=re.compile(b'^find_user_group_')))
async def find_user_group(event):
    if not event.is_private:
        return
    user_data_to_bot = event.data.decode('utf-8')
    print(f"--------------- > user_data_to_bot : {user_data_to_bot}")
    parts = user_data_to_bot.split('_')
    print(len(parts), '----------------- len parts')
    group_id = int(parts[3])
    user_id = int(parts[4])
    print(f"--------------- > group_id : {group_id}")
    print(f"--------------- > user_id : {user_id}")


    async with get_db() as session:
        result = await session.execute(
            select(GroupMemberShipRelation).options(

                # load replier data
                selectinload(GroupMemberShipRelation.sent_replies_through_membership)
                .selectinload(ReplyRelationship.replied_user)
                .selectinload(GroupMemberShipRelation.user),

                # load replied data
                selectinload(GroupMemberShipRelation.receive_replies_through_membership)
                .selectinload(ReplyRelationship.replier_user)
                .selectinload(GroupMemberShipRelation.user)
            ).where(
                GroupMemberShipRelation.group_id == group_id,
                GroupMemberShipRelation.user_id == user_id
            )
        )
        get_group_user = result.scalar_one_or_none()
        print(f"--------------- > get_group_user ----------------> : {get_group_user}")

        if not get_group_user:
            await event.respond("اطلاعاتی یافت نشد.(:")
            return

        message = await user_group_reply(get_group_user)

        await event.respond(message)


async def user_group_reply(get_group_user):
    text = "📊 ریپلای‌هایی که کاربری که وارد کرده اید در گروه زده است:\n\n"
    sent_replies = get_group_user.sent_replies_through_membership
    if not sent_replies:
        text += "📭 هیچ ریپلایی در این گروه ثبت نشده."

    for i, reply in enumerate(sent_replies, start=1):
        receiver_user = reply.replied_user.user
        username = receiver_user.username or 'یوزرنیم نداره مگه میشه ×-×'
        name = receiver_user.first_name or 'نام نداره '
        count = reply.reply_count
        text += f"{i}. {name} ({username}) - {count} بار\n"

    text += "\n" + "=" * 20 + "\n\n"
    receive_replies = get_group_user.receive_replies_through_membership
    text += "📥 **ریپلای‌هایی که یوزری که وارد کرده اید  دریافت کرده است:**\n\n"
    if not receive_replies:
        text += " موردی یافت نشد.\n"

    for i, reply in enumerate(receive_replies, start=1):
        receiver_user = reply.replier_user.user
        username = receiver_user.username or 'یوزرنیم نداره مگه میشه ×-×'
        name = receiver_user.first_name or 'نام نداره دهن سرویس'
        count = reply.reply_count
        text += f"{i}. {name} ({username}) - {count} بار\n"

    return text


async def group_reply_list(get_group_user):
    text = "📊 ریپلای‌هایی که شما در گروه زده اید:\n\n"
    sent_replies = get_group_user.sent_replies_through_membership
    if not sent_replies:
        text += "📭 هیچ ریپلایی در این گروه ثبت نشده."

    for i, reply in enumerate(sent_replies, start=1):
        receiver_user = reply.replied_user.user
        username = receiver_user.username or 'یوزرنیم نداره مگه میشه ×-×'
        name = receiver_user.first_name or 'نام نداره '
        count = reply.reply_count
        text += f"{i}. {name} ({username}) - {count} بار\n"

    text += "\n" + "="*20 + "\n\n"
    receive_replies = get_group_user.receive_replies_through_membership
    text += "📥 **ریپلای‌هایی که شما دریافت کردید:**\n\n"
    if not receive_replies:
        text += " موردی یافت نشد.\n"

    for i, reply in enumerate(receive_replies, start=1):
        receiver_user = reply.replier_user.user
        username = receiver_user.username or 'یوزرنیم نداره مگه میشه ×-×'
        name = receiver_user.first_name or 'نام نداره دهن سرویس'
        count = reply.reply_count
        text += f"{i}. {name} ({username}) - {count} بار\n"

    return text

known_patterns = [
    '/start',
    '/guide',
    '/information',
    '/groups',
    '/search_user_in_group'
]

@client.on(events.NewMessage())
async def default_message_handler(event):
    if not event.is_private:
        return
    text = event.raw_text.strip()
    if any(text.startswith(pattern) for pattern in known_patterns):
        return

    if re.match(r'^@\w+', text):
        return

    if not event.out and not event.mentioned:
        await event.respond("❓ متوجه منظورت نشدم!\nبرای راهنما دستور /guide رو بفرست.")



def main():
    print("Connecting to Telegram...")
    print("Client connected and running. Press Ctrl+C to stop.")
    client.run_until_disconnected()
    print("Client disconnected.")


if __name__ == '__main__':
    main()
