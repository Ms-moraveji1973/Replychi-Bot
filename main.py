import os
from telethon import TelegramClient,events
from database.session import get_db
from database.models import  TelegramUser , ReplyRelationship
from sqlalchemy.future import select
from sqlalchemy import update
from dotenv import load_dotenv
import asyncio

load_dotenv()

'''proxy = {
    'proxy_type': 'socks5',
    'addr': '127.0.0.1',
    'port': 9052,
}'''
api_id = os.getenv('api_id')
api_hash = os.getenv('api_hash')
BOT_TOKEN = os.getenv('BOT_TOKEN')
client = TelegramClient('bot', api_id, api_hash).start(bot_token=BOT_TOKEN)
@client.on(events.NewMessage())
async def main(event):
    try :
        sender = await event.get_sender()
       # print(f"------------------------------chat_id: {chat_id}---------------------")
        if sender:
            async with get_db() as session:
                result = await session.execute(select(TelegramUser).where(TelegramUser.id==sender.id ))
                user = result.scalars().first()
                if not user :
                    print('we have no user')
                    new_user = TelegramUser(
                        id=sender.id,
                        first_name=sender.first_name,
                        last_name=sender.last_name,
                        username=sender.username,
                        total_replies_received = 0,
                        total_replies_sent = 0,                    
                    )
                    session.add(new_user)
                    await session.commit()
                    await session.refresh(new_user)
                    user = new_user
                    print(f"New user created: {user.username or user.first_name} (ID: {user.id})")
                else :
                    print(f"Reply_Send:{user.total_replies_sent}")
                    print(f"Reply_Recive:{user.total_replies_received}")

        if event.is_reply:
            reply_message = await event.get_reply_message()
            if reply_message :
                reply_sender_id = sender.id
                reply_message_id = reply_message.sender_id
                if reply_sender_id != reply_message_id:
                    result_replied_to_user = await session.execute(select(TelegramUser).where(TelegramUser.id==reply_message_id
                                                                                              ))
                    replied_to_user = result_replied_to_user.scalars().first()
                    if not replied_to_user :
                        new_user = TelegramUser(
                            id=reply_message_id,
                            first_name=reply_message.sender.first_name,
                            last_name=reply_message.sender.last_name,
                            username=reply_message.sender.username,
                            total_replies_received=0,
                            total_replies_sent=0,
                        )
                        session.add(new_user)
                        await session.commit()
                        await session.refresh(new_user)
                        print('The reply_user has been created-----------------')

                    result_reply_relations = await session.execute(select(ReplyRelationship)
                                            .where(ReplyRelationship.replier_id == reply_sender_id ,
                                                    ReplyRelationship.replied_to_id == reply_message_id ))
                    get_result_reply_relations=result_reply_relations.scalars().first()
                    if not get_result_reply_relations :
                        new_result_reply_relation = ReplyRelationship(
                                replier_id=reply_sender_id,
                                replied_to_id=reply_message_id,
                                reply_count=1,
                            )
                        session.add(new_result_reply_relation)
                        print("New reply relationship created /")
                    else :
                        get_result_reply_relations.reply_count += 1
                        print(f"This Guys already has a reply and we're increasing this reply count : {get_result_reply_relations.reply_count}")



                    await session.execute(update(TelegramUser).where(TelegramUser.id==reply_sender_id).values(total_replies_sent=TelegramUser.total_replies_sent+1))
                    await session.execute(update(TelegramUser).where(TelegramUser.id==reply_message_id).values(total_replies_received=TelegramUser.total_replies_received+1))
                    await session.commit()

                    print("Reply counts updated successfully in DB.")


                    '''user_message_data = {'reply_message_id': reply_message_id,
                                         'reply_message_first_name': reply_message.sender.first_name,
                                        'reply_message_last_name': reply_message.sender.last_name ,
                                         'reply_message_username': reply_message.sender.username}
    
                    user_sender_data = {'reply_sender_id': reply_sender_id,
                                        'sender_first_name': sender.first_name,
                                        'sender_last_name': sender.last_name ,
                                        'sender_username': sender.username}
    
                    print(f"Reply Message Data: {user_message_data}")
                    print(f"Sender Message Data: {user_sender_data}")'''
                    print('Test')

                else:
                    print("This isn't reply to other person ")
            else :
                print("can not find reply")

    except Exception as e:
            print(f"An unexpected error occurred: {e}")

def main():
    print("Connecting to Telegram...")
    print("Client connected and running. Press Ctrl+C to stop.")
    client.run_until_disconnected()
    print("Client disconnected.")


if __name__ == '__main__':
    main()
