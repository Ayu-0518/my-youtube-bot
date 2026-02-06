import os
import re
import yt_dlp
import requests
from flask import Flask, request

app = Flask(__name__)

# --- 環境変数から設定を読み込む ---
CHATWORK_TOKEN = os.environ.get('CHATWORK_TOKEN')
MY_ACCOUNT_ID = os.environ.get('MY_ACCOUNT_ID') 

def send_chatwork_message(room_id, text):
    url = f"https://api.chatwork.com/v2/rooms/{room_id}/messages"
    headers = {"X-ChatWorkToken": CHATWORK_TOKEN}
    payload = {"body": text}
    requests.post(url, headers=headers, data=payload)

def get_video_info(youtube_url):
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'no_color': True,
        'cookiefile': 'youtube_cookies.txt', # アップロードしたファイル名
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(youtube_url, download=False)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if not data or 'webhook_event' not in data:
        return "No data", 400

    event = data['webhook_event']
    room_id = event['room_id']
    message_body = event['body']
    account_id = str(event['account_id'])

    # ボット自身の発言なら無視
    if MY_ACCOUNT_ID and account_id == MY_ACCOUNT_ID:
        return "Ignore self message", 200

    # YouTube URLの抽出
    yt_regex = r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|m\.youtube\.com/watch\?v=)[a-zA-Z0-9_-]+'
    found_urls = re.findall(yt_regex, message_body)

    if not found_urls:
        return "No URL found", 200

    target_url = found_urls[0]
    
    try:
        info = get_video_info(target_url)
        title = info.get('title', 'タイトル不明')
        stream_url = info.get('url')

        if stream_url:
            response_msg = (
                f"[info][title]🎬 解析完了: {title}[/title]"
                f"以下のURLでストリーミング再生できます！\n\n"
                f"{stream_url}[/info]"
            )
        else:
            raise Exception("ストリーミングURLが見つかりませんでした。")
            
        send_chatwork_message(room_id, response_msg)

    except Exception as e:
        error_msg = f"[info][title]⚠️ 解析エラー[/title]動画の解析に失敗しました。\n内容: {str(e)}[/info]"
        send_chatwork_message(room_id, error_msg)

    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
