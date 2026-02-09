import os
import json
import re
from collections import defaultdict
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# =============================================================================
# CONFIGURAÇÃO: Categorias de alimentos para consolidação
# =============================================================================

# Proteínas ordenadas por PRIORIDADE (primeira = preferida)
PROTEINAS = [
    "frango", "peito de frango", "coxa", "sobrecoxa",
    "carne", "bife", "filé", "file", "alcatra", "patinho", "acém", "acem", "costela", "lombo",
    "peixe", "tilapia", "salmão", "salmon", "atum",
    "ovo", "ovos", "omelete", "omelette", "ovos mexidos",
    "proteina", "proteína"
]

# Carboidratos ordenados por PRIORIDADE
CARBOIDRATOS = [
    "arroz", "arroz integral", "arroz branco",
    "batata", "batata doce", "batata inglesa",
    "macarrão", "macarrao", "massa", "espaguete", "penne", "fusilli", "talharim",
    "mandioca", "inhame", "cará", "cara",
    "pão", "pao", "pão francês", "pao frances", "pão de forma", "pao de forma",
    "nhoque", "ao sugo",
    "carboidrato"
]

# Frutas
FRUTAS = [
    "banana", "maçã", "maca", "laranja", "mamão", "mamao", "melão", "melao",
    "melancia", "abacaxi", "manga", "uva", "morango", "kiwi", "pera", "pêra",
    "goiaba", "ameixa", "fruta"
]

# Padrões que indicam SUBSTITUIÇÃO/OPÇÃO (refeições a ignorar)
PALAVRAS_IGNORAR = [
    "substituição", "substituicao", "substitui",
    "alternativa", "alternativo",
    "opção", "opcao", "opcional",
    "variação", "variacao",
    "sugestão", "sugestao",
    "ou_", "_ou_", "opcao_", "alt_",
    "opção 1", "opcao 1", "opção 2", "opcao 2", "opção 3", "opcao 3",
    "option", "replace", "alternative", "swap"
]

# Tipos de refeição para agrupamento
TIPOS_REFEICAO = {
    "cafe": ["cafe", "café", "manha", "manhã", "breakfast", "desjejum"],
    "almoco": ["almoco", "almoço", "lunch", "meio dia", "meio-dia"],
    "lanche": ["lanche", "tarde", "snack", "pre treino", "pré treino", "pos treino", "pós treino"],
    "jantar": ["jantar", "janta", "dinner", "noite"],
    "ceia": ["ceia", "antes de dormir", "noturno"]
}


# =============================================================================
# PROMPT: Interpretação simples - apenas extrair alimentos
# =============================================================================

SYSTEM_INTERPRETACAO = """
Você é um extrator de dados de dietas. Sua função é APENAS extrair alimentos e quantidades.

FORMATO DE SAÍDA (JSON):
{
  "refeicoes": {
    "cafe_manha": [{"item": "nome do alimento", "quantidade": "quantidade"}],
    "almoco": [...],
    "lanche_tarde": [...],
    "jantar": [...],
    "ceia": [...]
  },
  "dias": 1
}

REGRAS SIMPLES:
1. Extraia TODOS os alimentos mencionados
2. Mantenha as quantidades exatas (ex: "150g", "2 unidades", "1 pote")
3. Use "a vontade" para itens sem quantidade especificada
4. Identifique refeições pelos nomes/horários
5. dias = 1 (dieta diária) ou 7 (dieta semanal completa)

⚠️ NÃO tente interpretar opções ou fazer escolhas. Apenas extraia os dados.
⚠️ Se houver "Frango ou Carne ou Peixe", extraia TODOS separadamente.
⚠️ O sistema vai processar e consolidar depois.
"""


# =============================================================================
# PROMPT: Chat com usuário
# =============================================================================

SYSTEM_CHAT = """
Você é um assistente AMIGÁVEL e EFICIENTE de compras.

🎯 OBJETIVO: Gerar a lista em NO MÁXIMO 2 interações!

FLUXO:
1️⃣ PRIMEIRA MENSAGEM:
   "Recebi sua dieta! Pra quantas pessoas é? (Se quiser, me diz também o que já tem em casa)"

2️⃣ SEGUNDA MENSAGEM:
   Usuário respondeu? GERE A LISTA!
   "Perfeito! Gerando sua lista... [LISTA_PRONTA]"

⚠️ NUNCA pergunte sobre preferência de alimentos (proteína, carboidrato, frutas)
⚠️ A dieta JÁ TEM tudo que precisa!
⚠️ Adicione [LISTA_PRONTA] quando for gerar.
"""


