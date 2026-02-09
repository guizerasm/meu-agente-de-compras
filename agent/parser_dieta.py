import json
from agent.openai_client import client  # ✅ NÃO instanciar OpenAI aqui

SYSTEM = """
Extraia a dieta em JSON estruturado.
Não converse.
"""

def interpretar_dieta(texto: str):
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": texto}
        ],
        temperature=0
    )

    try:
        return json.loads(r.choices[0].message.content)
    except:
        return {}
