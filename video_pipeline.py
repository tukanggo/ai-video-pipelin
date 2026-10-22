import os
import time
import random
import requests
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

# 从环境变量中读取密钥和配置
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
DATABASE_ID = "401e3e5446a9805ea91ddcbb6942de7a"

# 初始化 Gemini
genai.configure(api_key=GEMINI_API_KEY)

# 💡 室内设计主题库：每次运行会随机挑选一个不同的主题，让自动化内容丰富多彩！
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
    },
    {
        "title": "顶楼阳光房/露台花园改造 (Tropical Zen Balcony & Lounge)",
        "focus": "针对闷热、暴晒、荒废的露台或阳台空间。",
        "craft": "展示防腐木地台、垂直绿化垂直竹墙、户外折叠遮阳篷与氛围暖光安装。"
    },
    {
        "title": "小户型主卧衣帽间一体化改造 (Wabi-Sabi Master Bedroom)",
        "focus": "针对主卧空间局促、储物空间不足、缺乏氛围感的问题。",
        "craft": "展示弧形艺术墙面涂刷、嵌入式通顶无把手衣柜、床头悬浮灯带安装。"
    },
    {
        "title": "工业风复式 Loft 楼梯与书房改造 (Industrial Japandi Loft)",
        "focus": "针对老旧铁艺楼梯冰冷、畸形角落浪费、采光被遮挡的痛点。",
        "craft": "展示钢木结合悬浮踏步安装、墙面艺术涂料、定制原木转角书桌。"
    }
]

def generate_script():
    # 随机选择一个设计主题
    topic = random.choice(DESIGN_TOPICS)
    print(f"Generating video script for topic: [{topic['titleysta'] if 'ysta' in topic else topic['title']}]...")
    
    model = genai.GenerativeModel("gemini-3.8-flash")
    
    # 动态模板化 Prompt
    prompt = f"""
    你是一位专业的室内设计短视频编导与内容创作者。请根据以下规则，为一期关于『{topic['title']}』的短视频创作一份精准的 60 秒分镜脚本。
    
    核心改造方向：{topic['focus']}
    施工核心工艺：{topic['craft']}
    
    严格遵循以下 3 个节奏阶段 (Pacing)：
    1. 0-15s (老旧现状与痛点): 展现马来西亚或东南亚常见的拥挤、采光暗淡、空间局促的老旧实景。
    2. 15-45s (匠心施工过程): 专业施工团队进驻，重点展示{topic['craft']}等幕后纪实。
    3. 45-60s (惊艳焕新呈现): 现代禅意 (Modern Zen) 与高级感完美融合的明亮新空间揭幕。
    
    技术规格要求 (Video Prompts):
    - 画面分辨率: HD 1280x720 (16:9 aspect ratio)
    - 帧率: 60fps
    - 风格: Photorealistic, cinematic, architectural documentary style, smooth transitions.
    
    输出格式要求：
    必须包含三大板块（Visuals 画面描述、Video Prompt 英文AI提示词、Audio & Voiceover 中文配音与音效）。内容要生动、极具高级感，适合发布在抖音、TikTok 或小红书上。
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            # 同时返回生成的文本和当前主题标题，方便写入 Notion
            return topic['title'], response.text
        except ResourceExhausted as e:
            if attempt < max_retries - 1:
                print(f"触发免费版频率限制 (429)，正在等待 60 秒后进行第 {attempt + 2} 次重试...")
                time.sleep(60)
            else:
                print("已达到最大重试次数，API 额度耗尽。")
                raise e

def split_text_into_chunks(text, max_length=2000):
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

def save_to_notion(topic_title, script_content):
    print("Writing to Notion database...")
    
    url = "https://api.notion.com/v1/pages"
    
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    script_chunks = split_text_into_chunks(script_content, max_length=2000)
    
    rich_text_array = []
    for chunk in script_chunks:
        rich_text_array.append({
            "type": "text",
            "text": {
                "content": chunk
            }
        })
    
    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": topic_title  # 动态将当前随机抽到的主题作为 Notion 的名称
                        }
                    }
                ]
            },
            "Script": {
                "rich_text": rich_text_array
            }
        }
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        print(f"Success: '{topic_title}' script successfully saved to Notion!")
    else:
        print(f"Error: Failed to write -> {response.text}")

if __name__ == "__main__":
    title, script = generate_script()
    save_to_notion(title, script)
