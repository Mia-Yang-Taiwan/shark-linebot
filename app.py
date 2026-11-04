import os
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from google import genai
from google.genai import types

app = Flask(__name__)

# 讀取環境變數
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# 鯊鯊助理 / Mia 專屬秘書系統提示詞
SYSTEM_PROMPT = """
# Role: Mia 專屬減壓排程教練

## Profile
你是一位溫柔、同理心極強且懂時間調度的「減壓排程教練」。你的目標是幫助事情太多、時間不夠用的高負載使用者（同時有學校課程、打工、英文課/考雅思、專題、運動等）進行壓力管理與排程規劃。你不會給使用者教訓或帶來壓力，而是扮演隨時聽吐苦水、並提供「留白與防爆排程」的後盾。

## Core Guiding Principles (核心原則)
1. **先同理，後建議**：當使用者表達累、焦慮或事情塞爆時，先給予高同理心的安慰（例：「拍拍你 💜」、「今天真的辛苦了 ☕」）。
2. **主動提議減壓調度**：主動建議將彈性任務移轉或刪減，預留 1~2 小時緩衝時間。
3. **語氣與 Emoji 規範**：語氣溫柔、鼓勵，常用指定表情符號 (🦈, ☕, 🌿, ✨)。
"""

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check channel access token/channel secret.")
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_text = event.message.text

    try:
        # 呼叫 Gemini 產生同理與排程建議
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_text,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7,
            )
        )
        reply_text = response.text

    except Exception as e:
        app.logger.error(f"Gemini API Error: {e}")
        reply_text = " MIA私人助理目前連線稍微有點卡住，請稍等我一下下再試一次喔！🌿"

    # 回覆訊息給 LINE 使用者
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
