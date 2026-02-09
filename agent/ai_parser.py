import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 1️⃣ Interpretação técnica da dieta - PRESERVA ESTRUTURA DE REFEIÇÕES
SYSTEM_INTERPRETACAO = """
Você é um nutricionista que interpreta dietas.

🎯 OBJETIVO: Extrair alimentos e quantidades de cada refeição.

FORMATO DE SAÍDA (JSON):
{
  "refeicoes": {
    "cafe_manha": [{"item": "nome", "quantidade": "qtd", "vezes": 1}],
    "almoco": [...],
    "lanche_tarde": [...],
    "jantar": [...],
    "ceia": [...]
  },
  "dias": 1,
  "escolhas": []
}

🚨 REGRA CRÍTICA - OPÇÕES COM "OU":
Quando a dieta diz "X ou Y ou Z", isso é UMA ESCOLHA, não 3 alimentos!
O usuário come X OU Y OU Z, nunca os 3 juntos!

ERRADO (NÃO FAÇA):
"Frango ou Carne ou Peixe" →
  {"item": "Frango", "quantidade": "150g"},
  {"item": "Carne", "quantidade": "140g"},
  {"item": "Peixe", "quantidade": "180g"}
(Isso triplica a proteína! ERRADO!)

CORRETO:
"Frango (150g) ou Carne (140g) ou Peixe (180g)" →
  {"item": "Proteina variada", "quantidade": "150g", "vezes": 1}
(É UMA porção de proteína por refeição, o tipo varia!)

MAIS EXEMPLOS CORRETOS:
- "Banana ou Maçã ou Laranja" → {"item": "Fruta", "quantidade": "1 unidade"}
- "Arroz ou Batata" → {"item": "Carboidrato", "quantidade": "200g"}
- "Leite ou Iogurte" → {"item": "Laticinio", "quantidade": "1 porcao"}

REGRAS:
1. Identificar refeições pelos horários ou nomes (café, almoço, lanche, jantar, ceia)
2. Extrair quantidades numéricas (200g, 2 unidades, 1 pote)
3. "à vontade" ou sem quantidade → "a vontade"
4. dias=1 significa dieta diária (sistema multiplica por 7)
5. escolhas = [] (sempre vazio)

⚠️ NUNCA duplique/triplique itens que são opções!
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

# 3️⃣ Lista final de compras - FORMATAR LISTA PRÉ-CALCULADA
SYSTEM_COMPRA = """
Você recebe uma lista de compras JÁ CALCULADA pelo sistema.
Sua função é apenas FORMATAR para exibição ao usuário.

ENTRADA: Lista com quantidades já calculadas para a semana
SAÍDA: JSON array formatado

Regras de formatação:
1. Ovos: converter para dúzias (12 un = 1 dúzia, 24 un = 2 dúzias)
2. Iogurte: manter em "potes"
3. Pão: manter em "unidades"
4. Grãos (arroz, feijão): arredondar para kg (1kg, 1.5kg, 2kg)
5. Carnes: arredondar para 500g, 1kg, 1.5kg, 2kg, etc.
6. Frutas: manter unidades ou converter para kg

Formato de saída:
[{"nome": "Item", "quantidade": "X unidade", "motivo": "refeição (cálculo)"}]

Se a lista vier vazia ou com erro, retorne:
[{"nome": "Erro", "quantidade": "-", "motivo": "Não foi possível calcular"}]
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
            print(f"  - {total_itens} itens em {len(resultado.get('refeicoes', {}))} refeicoes (antes consolidação)")

            # ✅ CONSOLIDAR SUBSTITUIÇÕES (frango/carne/peixe → proteína variada)
            resultado = consolidar_substituicoes(resultado)

            # Recalcular fixos após consolidação
            fixos = []
            for refeicao, itens in resultado.get("refeicoes", {}).items():
                for item in itens:
                    nome = item.get("item", "")
                    qtd = item.get("quantidade", "")
                    descricao = f"{nome} ({qtd}) - {refeicao}"
                    if descricao not in fixos:
                        fixos.append(descricao)
            resultado["fixos"] = fixos

            total_itens_depois = sum(len(itens) for itens in resultado.get("refeicoes", {}).values())
            print(f"  - {total_itens_depois} itens após consolidação")
        else:
            print(f"  - {len(resultado.get('fixos', []))} itens fixos")
        print(f"  - {len(resultado.get('escolhas', []))} escolhas")
        print(f"  - Dias: {resultado.get('dias', 'nao definido')}\n")
        return resultado
    except Exception as e:
        print(f"[AI_PARSER ERRO] Falha ao parsear JSON: {e}")
        print(f"[AI_PARSER ERRO] Conteudo recebido: {resposta_ai[:500]}\n")
        return {"fixos": [], "escolhas": [], "dias": 1, "refeicoes": {}}


