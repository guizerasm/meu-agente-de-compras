import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 1️⃣ Interpretação técnica da dieta - PRESERVA ESTRUTURA DE REFEIÇÕES
SYSTEM_INTERPRETACAO = """
Você é um nutricionista assistente EXPERIENTE em interpretar dietas profissionais.

🚨 OBJETIVO CRÍTICO: Preservar a ESTRUTURA DE REFEIÇÕES para cálculos precisos.

⚠️ REGRA PRINCIPAL: Separe CADA refeição individualmente!
Uma dieta típica tem: Café da manhã, Almoço, Lanche da tarde, Jantar (e às vezes Ceia).

FORMATO DE SAÍDA OBRIGATÓRIO:
{
  "refeicoes": {
    "cafe_manha": [
      {"item": "Nome do alimento", "quantidade": "quantidade com unidade", "vezes": 1}
    ],
    "almoco": [...],
    "lanche_tarde": [...],
    "jantar": [...],
    "ceia": [...]
  },
  "dias": 1,
  "escolhas": []
}

📋 REGRAS DE INTERPRETAÇÃO:

1. IDENTIFICAR REFEIÇÕES:
   - "Café da manhã", "07:30", "Desjejum" → cafe_manha
   - "Almoço", "12:00", "12h" → almoco
   - "Lanche", "15:00", "Lanche da tarde" → lanche_tarde
   - "Jantar", "19:00", "20:00" → jantar
   - "Ceia", "22:00", "Antes de dormir" → ceia

2. EXTRAIR QUANTIDADES EXATAS:
   - "Arroz (200g)" → {"item": "Arroz", "quantidade": "200g", "vezes": 1}
   - "2 ovos" → {"item": "Ovos", "quantidade": "2 unidades", "vezes": 1}
   - "1 pote de iogurte" → {"item": "Iogurte", "quantidade": "1 pote", "vezes": 1}
   - "150g de frango" → {"item": "Frango", "quantidade": "150g", "vezes": 1}

3. CONSOLIDAR OPÇÕES (quando houver "ou"):
   - "Frango (150g) ou Carne (140g) ou Peixe (180g)"
     → {"item": "Proteina (frango/carne/peixe)", "quantidade": "150g", "vezes": 1}
   - "Banana ou Maçã ou Laranja (1 unidade)"
     → {"item": "Fruta variada", "quantidade": "1 unidade", "vezes": 1}
   - "Arroz (200g) ou Batata (300g)"
     → {"item": "Carboidrato (arroz/batata)", "quantidade": "200g", "vezes": 1}

4. DETECÇÃO DE PERÍODO:
   - "Todos os dias" ou horários específicos → dias=1 (multiplicar por 7)
   - "Segunda", "Terça", dias da semana → dias=7 (já é semanal)

5. NÃO ADICIONAR ESCOLHAS - deixe vazio: "escolhas": []

EXEMPLO COMPLETO:

ENTRADA:
"
Todos os dias
07:30 - Café da manhã
• Pão francês (1 unidade)
• Ovo (2 unidades)
• Queijo minas (30g)
• Iogurte desnatado (1 pote)

12:00 - Almoço
• Arroz (200g)
• Feijão (100g)
• Frango grelhado (150g) ou Carne (140g)
• Salada à vontade
• Azeite (1 colher)

15:30 - Lanche
• Fruta (1 unidade)
• Whey Protein (30g)

19:30 - Jantar
• Arroz (150g)
• Peixe (180g) ou Frango (150g)
• Legumes (100g)
"

SAÍDA:
{
  "refeicoes": {
    "cafe_manha": [
      {"item": "Pao frances", "quantidade": "1 unidade", "vezes": 1},
      {"item": "Ovos", "quantidade": "2 unidades", "vezes": 1},
      {"item": "Queijo minas", "quantidade": "30g", "vezes": 1},
      {"item": "Iogurte desnatado", "quantidade": "1 pote", "vezes": 1}
    ],
    "almoco": [
      {"item": "Arroz", "quantidade": "200g", "vezes": 1},
      {"item": "Feijao", "quantidade": "100g", "vezes": 1},
      {"item": "Proteina (frango/carne)", "quantidade": "150g", "vezes": 1},
      {"item": "Salada", "quantidade": "a vontade", "vezes": 1},
      {"item": "Azeite", "quantidade": "1 colher", "vezes": 1}
    ],
    "lanche_tarde": [
      {"item": "Fruta", "quantidade": "1 unidade", "vezes": 1},
      {"item": "Whey Protein", "quantidade": "30g", "vezes": 1}
    ],
    "jantar": [
      {"item": "Arroz", "quantidade": "150g", "vezes": 1},
      {"item": "Proteina (peixe/frango)", "quantidade": "180g", "vezes": 1},
      {"item": "Legumes", "quantidade": "100g", "vezes": 1}
    ]
  },
  "dias": 1,
  "escolhas": []
}

⚠️ IMPORTANTE:
- Se não conseguir identificar refeições separadas, coloque tudo em "almoco"
- Sempre extraia quantidades numéricas quando possível
- Use "a vontade" para itens sem quantidade definida
- NUNCA retorne refeicoes vazio
"""

