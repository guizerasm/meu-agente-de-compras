import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)  # 🔴 ISSO RESOLVE 90% DOS SEUS ERROS

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)
