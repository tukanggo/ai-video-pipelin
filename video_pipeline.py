import os
import time
import random
import asyncio
import requests
import re
import edge_tts
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

# 从环境变量中读取密钥和配置
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "your-username/your-repo") # 自动获取 GitHub 仓库名
DATABASE_ID = "401e3e5446a9805ea91ddcbb6942de7a"

# 初始化 Gemini
genai.configure(api_key=GEMINI_API_KEY)

DESIGN_TOPICS = [
    {
        "title": "马来西亚老旧公寓厨房改造 (Modern Japandi Kitchen)",
        "focus": "针对采光暗淡、收纳混乱的老旧厨房，打造现代禅意与 Japandi 日式原木风。",
        "craft": "展示微水泥涂墙、定制木作安装、隐藏式暖光 LED 灯带铺设。"
    },
    {
        "title": "狭长型客厅与电视墙改造 (Minimalist Warm Living Room)",
        "focus": "针对传统排屋客厅空间压抑、采光不足、杂物暴露的痛点。",
        "craft": "展示无主灯设计、木饰面格栅背景墙隐形收纳、微水泥地面铺设。"
    }
]

def generate_script():
    topic = random.choice(DESIGN_TOPICS)
    print(f"Generating modular design script for: [{topic['title']}]...")
    
    model = genai.GenerativeModel("gemini-3.8-flash")
    prompt = f"""
    你是一位专业的室内设计短视频编导与内容创作者。请根据以下设计主题，为一期约 60 秒的短视频创作一份分步执行的分镜脚本。
    
    【项目信息】
    - 主题名称：{topic['title']}
    - 核心痛点：{topic['focus']}
    - 施工工艺：{topic['craft']}
    
    【核心格式要求】
    每一幕必须严格包含：
    - 📌 **幕号与主题** 
    - ⏱️ **时间轴** 
    - 🎙️ **口播旁白 (Voiceover)**: (纯中文口播台词)
    - 🎵 **音效 (SFX)**: 
    - 🖼️ **生图提示词**: 
    - 🎥 **生视频提示词**: 
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return topic['title'], response.text
        except ResourceExhausted as e:
            if attempt < max_retries - 1:
                time.sleep(60)
            else:
                raise e

async def text_to_speech(text, output_filename="voiceover.mp3"):
    print(f"正在合成语音旁白 (输出文件: {output_filename})...")
    voice = "zh-CN-XiaoxiaoNeural"
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_filename)
    print(f"✅ 语音合成成功: {output_filename}")

def extract_voiceovers(script_text):
    pattern = r"🎙️\s*\*?口播旁白[^:\n]*[:：]\s*\*?([^\n*]+)"
    matches = re.findall(pattern, script_text)
    if matches:
        return " ".join(matches)
    return re.sub(r'[#*`_]', '', script_text)[:1000]

def split_text_into_chunks(text, max_length=1900):
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

def save_to_notion_with_audio(topic_title, script_content):
    print("Writing to Notion database with native audio block...")
    
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    # 构造 GitHub 仓库中该音频文件的公开直链 (Raw URL)
    # 这样当 GitHub actions 把它 push 到仓库后，Notion 可以直接加载并播放它
    audio_public_url = f"https://raw.githubusercontent.com/{GITHUB_REPOSITORY}/main/voiceover.mp3"
    
    script_chunks = split_text_into_chunks(script_content, max_length=1900)
    rich_text_array = [{"type": "text", "text": {"content": chunk}} for chunk in script_chunks]
    
    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Name": {
                "title": [{"text": {"content": topic_title}}]
            },
            "Script": {
                "rich_text": rich_text_array
            }
        },
        # 💡 核心亮点：在 Notion 页面正文中直接挂载一个原生的音频播放器块！
        "children": [
            {
                "object": "block",
                "type": "audio",
                "audio": {
                    "type": "external",
                    "external": {
                        "url": audio_public_url
                    }
                }
            }
        ]
    }
    
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        print(f"Success: '{topic_title}' and audio block successfully saved to Notion!")
    else:
        print(f"Error: Failed to write -> {response.text}")

if __name__ == "__main__":
    title, script = generate_script()
    voiceover_text = extract_voiceovers(script)
    asyncio.run(text_to_speech(voiceover_text, "voiceover.mp3"))
    save_to_notion_with_audio(title, script)