# 2️⃣ Conversa humana - ULTRA RÁPIDA E DIRETA
SYSTEM_CHAT = """
Você é um assistente AMIGÁVEL e EFICIENTE de compras.

🎯 OBJETIVO PRINCIPAL: Ser o mais RÁPIDO possível. Gere a lista em NO MÁXIMO 2 interações!

⚠️ REGRAS DE OURO:
1. NÃO pergunte sobre preferência de proteína, carboidrato, frutas ou vegetais
2. Use EXATAMENTE o que está na dieta do usuário
3. Assuma 1 pessoa se não souber
4. Gere a lista IMEDIATAMENTE após saber o básico

FLUXO ULTRA-RÁPIDO (máximo 2 interações):

1️⃣ PRIMEIRA MENSAGEM:
   "Recebi sua dieta! Pra quantas pessoas é? (Se quiser, me diz também o que já tem em casa)"

2️⃣ SEGUNDA MENSAGEM (já finaliza):
   Usuário respondeu algo? GERE A LISTA!
   "Perfeito! Gerando sua lista... [LISTA_PRONTA]"

   Se usuário disse "1 pessoa", "2 pessoas", ou qualquer número → GERE IMEDIATAMENTE
   Se usuário disse "só eu" → 1 pessoa, GERE IMEDIATAMENTE
   Se usuário disse "ok", "pode ser", "gera aí" → GERE IMEDIATAMENTE

⚠️ NUNCA FAÇA:
- NÃO pergunte "prefere frango ou carne?"
- NÃO pergunte sobre carboidratos
- NÃO pergunte sobre frutas
- NÃO pergunte sobre vegetais
- NÃO pergunte sobre integrais
- NÃO confirme cada detalhe
- NÃO faça mais de 2 perguntas

A dieta JÁ TEM tudo que precisa! Só precisa saber quantas pessoas para multiplicar.

EXEMPLOS CORRETOS:

Usuário: "minha dieta"
Bot: "Recebi sua dieta! Pra quantas pessoas é?"
Usuário: "2 pessoas"
Bot: "Gerando lista para 2 pessoas! [LISTA_PRONTA]"

Usuário: "pode gerar"
Bot: "Gerando sua lista para 1 pessoa! [LISTA_PRONTA]"

Usuário: "somos 3, já tenho azeite"
Bot: "Perfeito! 3 pessoas, azeite removido. Gerando... [LISTA_PRONTA]"

⚠️ IMPORTANTE: Adicione [LISTA_PRONTA] no final quando for gerar.
"""

