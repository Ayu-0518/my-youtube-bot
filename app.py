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
    try:
        requests.post(url, headers=headers, data=payload, timeout=10)
    except Exception as e:
        print(f"Message send error: {e}")

def get_video_info(youtube_url):
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'no_color': True,
        'cookiefile': 'youtube_cookies.txt',
        'youtube_include_dash_manifest': False,
        'extractor_args': {
            'youtube': {
                'player_client': ['web', 'mweb'],
                'skip': ['dash', 'hls']
            }
        },
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
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

    # --- 無限ループ防止ガード 1: アカウントIDで判定 ---
    if MY_ACCOUNT_ID and account_id == str(MY_ACCOUNT_ID):
        print("Ignore: Message from self")
        return "OK", 200

    # --- 無限ループ防止ガード 2: メッセージ内容で判定 ---
    # 自分が送る返信定型文が含まれていたら即座に終了
    if "解析成功" in message_body or "解析制限中" in message_body:
        print("Ignore: Bot's own response pattern")
        return "OK", 200

    # YouTube URLの抽出 (ID部分をキャプチャ)
    yt_regex = r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|m\.youtube\.com/watch\?v=)([a-zA-Z0-9_-]+)'
    found_ids = re.findall(yt_regex, message_body)

    if not found_ids:
        return "No URL found", 200

    # 重複反応を防ぐため、最初のURLだけ処理
    video_id = found_ids[0]
    target_url = f"https://www.youtube.com/watch?v={video_id}"
    
    try:
        # 解析に挑戦
        info = get_video_info(target_url)
        title = info.get('title', '動画')
        stream_url = info.get('url')
        msg = f"[info][title]🎬 解析成功: {title}[/title]{stream_url}[/info]"
    except Exception as e:
        # 解析エラー時は通常のURLを返す
        fallback_url = f"https://www.youtube.com/watch?v={video_id}"
        msg = f"[info][title]⚠️ 解析制限中[/title]直接リンクは取得できませんでしたが、こちらから再生できます！\n{fallback_url}[/info]"
        
    send_chatwork_message(room_id, msg)
    return "OK", 200

# Render用の起動設定
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
