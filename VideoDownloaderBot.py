import asyncio
from telethon import TelegramClient
import os
import re
import json

# Замените на ваши данные API
api_id = 0123456
api_hash = 'abcde1234567890123456789edcba'

# Имя файла для хранения последней скачанной ссылки
LAST_LINK_FILE = 'last_downloaded_link.txt'
# Имя файла для хранения информации о скачанных видео
DOWNLOADED_VIDEOS_INFO_FILE = 'downloaded_videos_info.json'
# Имя папки для сохранения видео
VIDEOS_FOLDER = 'videos'

async def download_videos_from_channel():
    client = TelegramClient('session_name', api_id, api_hash)
    await client.connect()

    if not await client.is_user_authorized():
        phone_number = input("Введите свой номер телефона (например, +77012345678): ")
        await client.send_code_request(phone_number)
        code = input('Введите код из Telegram: ')
        await client.sign_in(phone_number, code)

    channel_link = input("Введите ссылку на Telegram-канал (например, https://t.me/название_канала): ")
    start_num_str = input("Введите начальный номер сообщения для скачивания: ")
    end_num_str = input("Введите конечный номер сообщения для скачивания: ")

    channel_username = None
    if channel_link.startswith('https://t.me/'):
        channel_username = channel_link[len('https://t.me/'):]
    elif channel_link.startswith('t.me/'):
        channel_username = channel_link[len('t.me/'):]
    elif not channel_link.startswith('@'):
        channel_username = channel_link  # Попробуем как имя пользователя, если не ссылка

    if not channel_username:
        print("Некорректная ссылка на канал.")
        return

    try:
        start_message_id = int(start_num_str)
        end_message_id = int(end_num_str)
    except ValueError:
        print("Некорректный формат номера сообщения.")
        return

    # Проверяем и создаем папку для видео, если ее нет
    if not os.path.exists(VIDEOS_FOLDER):
        os.makedirs(VIDEOS_FOLDER)
        print(f"Создана папка для сохранения видео: {VIDEOS_FOLDER}")
    else:
        print(f"Видео будут сохранены в папку: {VIDEOS_FOLDER}")

    last_downloaded_message_id = start_message_id
    if os.path.exists(LAST_LINK_FILE):
        with open(LAST_LINK_FILE, 'r') as f:
            last_link = f.readline().strip()
            match = re.search(r'/(\d+)$', last_link)
            if match:
                last_downloaded_message_id = int(match.group(1)) + 1
                print(f"Продолжаем скачивание с сообщения №{last_downloaded_message_id}")
            else:
                print("Некорректный формат ссылки в файле.")
                last_downloaded_message_id = start_message_id
    else:
        print(f"Начинаем скачивание с сообщения №{start_message_id}")

    downloaded_videos_info = []
    if os.path.exists(DOWNLOADED_VIDEOS_INFO_FILE):
        with open(DOWNLOADED_VIDEOS_INFO_FILE, 'r') as f:
            try:
                downloaded_videos_info = json.load(f)
            except json.JSONDecodeError:
                print("Ошибка при чтении файла с информацией о скачанных видео. Файл будет перезаписан.")

    total_downloaded_size = 0
    videos_downloaded_count = 0
    limit_reached = False

    for message_id in range(last_downloaded_message_id, end_message_id + 1):
        if total_downloaded_size >= 10 * 1024 * 1024 * 1024:
            print("Достигнут дневной лимит скачивания (10 Гб).")
            limit_reached = True
            break

        message_link = f"{channel_link.rsplit('/', 1)[0]}/{message_id}"
        try:
            entity = await client.get_entity(channel_username)
            message = await client.get_messages(entity, ids=message_id)

            if message and message.media:
                if hasattr(message.media,
                           'document') and message.media.document and message.media.document.mime_type.startswith(
                        'video'):
                    print(f"Скачиваю видео из сообщения №{message_id} ({message_link})...")
                    file_name = f'{VIDEOS_FOLDER}/{channel_username}_{message_id}.mp4'  # Сохраняем в папку videos
                    download_result = await client.download_media(message.media, file=file_name)
                    if download_result:
                        file_path = os.path.abspath(download_result)  # Получаем абсолютный путь
                        file_size = os.path.getsize(file_path)
                        total_downloaded_size += file_size
                        videos_downloaded_count += 1
                        print(f"Видео сохранено в: {file_path} ({file_size / (1024 * 1024):.2f} Мб)")

                        downloaded_videos_info.append({"file_name": os.path.basename(file_path), "link": message_link})
                        with open(LAST_LINK_FILE, 'w') as f:
                            f.write(message_link + '\n')
                    else:
                        print(f"Не удалось скачать видео из сообщения №{message_id}.")
                elif hasattr(message.media, 'photo'):
                    print(f"В сообщении №{message_id} найдено фото, пропускаем.")
                else:
                    print(f"В сообщении №{message_id} нет видео, пропускаем.")
            else:
                print(f"Сообщение №{message_id} не содержит медиафайлов.")

            await asyncio.sleep(1) # Небольшая задержка
        except Exception as e:
            print(f"Произошла ошибка при обработке сообщения №{message_id}: {e}")
            await asyncio.sleep(5) # Большая задержка в случае ошибки

    await client.disconnect()

    with open(DOWNLOADED_VIDEOS_INFO_FILE, 'w') as f:
        json.dump(downloaded_videos_info, f, indent=4, ensure_ascii=False)
        print(f"Информация о скачанных видео сохранена в {DOWNLOADED_VIDEOS_INFO_FILE}")

    if limit_reached:
        print(f"Скачано {videos_downloaded_count} видео.")
        print("Скачивание прервано из-за достижения дневного лимита.")
    else:
        print(f"Скачано {videos_downloaded_count} видео из диапазона {start_message_id}-{end_message_id}.")
        print("Скачивание завершено.")

if __name__ == '__main__':
    asyncio.run(download_videos_from_channel())