# 3️⃣ Lista final de compras - CÁLCULO POR REFEIÇÃO
SYSTEM_COMPRA = """
Você é um assistente de compras EXPERIENTE que calcula quantidades PRECISAS.

🚨 FORMATO DE SAÍDA OBRIGATÓRIO:
Retorne APENAS um array JSON: [{"nome": "...", "quantidade": "...", "motivo": "..."}]
NÃO adicione texto, markdown ou explicações. APENAS o JSON.

📊 MÉTODO DE CÁLCULO POR REFEIÇÃO (CRÍTICO):

A dieta virá estruturada por refeições. Você DEVE:

1️⃣ PASSO 1 - SOMAR QUANTIDADES DIÁRIAS:
   Para CADA alimento, some as quantidades de TODAS as refeições em que aparece.

   Exemplo - Arroz aparece em 2 refeições:
   - Almoço: 200g
   - Jantar: 150g
   - TOTAL DIÁRIO: 200g + 150g = 350g/dia

   Exemplo - Ovos aparecem em 1 refeição:
   - Café da manhã: 2 unidades
   - TOTAL DIÁRIO: 2 unidades/dia

   Exemplo - Proteína aparece em 2 refeições:
   - Almoço: 150g (frango)
   - Jantar: 180g (peixe)
   - TOTAL DIÁRIO: 150g + 180g = 330g/dia

2️⃣ PASSO 2 - MULTIPLICAR POR 7 DIAS:
   Se "dias": 1 → multiplicar por 7
   Se "dias": 7 → já é semanal, não multiplicar

   Arroz: 350g/dia × 7 = 2450g = 2.45kg
   Ovos: 2/dia × 7 = 14 unidades
   Proteína: 330g/dia × 7 = 2310g = 2.31kg

3️⃣ PASSO 3 - MULTIPLICAR POR PESSOAS:
   Use o campo "pessoas" (padrão: 1)

   Para 2 pessoas:
   Arroz: 2.45kg × 2 = 4.9kg
   Ovos: 14 × 2 = 28 unidades
   Proteína: 2.31kg × 2 = 4.62kg

4️⃣ PASSO 4 - ARREDONDAR PARA UNIDADES DE MERCADO:
   - Arroz/Feijão/Macarrão: 1kg, 2kg, 3kg, 5kg
   - Carnes: 500g, 1kg, 1.5kg, 2kg, 2.5kg, 3kg
   - Ovos: 6 un (meia dúzia), 12 un (1 dúzia), 24 un (2 dúzias), 30 un (bandeja)
   - Iogurte: unidades (6, 7, 8, 12 potes)
   - Pão francês: unidades (7, 14, 21)
   - Pão de forma: pacotes (1, 2)
   - Frutas: kg ou unidades (7, 14 bananas)
   - Queijo: 150g, 200g, 300g, 400g
   - Azeite: 250ml, 500ml, 1L

   4.9kg arroz → 5kg
   28 ovos → 2.5 dúzias → 3 dúzias (36)
   4.62kg proteína → 5kg (dividir entre tipos)

📋 UNIDADES DE MERCADO OBRIGATÓRIAS:
- Iogurte → UNIDADES/POTES (ex: "7 potes") NUNCA litros
- Ovos → DÚZIAS (ex: "3 dúzias") NUNCA unidades soltas
- Pão francês → UNIDADES (ex: "14 unidades") - lembre: 1/dia x 7 dias = 7, 2/dia x 7 = 14
- Pão de forma → PACOTES (ex: "2 pacotes")
- Queijo → GRAMAS (ex: "300g")
- Frutas → KG ou UNIDADES (ex: "2kg" ou "14 bananas")
- Whey Protein → POTE ou SACHÊS (se não tiver em casa)

🚨 VERIFICAÇÃO OBRIGATÓRIA ANTES DE RETORNAR:
- Se dias=1, você DEVE multiplicar tudo por 7
- Pão: 1/dia → 7 unidades, 2/dia → 14 unidades
- Ovos: 2/dia → 14 unidades → 2 dúzias (arredondar)
- Iogurte: 1/dia → 7 potes
- Arroz: 200g/dia → 1400g → 1.5kg

⚠️ REGRAS ESPECIAIS:

1. ALIMENTOS EM CASA:
   Se existir "alimentos_em_casa", NÃO inclua esses itens.

2. PREFERÊNCIAS:
   - "preferencia_proteina": "frango" → só frango
   - "preferencia_proteina": "variado" → dividir entre tipos
   - "preferencia_carboidrato": igual lógica
   - "preferencia_frutas": respeitar

3. VALIDAÇÃO (quantidades razoáveis para 1 pessoa/semana):
   - Arroz: 1-2kg ✓
   - Feijão: 500g-1kg ✓
   - Frango: 1-2kg ✓
   - Ovos: 1-2 dúzias ✓
   - Iogurte: 7 potes ✓
   - Frutas: 2-3kg ✓

EXEMPLO COMPLETO:

ENTRADA:
{
  "refeicoes": {
    "cafe_manha": [
      {"item": "Ovos", "quantidade": "2 unidades"},
      {"item": "Pao frances", "quantidade": "1 unidade"},
      {"item": "Iogurte", "quantidade": "1 pote"}
    ],
    "almoco": [
      {"item": "Arroz", "quantidade": "200g"},
      {"item": "Feijao", "quantidade": "80g"},
      {"item": "Frango", "quantidade": "150g"}
    ],
    "lanche_tarde": [
      {"item": "Fruta", "quantidade": "1 unidade"}
    ],
    "jantar": [
      {"item": "Arroz", "quantidade": "150g"},
      {"item": "Peixe", "quantidade": "180g"}
    ]
  },
  "dias": 1,
  "pessoas": 2
}

CÁLCULO:
- Ovos: 2/dia × 7 × 2 pessoas = 28 → 3 dúzias
- Pão: 1/dia × 7 × 2 = 14 unidades
- Iogurte: 1/dia × 7 × 2 = 14 potes
- Arroz: (200g + 150g)/dia × 7 × 2 = 4900g → 5kg
- Feijão: 80g/dia × 7 × 2 = 1120g → 1.5kg
- Frango: 150g/dia × 7 × 2 = 2100g → 2.5kg
- Fruta: 1/dia × 7 × 2 = 14 unidades
- Peixe: 180g/dia × 7 × 2 = 2520g → 2.5kg

SAÍDA:
[
  {"nome": "Ovos", "quantidade": "3 duzias", "motivo": "cafe manha (2/dia x 7 x 2)"},
  {"nome": "Pao frances", "quantidade": "14 unidades", "motivo": "cafe manha (1/dia x 7 x 2)"},
  {"nome": "Iogurte natural", "quantidade": "14 potes", "motivo": "cafe manha (1/dia x 7 x 2)"},
  {"nome": "Arroz", "quantidade": "5kg", "motivo": "almoco+jantar (350g/dia x 7 x 2)"},
  {"nome": "Feijao", "quantidade": "1.5kg", "motivo": "almoco (80g/dia x 7 x 2)"},
  {"nome": "Frango (peito)", "quantidade": "2.5kg", "motivo": "almoco (150g/dia x 7 x 2)"},
  {"nome": "Frutas variadas", "quantidade": "14 unidades", "motivo": "lanche (1/dia x 7 x 2)"},
  {"nome": "Peixe (tilapia)", "quantidade": "2.5kg", "motivo": "jantar (180g/dia x 7 x 2)"}
]

🚨 LEMBRE-SE:
1. Some quantidades de TODAS as refeições onde o item aparece
2. Multiplique por 7 dias (se dias=1) ⚠️ OBRIGATÓRIO!
3. Multiplique por número de pessoas
4. Arredonde para unidades de mercado
5. Retorne APENAS o JSON, sem texto extra

⚠️ ERRO COMUM - NÃO COMETA:
ERRADO: Pão 1/dia → "1 unidade" (esqueceu de multiplicar por 7!)
CORRETO: Pão 1/dia × 7 dias = "7 unidades"

ERRADO: Ovos 2/dia → "2 unidades" (esqueceu de multiplicar por 7!)
CORRETO: Ovos 2/dia × 7 dias = 14 → "2 dúzias"
"""