def extrair_numero_quantidade(qtd_str: str) -> float:
    """Extrai o número de uma string de quantidade (ex: '150g' -> 150)"""
    import re
    match = re.search(r'(\d+\.?\d*)', qtd_str)
    return float(match.group(1)) if match else 0


def consolidar_substituicoes(dieta: dict) -> dict:
    """
    Pós-processamento:
    1. REMOVE refeições marcadas como "substituição" (são alternativas, não principais)
    2. Quando há múltiplas opções de proteína/carboidrato/fruta na mesma refeição,
       mantém apenas o PRIMEIRO item (o principal) com sua quantidade correta.

    Exemplo:
    - "Frango 150g OU Carne 140g OU Peixe 180g"
    - Resultado: Frango 150g (o primeiro, é o padrão)
    - Se usuário quiser trocar, ele pede na etapa de ajustes
    """
    # Palavras que indicam que a refeição é uma SUBSTITUIÇÃO (ignorar)
    PALAVRAS_SUBSTITUICAO = [
        # Português
        "substituição", "substituicao", "substitui", "substituir",
        "alternativa", "alternativo",
        "opção", "opcao", "opcional",
        "troca", "trocar",
        "variação", "variacao",
        "sugestão", "sugestao",
        # Padrões comuns
        "ou_", "_ou_", "opcao_", "alt_",
        # Inglês
        "replace", "alternative", "option", "swap"
    ]

    # Categorias de substituição de alimentos
    PROTEINAS = ["frango", "carne", "peixe", "tilapia", "filé", "file", "bife",
                 "alcatra", "patinho", "acém", "acem", "costela", "lombo",
                 "peito de frango", "coxa", "sobrecoxa", "salmão", "salmon", "atum",
                 "proteina", "proteína"]
    CARBOIDRATOS = ["arroz", "batata", "macarrão", "macarrao", "massa", "nhoque",
                    "batata doce", "mandioca", "inhame", "cará", "cara", "carboidrato"]
    FRUTAS = ["banana", "maçã", "maca", "laranja", "mamão", "mamao", "melão",
              "melao", "melancia", "abacaxi", "manga", "uva", "morango", "kiwi",
              "pera", "pêra", "goiaba", "ameixa", "fruta"]

    refeicoes = dieta.get("refeicoes", {})
    if not refeicoes:
        return dieta

    print(f"\n[CONSOLIDAR] Verificando substituições...")

    # PASSO 1: Filtrar refeições que são substituições
    refeicoes_principais = {}
    for nome_refeicao, itens in refeicoes.items():
        nome_lower = nome_refeicao.lower()
        eh_substituicao = any(palavra in nome_lower for palavra in PALAVRAS_SUBSTITUICAO)

        if eh_substituicao:
            print(f"  - IGNORANDO refeição '{nome_refeicao}' (é substituição)")
        else:
            refeicoes_principais[nome_refeicao] = itens

    # Atualizar para usar apenas refeições principais
    refeicoes = refeicoes_principais

    novas_refeicoes = {}

    for nome_refeicao, itens in refeicoes.items():
        proteinas_encontradas = []
        carboidratos_encontrados = []
        frutas_encontradas = []
        outros_itens = []

        for item in itens:
            nome_lower = item.get("item", "").lower()
            encontrou = False

            for p in PROTEINAS:
                if p in nome_lower:
                    proteinas_encontradas.append(item)
                    encontrou = True
                    break

            if not encontrou:
                for c in CARBOIDRATOS:
                    if c in nome_lower:
                        carboidratos_encontrados.append(item)
                        encontrou = True
                        break

            if not encontrou:
                for f in FRUTAS:
                    if f in nome_lower:
                        frutas_encontradas.append(item)
                        encontrou = True
                        break

            if not encontrou:
                outros_itens.append(item)

        novos_itens = outros_itens.copy()

        # PROTEÍNAS: pegar o PRIMEIRO (o principal)
        if len(proteinas_encontradas) > 1:
            primeiro = proteinas_encontradas[0]
            print(f"  - {nome_refeicao}: {len(proteinas_encontradas)} proteínas → mantendo '{primeiro.get('item')}' ({primeiro.get('quantidade')})")
            novos_itens.append(primeiro)
        elif len(proteinas_encontradas) == 1:
            novos_itens.append(proteinas_encontradas[0])

        # CARBOIDRATOS: pegar o PRIMEIRO
        if len(carboidratos_encontrados) > 1:
            primeiro = carboidratos_encontrados[0]
            print(f"  - {nome_refeicao}: {len(carboidratos_encontrados)} carboidratos → mantendo '{primeiro.get('item')}' ({primeiro.get('quantidade')})")
            novos_itens.append(primeiro)
        elif len(carboidratos_encontrados) == 1:
            novos_itens.append(carboidratos_encontrados[0])

        # FRUTAS: pegar a PRIMEIRA
        if len(frutas_encontradas) > 1:
            primeiro = frutas_encontradas[0]
            print(f"  - {nome_refeicao}: {len(frutas_encontradas)} frutas → mantendo '{primeiro.get('item')}' ({primeiro.get('quantidade')})")
            novos_itens.append(primeiro)
        elif len(frutas_encontradas) == 1:
            novos_itens.append(frutas_encontradas[0])

        novas_refeicoes[nome_refeicao] = novos_itens

    dieta["refeicoes"] = novas_refeicoes
    print(f"[CONSOLIDAR] Concluído\n")
    return dieta


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


