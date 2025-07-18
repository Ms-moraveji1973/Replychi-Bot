import os
from telethon import TelegramClient,events
from database.session import get_db
from database.models import  TelegramUser , GroupMemberShipRelation ,ReplyRelationship
from sqlalchemy.future import select
from sqlalchemy import update
from dotenv import load_dotenv
import asyncio

load_dotenv()

'''proxy = {
    'proxy_type': 'socks5',
    'addr': '127.0.0.1',
    'port': 9052,
} '''
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
            return new_user
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



client = TelegramClient('bot', api_id, api_hash).start(bot_token=BOT_TOKEN)
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

                    # --- BEGIN: Logging the confirmed state after commit ---
                    # Refresh objects to get the latest data from the database
                    await session.refresh(user)  # Refreshes sender's TelegramUser
                    await session.refresh(replied_user)  # Refreshes replied-to's TelegramUser

                    # Determine which ReplyRelationship object to refresh (newly created or existing)
                    current_reply_relation = get_result_reply_relations if get_result_reply_relations else new_result_reply_relation
                    await session.refresh(current_reply_relation)  # Refreshes the ReplyRelationship

                    print("\n--- Reply Tracking Summary (Confirmed in DB) ---")
                    print(
                        f"  Replier: {user.first_name} (@{user.username if user.username else 'N/A'}) [ID: {user.id}]")
                    print(
                        f"  Replied To: {replied_user.first_name} (@{replied_user.username if replied_user.username else 'N/A'}) [ID: {replied_user.id}]")
                    print(f"  Group Chat ID: {user_group_id}")
                    print(f"  Replies from Replier to Replied-To in this group: {current_reply_relation.reply_count}")
                    print(f"  Total Replies SENT by {user.first_name}: {user.total_replies_sent}")
                    print(
                        f"  Total Replies RECEIVED by {replied_user.first_name}: {replied_user.total_replies_received}")
                    print("--------------------------------------------------\n")
                else:
                    print("------- This isn't Reply to Other Person ---------")
            else :
                print("-------- can not find reply ---------")

def main():
    print("Connecting to Telegram...")
    print("Client connected and running. Press Ctrl+C to stop.")
    client.run_until_disconnected()
    print("Client disconnected.")


if __name__ == '__main__':
    main()
