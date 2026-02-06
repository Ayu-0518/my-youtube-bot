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
        # クッキーを読み込む設定（ファイル名が合っていれば有効になる）
        'cookiefile': 'youtube_cookies.txt',
        # 【重要】YouTubeの新しい制限を回避するための「招待状」
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

    if MY_ACCOUNT_ID and account_id == MY_ACCOUNT_ID:
        return "Ignore self message", 200

    # YouTube URLの抽出
    yt_regex = r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|m\.youtube\.com/watch\?v=)([a-zA-Z0-9_-]+)'
    found_ids = re.findall(yt_regex, message_body)

    if not found_ids:
        return "No URL found", 200

    video_id = found_ids[0]
    target_url = f"https://www.youtube.com/watch?v={video_id}"
    
    try:
        # まずは解析に挑戦！
        info = get_video_info(target_url)
        title = info.get('title', '動画')
        stream_url = info.get('url')
        msg = f"[info][title]🎬 解析成功: {title}[/title]{stream_url}[/info]"
    except Exception as e:
        # 解析に失敗しても、再生用URLを無理やり作って返す（これが最終兵器！）
        # このURLはブラウザで開けば、そのまま動画が再生できる特殊なリンクだよ
        fallback_url = f"https://www.youtube.com/embed/{video_id}"
        msg = f"[info][title]⚠️ 解析制限中[/title]YouTubeの制限で直接リンクが取得できませんでしたが、こちらで再生できるかも！\n{fallback_url}[/info]"
        
    send_chatwork_message(room_id, msg)
    return "OK", 200
