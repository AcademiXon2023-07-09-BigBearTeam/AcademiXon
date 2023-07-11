import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import re
import requests
import openai
import numpy as np

SLACK_BOT_TOKEN = "token"
SLACK_APP_TOKEN = "token"
openai.api_key = "api key"

import tempfile, os
from google.cloud import texttospeech

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "api key"
client = texttospeech.TextToSpeechClient()

from slack_sdk import WebClient
bot = WebClient(SLACK_BOT_TOKEN)
auth_test = bot.auth_test()
bot_user_id = auth_test["user_id"]
print(f"App's bot user: {bot_user_id}")

#声の設定
voice = texttospeech.VoiceSelectionParams(
    name="ja-JP-Wavenet-A",
    language_code="ja-JP",
    ssml_gender=texttospeech.SsmlVoiceGender.MALE
)

#生成する音声ファイルのエンコード方式
audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.LINEAR16
)

def completion(new_message_text:str):

    character_settings = f"""
    あなたは大熊という名前の、テクノロジーに精通していて、会話中に頻繁に「すね」や「んすよ」という独特の終助詞を用い、また話し始めるときには「えっとそうっすね」や「えっとなんだろう」という口癖を頻繁に使う人物です。
    ただし語尾に入れた結果あまりに不自然になる場合は入れないでください．
    あなたは敬意を持って相手に接しながらも、カジュアルな表現を使うことがあります．
    程度の表現に関しては割とやそこそこを多用します．
    一人称は必ず僕です．
    この条件のもとで私の入力に対して大熊さんになりきって自然な日本語でチャットを返してくれますか？
    返す言葉は必ず100字以内の短いものにしてください
    ではシミュレーションを開始します。
    ###
    text: {new_message_text}
    """
    new_message = [
        {"role": "assistant", "content": character_settings},
    ]

    result = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=new_message
    )
    response_message_text = result.choices[0].message.content
    return response_message_text

def upload_file(file_path):
    url = "https://slack.com/api/files.upload"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
    }

    files = {
        "file": open(file_path, "rb"),
    }

    response = requests.post(url, headers=headers, files=files)
    response_data = response.json()
    if response_data["ok"]:
        return response_data["file"]["url_private"]
    else:
        return None

from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips

app = App(token=SLACK_BOT_TOKEN)
@app.event("app_mention")  # chatbotにメンションが付けられたときのハンドラ
def respond_to_mention(event, say):
    say("考え中...")
    message = re.sub(r'^<.*>', '', event['text'])
    message = completion(message)
    synthesis_input = texttospeech.SynthesisInput(text=message)

    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    # 音声ファイル
    with open("../assets/output.wav", "wb") as f:
        f.write(response.audio_content)

    video_file = "../assets/video.mp4"
    audio_file = "../assets/output.wav"

    video_clip = VideoFileClip(video_file)
    audio_clip = AudioFileClip(audio_file)
    audio_duration = audio_clip.duration
    looped_video_clips = concatenate_videoclips([video_clip] * int(audio_duration / video_clip.duration))
    final_clip = looped_video_clips.set_audio(audio_clip)
    final_clip.write_videofile("output.mp4", fps=video_clip.fps)

    new_file = bot.files_upload(
        title="My Test Text File",
        file="../assets/output.mp4"
    )
    file_url = new_file.get("file").get("permalink")
    # file_url = upload_file("output.wav")

    say(f"大熊さんからの返答: { message }", files=[{
            "name": "output.wav",
            "url_private": file_url
    }])
    say("file_url: " + file_url)

@app.event("message") # ロギング
def handle_message_events(body, logger):
    logger.info(body)


SocketModeHandler(app, SLACK_APP_TOKEN).start()