import os
import re
import requests
import random
import string
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

# ⭐ 動画が存在するかチェックする魔法の関数
def check_video_exists(video_id):
    # oEmbedという仕組みを使って、動画が存在するか確認するよ
    check_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}"
    response = requests.get(check_url)
    return response.status_code == 200

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if not data or 'webhook_event' not in data:
        return "No data", 400

    event = data['webhook_event']
    room_id = event['room_id']
    message_body = event['body']
    account_id = str(event['account_id'])

    if MY_ACCOUNT_ID and account_id == str(MY_ACCOUNT_ID):
        return "OK", 200
    if "動画IDガチャ" in message_body:
        return "OK", 200

    # ⭐【超進化】「暇！」で再抽選するルール
    if "暇！" in message_body:
        characters = string.ascii_letters + string.digits + "-_"
        found_id = None
        
        # 最大10回まで「当たり」を探して回す！
        for i in range(10):
            temp_id = ''.join(random.choice(characters) for _ in range(11))
            if check_video_exists(temp_id):
                found_id = temp_id
                break # 当たりが出たらループ終了！
        
        if found_id:
            msg = f"[info][title]🎰 動画IDガチャ (当たり！)[/title]ボットが再抽選して、実在する動画を見つけたよ！\nhttps://www.youtube.com/watch?v={found_id}[/info]"
        else:
            msg = f"[info][title]🎰 動画IDガチャ (ハズレ...)[/title]10回抽選したけど、実在する動画は見つからなかったよ。もう一回「暇！」って言ってみて！[/info]"
            
        send_chatwork_message(room_id, msg)
        return "OK", 200

    # --- 以下、通常のURL反応 ---
    yt_regex = r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|m\.youtube\.com/watch\?v=)([a-zA-Z0-9_-]+)'
    found_ids = re.findall(yt_regex, message_body)
    if found_ids:
        video_id = found_ids[0]
        fallback_url = f"https://www.youtube.com/watch?v={video_id}"
        msg = f"[info][title]📺 動画リンク[/title]{fallback_url}[/info]"
        send_chatwork_message(room_id, msg)

    return "OK", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