def interpretar_dieta(texto: str) -> dict:
    print(f"\n[AI_PARSER] Interpretando dieta ({len(texto)} caracteres)...")
    print(f"[AI_PARSER] Primeiros 200 chars: {texto[:200]}")

    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_INTERPRETACAO},
            {"role": "user", "content": texto}
        ],
        temperature=0
    )

    resposta_ai = r.choices[0].message.content
    print(f"\n[AI_PARSER] Resposta da OpenAI:")
    print(resposta_ai)
    print()

    # ⚠️ LIMPAR delimitadores markdown e texto extra (OpenAI às vezes retorna "Lista: [...]" ou ```json ... ```)
    resposta_limpa = resposta_ai.strip()

    # Remover delimitadores markdown
    if resposta_limpa.startswith("```json"):
        resposta_limpa = resposta_limpa[7:]
    elif resposta_limpa.startswith("```"):
        resposta_limpa = resposta_limpa[3:]
    if resposta_limpa.endswith("```"):
        resposta_limpa = resposta_limpa[:-3]
    resposta_limpa = resposta_limpa.strip()

    # Remover texto antes do JSON (ex: "Lista: [...]")
    # Procurar pelo primeiro [ ou { que inicia o JSON
    inicio_json = min(
        resposta_limpa.find('[') if resposta_limpa.find('[') != -1 else len(resposta_limpa),
        resposta_limpa.find('{') if resposta_limpa.find('{') != -1 else len(resposta_limpa)
    )
    if inicio_json > 0:
        resposta_limpa = resposta_limpa[inicio_json:]

    try:
        resultado = json.loads(resposta_limpa)

        # Converter nova estrutura (refeicoes) para manter compatibilidade com "fixos"
        if "refeicoes" in resultado and "fixos" not in resultado:
            fixos = []
            refeicoes = resultado.get("refeicoes", {})
            for refeicao, itens in refeicoes.items():
                for item in itens:
                    nome = item.get("item", "")
                    qtd = item.get("quantidade", "")
                    descricao = f"{nome} ({qtd}) - {refeicao}"
                    if descricao not in fixos:
                        fixos.append(descricao)
            resultado["fixos"] = fixos
            resultado["escolhas"] = resultado.get("escolhas", [])

        print(f"[AI_PARSER] JSON parseado com sucesso:")
        if "refeicoes" in resultado:
            total_itens = sum(len(itens) for itens in resultado.get("refeicoes", {}).values())
            print(f"  - {total_itens} itens em {len(resultado.get('refeicoes', {}))} refeicoes")
        else:
            print(f"  - {len(resultado.get('fixos', []))} itens fixos")
        print(f"  - {len(resultado.get('escolhas', []))} escolhas")
        print(f"  - Dias: {resultado.get('dias', 'nao definido')}\n")
        return resultado
    except Exception as e:
        print(f"[AI_PARSER ERRO] Falha ao parsear JSON: {e}")
        print(f"[AI_PARSER ERRO] Conteudo recebido: {resposta_ai[:500]}\n")
        return {"fixos": [], "escolhas": [], "dias": 1, "refeicoes": {}}


