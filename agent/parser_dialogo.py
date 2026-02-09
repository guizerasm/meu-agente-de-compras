from agent.openai_client import client



SYSTEM_DIALOGO = """
Você é um assistente de nutrição conversacional.

Objetivo:
Resolver APENAS escolhas pendentes de uma dieta.

REGRAS:
- Faça UMA pergunta por vez
- Seja humano e direto
- NÃO reinterprete a dieta inteira
- NÃO gere lista de compras

Responda APENAS texto natural.
"""

def dialogar(dieta, historico, mensagem):
    historico.append({"role": "user", "content": mensagem})

    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_DIALOGO},
            *historico
        ],
        temperature=0.5
    )

    resposta = r.choices[0].message.content
    historico.append({"role": "assistant", "content": resposta})

    return resposta, historico
