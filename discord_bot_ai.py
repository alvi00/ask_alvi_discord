import discord
import os
import requests
import json
import openai
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
openai.api_key = os.getenv("OPENAI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API")
BRAVE_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY")

# Discord Bot Setup
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = discord.Client(intents=intents)

async def fetch_search_results(question, engine="serper"):
    if engine == "serper":
        search_url = "https://google.serper.dev/search"
        headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
        search_data = {"q": question, "num": 5}
        response = requests.post(search_url, headers=headers, data=json.dumps(search_data))
        search_results = response.json()
        snippets = [result.get("snippet", "") for result in search_results.get("organic", [])[:3]]
        links = [result.get("link", "") for result in search_results.get("organic", [])[:3]]
    else:
        search_url = "https://api.search.brave.com/res/v1/web/search"
        headers = {"Accept": "application/json", "X-Subscription-Token": BRAVE_API_KEY}
        params = {"q": question, "count": 5}
        response = requests.get(search_url, headers=headers, params=params)
        search_results = response.json()
        snippets = [result.get("description", "") for result in search_results.get("web", {}).get("results", [])[:3]]
        links = [result.get("url", "") for result in search_results.get("web", {}).get("results", [])[:3]]
    
    return snippets, links

async def generate_response(question, snippets, provider="groq"):
    system_prompt = f"Answer concisely using these search results:\n{snippets}"
    if provider == "groq":
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            model="mixtral-8x7b-32768"
        )
        return chat_completion.choices[0].message.content
    else:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ]
        )
        return response.choices[0].message['content']

@client.event
async def on_ready():
    print(f'✅ Logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("@askalvi"):
        question = message.content[9:].strip()
        if not question:
            await message.channel.send("❌ Please provide a question. Example: `@askalvi What is AI?`")
            return

        await message.channel.send("🔍 Searching for answers...")

        snippets, links = await fetch_search_results(question)
        answer = await generate_response(question, snippets)

        response_text = f"**🤖 Answer:** {answer}\n\n🔗 **Sources:**\n" + "\n".join([f"- {link}" for link in links[:3]])
        await message.channel.send(response_text)

# Run the bot
client.run(DISCORD_TOKEN)
