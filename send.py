from telethon import TelegramClient
import asyncio
from telethon import events
# Use your own values from my.telegram.org
api_id = 25551282
api_hash = 'f6c4886ab837f67a23df996090001058'

proxy = {
    'proxy_type': 'socks5',
    'addr': '127.0.0.1',
    'port': 9150,
}
client = TelegramClient('anon', api_id, api_hash, proxy=proxy)
@client.on(events.NewMessage())
async def reply(event):
    is_reply = False
    if event.is_reply:
        reply_message = await event.get_reply_message()
        reply_sender = await  event.get_sender()
        if reply_message :
            reply_sender_id = reply_sender.id
            reply_message_id = reply_message.sender_id
            if reply_sender_id != reply_message_id:
                is_reply = True
                user_message_data = {'reply_message_id': reply_message_id,
                                     'reply_message_first_name': reply_message.sender.first_name,
                                    'reply_message_last_name': reply_message.sender.last_name ,
                                     'reply_message_username': reply_message.sender.username}

                user_sender_data = {'reply_message_id': reply_sender_id,
                                    'reply_sender_first_name': reply_sender.first_name,
                                    'reply_sender_last_name': reply_sender.last_name ,
                                    'reply_sender_username': reply_sender.username}

                print(f"Reply Message Data: {user_message_data}")
                print(f"Sender Message Data: {user_sender_data}")

            else:
                print("This isn't reply to other person ")
        else :
            print("can not find reply")


async def main():
    print("Connecting to Telegram...")
    await client.start()
    print("Client connected and running. Press Ctrl+C to stop.")

    await client.run_until_disconnected()
    print("Client disconnected.")


if __name__ == '__main__':
    asyncio.run(main())

