import os
import requests
import google.generativeai as genai

# 1. Load keys securely from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = "400e3e5446a980a5981fd5ca4e370977"

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

def generate_video_content(topic):
    """Using Gemini to generate a video script"""
    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = f"""
    You are a professional short-form video director. Create a 60-second video script about "{topic}".
    Strictly split it into 3 scenes and include:
    1. Visual Prompts (in English)
    2. Voiceover (in Chinese)
    """
    response = model.generate_content(prompt)
    return response.text

def save_to_notion(title, full_content):
    """Automatically save the script to your Notion database"""
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Name": {
                "title": [{"text": {"content": title}}]
            },
            "Script": {
                "rich_text": [{"text": {"content": full_content}}]
            }
        }
    }
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        print("Success: Script successfully saved to Notion!")
    else:
        print(f"Error: Failed to write -> {response.text}")

if __name__ == "__main__":
    topic_name = "AI Automation Workflow"
    
    print(f"Generating video script for [{topic_name}]...")
    script_text = generate_video_content(topic_name)
    
    print("Writing to Notion database...")
    save_to_notion(topic_name, script_text)