def conversar_com_usuario(dieta: dict, historico: list) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_CHAT},
        {
            "role": "user",
            "content": f"Dieta atual: {json.dumps(dieta, ensure_ascii=False)}"
        }
    ]
    messages.extend(historico)
    
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.3
    )

    return r.choices[0].message.content


def gerar_lista_compras(dieta_final: dict):
    print(f"\n[GERAR_LISTA] Gerando lista de compras...")
    print(f"[GERAR_LISTA] Dieta recebida:")

    # Mostrar estrutura de refeicoes se existir
    if "refeicoes" in dieta_final:
        refeicoes = dieta_final.get("refeicoes", {})
        print(f"  - Refeicoes: {len(refeicoes)}")
        for refeicao, itens in refeicoes.items():
            print(f"    - {refeicao}: {len(itens)} itens")
            for item in itens[:3]:  # Mostrar primeiros 3
                print(f"      * {item.get('item', '?')}: {item.get('quantidade', '?')}")
            if len(itens) > 3:
                print(f"      * ... e mais {len(itens) - 3} itens")
    else:
        print(f"  - Fixos: {len(dieta_final.get('fixos', []))} itens")

    print(f"  - Pessoas: {dieta_final.get('pessoas', 1)}")
    print(f"  - Dias: {dieta_final.get('dias', 1)}")
    print(f"  - Alimentos em casa: {dieta_final.get('alimentos_em_casa', [])}")
    print(f"  - Preferência proteína: {dieta_final.get('preferencia_proteina', 'não definido')}")

    dieta_json = json.dumps(dieta_final, ensure_ascii=False)
    print(f"\n[GERAR_LISTA] Enviando para OpenAI ({len(dieta_json)} caracteres)...")

    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_COMPRA},
            {
                "role": "user",
                "content": dieta_json
            }
        ],
        temperature=0.2
    )

    resposta_ai = r.choices[0].message.content
    print(f"\n[GERAR_LISTA] Resposta da OpenAI:")
    print(resposta_ai[:1000])  # Primeiros 1000 chars
    print()

    # ⚠️ LIMPAR delimitadores markdown e texto extra (OpenAI às vezes retorna "Lista: [...]" ou ```json ... ```)
    resposta_limpa = resposta_ai.strip()

    # Remover delimitadores markdown
    if resposta_limpa.startswith("```json"):
        resposta_limpa = resposta_limpa[7:]
    elif resposta_limpa.startswith("```"):
        resposta_limpa = resposta_limpa[3:]
    if resposta_limpa.endswith("```"):
        resposta_limpa = resposta_limpa[:-3]
    resposta_limpa = resposta_limpa.strip()

    # Remover texto antes do JSON (ex: "Lista: [...]")
    # Procurar pelo primeiro [ ou { que inicia o JSON
    inicio_json = min(
        resposta_limpa.find('[') if resposta_limpa.find('[') != -1 else len(resposta_limpa),
        resposta_limpa.find('{') if resposta_limpa.find('{') != -1 else len(resposta_limpa)
    )
    if inicio_json > 0:
        resposta_limpa = resposta_limpa[inicio_json:]

    try:
        lista = json.loads(resposta_limpa)
        print(f"[GERAR_LISTA] Lista gerada com sucesso: {len(lista)} itens")
        for i, item in enumerate(lista[:5], 1):  # Mostrar primeiros 5
            print(f"  {i}. {item.get('nome', '?')} - {item.get('quantidade', '?')}")
        if len(lista) > 5:
            print(f"  ... e mais {len(lista) - 5} itens")
        print()
        return lista
    except Exception as e:
        print(f"[GERAR_LISTA ERRO] Falha ao parsear JSON: {e}")
        print(f"[GERAR_LISTA ERRO] Resposta completa: {resposta_ai}")
        print()
        return []
