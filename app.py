import os
import re
import yt_dlp
import requests
import random
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

def get_random_search_video(keyword):
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # 検索結果の1件目を取得
            result = ydl.extract_info(f"ytsearch1:{keyword}", download=False)
            if 'entries' in result and len(result['entries']) > 0:
                return result['entries'][0]
        except Exception as e:
            print(f"Search error: {e}")
        return None

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if not data or 'webhook_event' not in data:
        return "No data", 400

    event = data['webhook_event']
    room_id = event['room_id']
    message_body = event['body']
    account_id = str(event['account_id'])

    # --- 🔥 無限ループ防止ガード ---
    
    # ガード1: 自分のアカウントIDなら無視
    if MY_ACCOUNT_ID and account_id == str(MY_ACCOUNT_ID):
        return "OK", 200

    # ガード2: ボット自身の定型文が含まれていたら無視
    stop_words = ["ガチャ", "解析成功", "解析制限中", "動画リンク"]
    if any(word in message_body for word in stop_words):
        return "OK", 200

    # --- ⭐ 「暇！」ガチャ処理 ---
    if message_body == "暇！":
        hiragana = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん"
        search_word = "".join(random.sample(hiragana, k=3))
        
        video = get_random_search_video(search_word)
        
        if video:
            title = video.get('title', '不明な動画')
            video_url = f"https://www.youtube.com/watch?v={video['id']}"
            msg = f"[info][title]🎰 3文字検索ガチャ[/title]キーワード：『{search_word}』で見つけたよ！\n\n【{title}】\n{video_url}[/info]"
        else:
            msg = f"[info][title]🎰 3文字検索ガチャ[/title]『{search_word}』で見つからなかった...もう一回引いてみて！[/info]"

        send_chatwork_message(room_id, msg)
        return "OK", 200

    # --- 📺 通常のYouTube URL抽出処理 ---
    # ここが切れてた部分だよ！しっかり閉じました！
    yt_regex = r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|m\.youtube\.com/watch\?v=)([a-zA-Z0-9_-]+)'
    found_ids = re.findall(yt_regex, message_body)

    if found_ids:
        video_id = found_ids[0]
        fallback_url = f"https://www.youtube.com/watch?v={video_id}"
        msg = f"[info][title]📺 動画リンク[/title]どうぞ！\n{fallback_url}[/info]"
        send_chatwork_message(room_id, msg)

    return "OK", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