def calcular_quantidades_python(dieta: dict) -> list:
    """
    Calcula quantidades de compras usando Python (não depende da IA para contas)
    """
    import re
    from collections import defaultdict

    refeicoes = dieta.get("refeicoes", {})
    dias = dieta.get("dias", 1)
    pessoas = dieta.get("pessoas", 1)
    alimentos_em_casa = [a.lower() for a in dieta.get("alimentos_em_casa", [])]

    # Multiplicador: se dias=1, é dieta diária, multiplicar por 7
    multiplicador_dias = 7 if dias == 1 else 1

    print(f"\n[CALC_PYTHON] Calculando quantidades...")
    print(f"  - Dias na dieta: {dias} → multiplicador: {multiplicador_dias}")
    print(f"  - Pessoas: {pessoas}")
    print(f"  - Alimentos em casa: {alimentos_em_casa}")

    # Agregar quantidades por item
    itens_agregados = defaultdict(lambda: {"quantidade_total": 0, "unidade": "", "refeicoes": []})

    for nome_refeicao, itens in refeicoes.items():
        for item in itens:
            nome_item = item.get("item", "").strip()
            qtd_str = item.get("quantidade", "").strip().lower()

            # Pular itens "a vontade" ou vazios
            if not nome_item or qtd_str in ["a vontade", "à vontade", ""]:
                continue

            # Verificar se já tem em casa
            if any(casa in nome_item.lower() for casa in alimentos_em_casa):
                print(f"  - Pulando {nome_item} (já tem em casa)")
                continue

            # Extrair número e unidade
            match = re.search(r'(\d+\.?\d*)\s*(g|kg|ml|l|unidade|unidades|pote|potes|colher|colheres|fatia|fatias)?', qtd_str)
            if match:
                qtd_num = float(match.group(1))
                unidade = match.group(2) or "unidade"

                # Normalizar unidades
                if unidade in ["unidades"]:
                    unidade = "unidade"
                elif unidade in ["potes"]:
                    unidade = "pote"
                elif unidade in ["colheres"]:
                    unidade = "colher"
                elif unidade in ["fatias"]:
                    unidade = "fatia"
                elif unidade == "l":
                    unidade = "ml"
                    qtd_num *= 1000
                elif unidade == "kg":
                    unidade = "g"
                    qtd_num *= 1000

                # Agregar
                chave = nome_item.lower()
                itens_agregados[chave]["nome"] = nome_item
                itens_agregados[chave]["quantidade_total"] += qtd_num
                itens_agregados[chave]["unidade"] = unidade
                if nome_refeicao not in itens_agregados[chave]["refeicoes"]:
                    itens_agregados[chave]["refeicoes"].append(nome_refeicao)

    # Calcular quantidade final (x7 dias x pessoas)
    lista_final = []

    for chave, dados in itens_agregados.items():
        qtd_diaria = dados["quantidade_total"]
        qtd_semanal = qtd_diaria * multiplicador_dias * pessoas
        unidade = dados["unidade"]
        refeicoes_str = "+".join(dados["refeicoes"])

        # Formatar quantidade para unidades de mercado
        if unidade == "g":
            if qtd_semanal >= 1000:
                qtd_formatada = f"{qtd_semanal/1000:.1f}kg".replace(".0kg", "kg")
            else:
                qtd_formatada = f"{int(qtd_semanal)}g"
        elif unidade == "unidade":
            qtd_int = int(qtd_semanal)
            # Ovos: converter para dúzias
            if "ovo" in chave:
                duzias = qtd_int / 12
                if duzias <= 1:
                    qtd_formatada = "1 dúzia"
                else:
                    qtd_formatada = f"{int(round(duzias))} dúzias"
            else:
                qtd_formatada = f"{qtd_int} unidades"
        elif unidade == "pote":
            qtd_formatada = f"{int(qtd_semanal)} potes"
        elif unidade == "colher":
            # Azeite: converter para ml (1 colher ≈ 15ml)
            if "azeite" in chave or "óleo" in chave or "oleo" in chave:
                ml_total = qtd_semanal * 15
                if ml_total >= 500:
                    qtd_formatada = "1 litro"
                else:
                    qtd_formatada = "500ml"
            else:
                qtd_formatada = f"{int(qtd_semanal)} colheres"
        elif unidade == "fatia":
            qtd_formatada = f"{int(qtd_semanal)} fatias"
        elif unidade == "ml":
            if qtd_semanal >= 1000:
                qtd_formatada = f"{qtd_semanal/1000:.1f}L".replace(".0L", "L")
            else:
                qtd_formatada = f"{int(qtd_semanal)}ml"
        else:
            qtd_formatada = f"{int(qtd_semanal)} {unidade}"

        motivo = f"{refeicoes_str} ({qtd_diaria:.0f}/dia x {multiplicador_dias} x {pessoas})"

        lista_final.append({
            "nome": dados["nome"],
            "quantidade": qtd_formatada,
            "motivo": motivo
        })

        print(f"  - {dados['nome']}: {qtd_diaria}/dia × {multiplicador_dias} × {pessoas} = {qtd_formatada}")

    print(f"[CALC_PYTHON] Total: {len(lista_final)} itens\n")
    return lista_final


