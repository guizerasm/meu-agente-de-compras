from agent.openai_client import client

SYSTEM = """
Você é um assistente inteligente de nutrição e compras.
Converse normalmente, entenda intenções e ajude o usuário.
Nunca gere JSON.
"""

def responder_chat(dieta, historico, mensagem):
    mensagens = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"Dieta atual:\n{dieta}"}
    ]

    for h in historico:
        mensagens.append(h)

    mensagens.append({"role": "user", "content": mensagem})

    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=mensagens,
        temperature=0.6
    )

    resposta = r.choices[0].message.content

    historico.append({"role": "user", "content": mensagem})
    historico.append({"role": "assistant", "content": resposta})

    return resposta, historico
