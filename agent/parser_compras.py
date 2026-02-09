import json
from agent.openai_client import client

SYSTEM = """
Gere uma lista de compras semanal com quantidades reais.
Retorne APENAS JSON.
"""

def gerar_lista(dieta: dict):
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(dieta, ensure_ascii=False)}
        ],
        temperature=0.2
    )

    try:
        return json.loads(r.choices[0].message.content)
    except:
        return []
