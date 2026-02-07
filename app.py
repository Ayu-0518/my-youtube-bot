import os
import re
import yt_dlp
import requests
import random  # ← 追加：ランダム機能を使うために必要
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
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'referer': 'https://www.google.com/',
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web', 'ios'],
                'skip': ['dash', 'hls']
            }
        },
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

    # --- 無限ループ防止ガード ---
    if MY_ACCOUNT_ID and account_id == str(MY_ACCOUNT_ID):
        return "OK", 200
    if "解析成功" in message_body or "解析制限中" in message_body or "世界の動画" in message_body:
        return "OK", 200

    # ⭐【新機能】「暇！」に反応するルール
    if "暇！" in message_body:
        # ランダムな検索ワード（ここを好きな言葉に変えてもOK！）
        keywords = ["sky", "travel", "cooking", "cat", "japan", "science", "piano", "funny", "vlog", "nature"]
        word = random.choice(keywords)
        
        # YouTubeの検索結果画面のURL（動画じゃなくて「検索結果」に飛ばすことで確実に動くよ！）
        search_url = f"https://www.youtube.com/results?search_query={word}"
        
        msg = f"[info][title]🌍 世界の動画ガチャ[/title]暇なんだね！じゃあ『{word}』で検索したこの結果から気になる動画を探してみて！\n{search_url}[/info]"
        send_chatwork_message(room_id, msg)
        return "OK", 200

    # --- YouTube URLの抽出 (通常の処理) ---
    yt_regex = r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|m\.youtube\.com/watch\?v=)([a-zA-Z0-9_-]+)'
    found_ids = re.findall(yt_regex, message_body)

    if not found_ids:
        return "No URL found", 200

    video_id = found_ids[0]
    target_url = f"https://www.youtube.com/watch?v={video_id}"
    
    try:
        info = get_video_info(target_url)
        title = info.get('title', '動画')
        stream_url = info.get('url')
        msg = f"[info][title]🎬 解析成功: {title}[/title]{stream_url}[/info]"
    except Exception as e:
        fallback_url = f"https://www.youtube.com/watch?v={video_id}"
        msg = f"[info][title]⚠️ 解析制限中[/title]直接リンクは取得できませんでしたが、こちらから再生できます！\n{fallback_url}[/info]"
        
    send_chatwork_message(room_id, msg)
    return "OK", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