# =============================================================================
# FUNÇÕES PRINCIPAIS
# =============================================================================

def interpretar_dieta(texto: str) -> dict:
    """Interpreta dieta usando IA e aplica consolidação"""
    print(f"\n[AI_PARSER] Interpretando dieta ({len(texto)} caracteres)...")

    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_INTERPRETACAO},
            {"role": "user", "content": texto}
        ],
        temperature=0
    )

    resposta_ai = r.choices[0].message.content
    print(f"[AI_PARSER] Resposta da IA recebida")

    # Limpar resposta
    resultado = _parsear_json(resposta_ai)

    if not resultado:
        print("[AI_PARSER ERRO] Falha ao parsear JSON")
        return {"fixos": [], "escolhas": [], "dias": 1, "refeicoes": {}}

    # Contar itens antes
    total_antes = sum(len(itens) for itens in resultado.get("refeicoes", {}).values())
    print(f"[AI_PARSER] Itens extraídos: {total_antes}")

    # ✅ CONSOLIDAR: Aplicar regras de negócio
    resultado = consolidar_refeicoes(resultado)

    # Contar itens depois
    total_depois = sum(len(itens) for itens in resultado.get("refeicoes", {}).values())
    print(f"[AI_PARSER] Itens após consolidação: {total_depois}")

    # Gerar lista de fixos para compatibilidade
    resultado["fixos"] = _gerar_fixos(resultado)
    resultado["escolhas"] = []

    return resultado


def consolidar_refeicoes(dieta: dict) -> dict:
    """
    CONSOLIDAÇÃO ROBUSTA:
    1. Remove refeições que são substituições/opções
    2. Agrupa refeições por TIPO (café, almoço, lanche, jantar)
    3. Para cada tipo, mantém apenas 1 proteína, 1 carboidrato, 1 fruta
    """
    refeicoes = dieta.get("refeicoes", {})
    if not refeicoes:
        return dieta

    print(f"\n[CONSOLIDAR] Iniciando consolidação...")

    # PASSO 1: Filtrar refeições de substituição
    refeicoes_filtradas = {}
    for nome, itens in refeicoes.items():
        nome_lower = nome.lower()
        if any(palavra in nome_lower for palavra in PALAVRAS_IGNORAR):
            print(f"  - IGNORANDO '{nome}' (é substituição/opção)")
        else:
            refeicoes_filtradas[nome] = itens

    # PASSO 2: Agrupar por tipo de refeição
    refeicoes_por_tipo = defaultdict(list)
    for nome, itens in refeicoes_filtradas.items():
        tipo = _identificar_tipo_refeicao(nome)
        for item in itens:
            refeicoes_por_tipo[tipo].append(item)

    print(f"  - Tipos encontrados: {list(refeicoes_por_tipo.keys())}")

    # PASSO 3: Para cada tipo, consolidar categorias
    refeicoes_consolidadas = {}
    for tipo, itens in refeicoes_por_tipo.items():
        itens_consolidados = _consolidar_itens_refeicao(itens, tipo)
        refeicoes_consolidadas[tipo] = itens_consolidados

    dieta["refeicoes"] = refeicoes_consolidadas
    print(f"[CONSOLIDAR] Concluído\n")
    return dieta


def _consolidar_itens_refeicao(itens: list, nome_refeicao: str) -> list:
    """
    Consolida itens de uma refeição:
    - Mantém apenas 1 proteína (a primeira na ordem de prioridade)
    - Mantém apenas 1 carboidrato (o primeiro na ordem de prioridade)
    - Mantém apenas 1 fruta (a primeira)
    - Mantém todos os outros itens
    """
    proteinas = []
    carboidratos = []
    frutas = []
    outros = []

    for item in itens:
        nome_item = item.get("item", "").lower()
        categoria = _identificar_categoria(nome_item)

        if categoria == "proteina":
            proteinas.append(item)
        elif categoria == "carboidrato":
            carboidratos.append(item)
        elif categoria == "fruta":
            frutas.append(item)
        else:
            outros.append(item)

    resultado = outros.copy()

    # Proteína: escolher a de maior prioridade
    if proteinas:
        escolhida = _escolher_por_prioridade(proteinas, PROTEINAS)
        resultado.append(escolhida)
        if len(proteinas) > 1:
            print(f"    - {nome_refeicao}: {len(proteinas)} proteínas → '{escolhida.get('item')}'")

    # Carboidrato: escolher o de maior prioridade
    if carboidratos:
        escolhido = _escolher_por_prioridade(carboidratos, CARBOIDRATOS)
        resultado.append(escolhido)
        if len(carboidratos) > 1:
            print(f"    - {nome_refeicao}: {len(carboidratos)} carboidratos → '{escolhido.get('item')}'")

    # Fruta: escolher a primeira
    if frutas:
        resultado.append(frutas[0])
        if len(frutas) > 1:
            print(f"    - {nome_refeicao}: {len(frutas)} frutas → '{frutas[0].get('item')}'")

    return resultado