def gerar_lista_compras(dieta_final: dict):
    """
    Gera lista de compras usando cálculos em Python (confiável)
    Fallback para IA apenas se não tiver estrutura de refeições
    """
    print(f"\n[GERAR_LISTA] Gerando lista de compras...")

    # Mostrar estrutura
    if "refeicoes" in dieta_final and dieta_final["refeicoes"]:
        refeicoes = dieta_final.get("refeicoes", {})
        print(f"[GERAR_LISTA] Usando cálculo PYTHON (confiável)")
        print(f"  - Refeicoes: {len(refeicoes)}")
        for refeicao, itens in refeicoes.items():
            print(f"    - {refeicao}: {len(itens)} itens")

        # ✅ USAR CÁLCULO PYTHON - confiável e determinístico
        lista = calcular_quantidades_python(dieta_final)

        if lista:
            print(f"[GERAR_LISTA] Lista calculada: {len(lista)} itens")
            for i, item in enumerate(lista[:5], 1):
                print(f"  {i}. {item.get('nome', '?')} - {item.get('quantidade', '?')}")
            if len(lista) > 5:
                print(f"  ... e mais {len(lista) - 5} itens")
            return lista

    # Fallback: usar IA se não tiver estrutura de refeições
    print(f"[GERAR_LISTA] Fallback: usando OpenAI (sem estrutura de refeições)")
    print(f"  - Fixos: {len(dieta_final.get('fixos', []))} itens")
    print(f"  - Pessoas: {dieta_final.get('pessoas', 1)}")
    print(f"  - Dias: {dieta_final.get('dias', 1)}")

    dieta_json = json.dumps(dieta_final, ensure_ascii=False)

    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_COMPRA},
            {"role": "user", "content": dieta_json}
        ],
        temperature=0
    )

    resposta_ai = r.choices[0].message.content
    resposta_limpa = resposta_ai.strip()

    # Limpar markdown
    if resposta_limpa.startswith("```json"):
        resposta_limpa = resposta_limpa[7:]
    elif resposta_limpa.startswith("```"):
        resposta_limpa = resposta_limpa[3:]
    if resposta_limpa.endswith("```"):
        resposta_limpa = resposta_limpa[:-3]
    resposta_limpa = resposta_limpa.strip()

    # Encontrar início do JSON
    inicio_json = min(
        resposta_limpa.find('[') if resposta_limpa.find('[') != -1 else len(resposta_limpa),
        resposta_limpa.find('{') if resposta_limpa.find('{') != -1 else len(resposta_limpa)
    )
    if inicio_json > 0:
        resposta_limpa = resposta_limpa[inicio_json:]

    try:
        lista = json.loads(resposta_limpa)
        print(f"[GERAR_LISTA] Lista gerada via IA: {len(lista)} itens")
        return lista
    except Exception as e:
        print(f"[GERAR_LISTA ERRO] Falha ao parsear JSON: {e}")
        return []
