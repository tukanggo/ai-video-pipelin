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
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "tukanggo/ai-video-pipelin") # 根据你的仓库名调整
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
    每一幕必须严格包含以下 5 个模块：
    - 📌 **幕号与主题** 
    - ⏱️ **时间轴** 
    - 🎙️ **口播旁白 (Voiceover)**: (纯中文口播台词，不要包含英文提示词或代码符号)
    - 🎵 **音效 (SFX)**: 
    - 🖼️ **第一步：生图提示词**: 
    - 🎥 **第二步：生视频提示词**: 
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
    print(f"正在合成纯旁白语音 (字数: {len(text)})...")
    voice = "zh-CN-XiaoxiaoNeural"
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_filename)
    print(f"✅ 语音合成成功: {output_filename}")

def extract_voiceovers(script_text):
    """
    🎯 核心升级：精确提取所有 '🎙️ 口播旁白' 后面的台词内容，
    过滤掉所有时间轴、音效和生图生视频提示词。
    """
    # 匹配以 🎙️ 或 “口播旁白” 开头，直到行尾或下一个模块的所有中文/英文台词
    pattern = r"(?:🎙️|\*\*?口播旁白[^:\n]*[:：]\*\*?)\s*([^\n#*]+)"
    matches = re.findall(pattern, script_text)
    
    if matches:
        # 清洗并合并所有旁白片段
        clean_lines = [m.strip(" *`-_") for m in matches if len(m.strip()) > 2]
        full_voiceover = " ".join(clean_lines)
        print(f"📌 成功提取的纯旁白内容: {full_voiceover[:150]}...")
        return full_voiceover
    
    # 兜底方案：如果正则没对齐，返回前 800 字纯文本
    print("⚠️ 未能通过正则精准匹配旁白，启动兜底清洗...")
    return re.sub(r'[#*`_]', '', script_text)[:800]

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
    
    # 构造公开直链
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
    
    # 1. 精准提取纯旁白
    voiceover_text = extract_voiceovers(script)
    
    # 2. 合成语音
    asyncio.run(text_to_speech(voiceover_text, "voiceover.mp3"))
    
    # 3. 写入 Notion
    save_to_notion_with_audio(title, script)