def _escolher_por_prioridade(itens: list, lista_prioridade: list) -> dict:
    """Escolhe o item com maior prioridade na lista"""
    melhor = itens[0]
    melhor_prioridade = 999

    for item in itens:
        nome = item.get("item", "").lower()
        for i, termo in enumerate(lista_prioridade):
            if termo in nome:
                if i < melhor_prioridade:
                    melhor_prioridade = i
                    melhor = item
                break

    return melhor


def _identificar_categoria(nome_item: str) -> str:
    """Identifica a categoria de um alimento"""
    nome_lower = nome_item.lower()

    for termo in PROTEINAS:
        if termo in nome_lower:
            return "proteina"

    for termo in CARBOIDRATOS:
        if termo in nome_lower:
            return "carboidrato"

    for termo in FRUTAS:
        if termo in nome_lower:
            return "fruta"

    return "outro"


def _identificar_tipo_refeicao(nome_refeicao: str) -> str:
    """Identifica o tipo de refeição pelo nome"""
    nome_lower = nome_refeicao.lower()

    for tipo, palavras in TIPOS_REFEICAO.items():
        if any(palavra in nome_lower for palavra in palavras):
            return tipo

    # Fallback: usar o nome original
    return nome_refeicao


def _gerar_fixos(resultado: dict) -> list:
    """Gera lista de fixos para compatibilidade com frontend"""
    fixos = []
    for refeicao, itens in resultado.get("refeicoes", {}).items():
        for item in itens:
            nome = item.get("item", "")
            qtd = item.get("quantidade", "")
            descricao = f"{nome} ({qtd}) - {refeicao}"
            if descricao not in fixos:
                fixos.append(descricao)
    return fixos


def _parsear_json(resposta: str) -> dict:
    """Parseia JSON de forma robusta"""
    resposta_limpa = resposta.strip()

    # Remover markdown
    if resposta_limpa.startswith("```json"):
        resposta_limpa = resposta_limpa[7:]
    elif resposta_limpa.startswith("```"):
        resposta_limpa = resposta_limpa[3:]
    if resposta_limpa.endswith("```"):
        resposta_limpa = resposta_limpa[:-3]
    resposta_limpa = resposta_limpa.strip()

    # Encontrar início do JSON
    inicio = min(
        resposta_limpa.find('[') if '[' in resposta_limpa else len(resposta_limpa),
        resposta_limpa.find('{') if '{' in resposta_limpa else len(resposta_limpa)
    )
    if inicio > 0:
        resposta_limpa = resposta_limpa[inicio:]

    try:
        return json.loads(resposta_limpa)
    except:
        return None


# =============================================================================
# CHAT COM USUÁRIO
# =============================================================================

def conversar_com_usuario(dieta: dict, historico: list) -> str:
    """Conversa com usuário para coletar informações"""
    messages = [
        {"role": "system", "content": SYSTEM_CHAT},
        {"role": "user", "content": f"Dieta: {json.dumps(dieta, ensure_ascii=False)}"}
    ]
    messages.extend(historico)

    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.3
    )

    return r.choices[0].message.content


# =============================================================================
# CÁLCULO DE QUANTIDADES (em Python, não depende da IA)
# =============================================================================

def calcular_quantidades(dieta: dict) -> list:
    """
    Calcula quantidades de compras usando Python.
    IMPORTANTE: Aplica consolidação novamente antes de calcular!
    """
    # ✅ GARANTIR que consolidação foi aplicada
    dieta = consolidar_refeicoes(dieta)

    refeicoes = dieta.get("refeicoes", {})
    dias = dieta.get("dias", 1)
    pessoas = dieta.get("pessoas", 1)
    alimentos_em_casa = [a.lower() for a in dieta.get("alimentos_em_casa", [])]

    # Se dias=1, é dieta diária, multiplicar por 7
    multiplicador = 7 if dias == 1 else dias

    print(f"\n[CALC] Calculando: {multiplicador} dias × {pessoas} pessoas")

    # Agregar quantidades
    agregado = defaultdict(lambda: {"qtd": 0, "unidade": "", "refeicoes": []})

    for nome_refeicao, itens in refeicoes.items():
        for item in itens:
            nome = item.get("item", "").strip()
            qtd_str = item.get("quantidade", "").strip().lower()

            if not nome or qtd_str in ["a vontade", "à vontade", ""]:
                continue

            # Verificar se já tem em casa
            if any(casa in nome.lower() for casa in alimentos_em_casa):
                print(f"  - Pulando {nome} (já tem em casa)")
                continue

            # Extrair número e unidade
            qtd_num, unidade = _extrair_quantidade(qtd_str)
            if qtd_num == 0:
                continue

            chave = nome.lower()
            agregado[chave]["nome"] = nome
            agregado[chave]["qtd"] += qtd_num
            agregado[chave]["unidade"] = unidade
            if nome_refeicao not in agregado[chave]["refeicoes"]:
                agregado[chave]["refeicoes"].append(nome_refeicao)

    # Calcular final
    lista = []
    for chave, dados in agregado.items():
        qtd_diaria = dados["qtd"]
        qtd_final = qtd_diaria * multiplicador * pessoas
        unidade = dados["unidade"]

        qtd_formatada = _formatar_quantidade(chave, qtd_final, unidade)
        motivo = f"{'+'.join(dados['refeicoes'])} ({qtd_diaria:.0f}/dia × {multiplicador} × {pessoas})"

        lista.append({
            "nome": dados["nome"],
            "quantidade": qtd_formatada,
            "motivo": motivo
        })

        print(f"  - {dados['nome']}: {qtd_formatada}")

    print(f"[CALC] Total: {len(lista)} itens\n")
    return lista


def _extrair_quantidade(qtd_str: str) -> tuple:
    """Extrai número e unidade de uma string de quantidade"""
    match = re.search(r'(\d+\.?\d*)\s*(g|kg|ml|l|unidade|unidades|pote|potes|colher|colheres|fatia|fatias)?', qtd_str)
    if not match:
        return 0, "unidade"

    qtd = float(match.group(1))
    unidade = match.group(2) or "unidade"

    # Normalizar
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
        qtd *= 1000
    elif unidade == "kg":
        unidade = "g"
        qtd *= 1000

    return qtd, unidade


def _formatar_quantidade(nome: str, qtd: float, unidade: str) -> str:
    """Formata quantidade para unidades de mercado"""
    nome_lower = nome.lower()

    if unidade == "g":
        if qtd >= 1000:
            return f"{qtd/1000:.1f}kg".replace(".0kg", "kg")
        return f"{int(qtd)}g"

    elif unidade == "unidade":
        qtd_int = int(qtd)
        if "ovo" in nome_lower:
            duzias = qtd_int / 12
            if duzias <= 1:
                return "1 dúzia"
            return f"{int(round(duzias))} dúzias"
        return f"{qtd_int} unidades"

    elif unidade == "pote":
        return f"{int(qtd)} potes"

    elif unidade == "colher":
        if "azeite" in nome_lower or "óleo" in nome_lower or "oleo" in nome_lower:
            ml = qtd * 15
            return "1 litro" if ml >= 500 else "500ml"
        return f"{int(qtd)} colheres"

    elif unidade == "fatia":
        return f"{int(qtd)} fatias"

    elif unidade == "ml":
        if qtd >= 1000:
            return f"{qtd/1000:.1f}L".replace(".0L", "L")
        return f"{int(qtd)}ml"

    return f"{int(qtd)} {unidade}"


# =============================================================================
# FUNÇÃO PRINCIPAL: Gerar lista de compras
# =============================================================================

def gerar_lista_compras(dieta_final: dict) -> list:
    """Gera lista de compras usando cálculos em Python"""
    print(f"\n[GERAR_LISTA] Iniciando...")

    if "refeicoes" in dieta_final and dieta_final["refeicoes"]:
        return calcular_quantidades(dieta_final)

    # Fallback: dieta sem estrutura de refeições
    print("[GERAR_LISTA] AVISO: Dieta sem estrutura de refeições")
    return []
