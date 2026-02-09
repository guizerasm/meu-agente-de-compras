import os
import json
import re
from collections import defaultdict
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# =============================================================================
# CONFIGURAÇÃO: Categorias de alimentos
# =============================================================================

PROTEINAS = [
    "frango", "peito de frango", "coxa", "sobrecoxa",
    "carne", "bife", "filé", "file", "alcatra", "patinho", "acém", "acem",
    "costela", "lombo", "maminha", "lagarto", "coxão", "mignon",
    "peixe", "tilapia", "tilápia", "salmão", "salmon", "atum", "pescada",
    "ovo", "ovos", "omelete",
    "lombo suíno", "lombo suino"
]

CARBOIDRATOS = [
    "arroz", "batata", "macarrão", "macarrao", "massa", "espaguete",
    "penne", "fusilli", "talharim", "nhoque",
    "mandioca", "inhame", "cará", "cara",
    "pão", "pao"
]

FRUTAS = [
    "banana", "maçã", "maca", "laranja", "mamão", "mamao", "melão", "melao",
    "melancia", "abacaxi", "manga", "uva", "morango", "kiwi", "pera", "pêra",
    "goiaba", "ameixa", "caqui", "mexerica", "jabuticaba", "pêssego", "pessego",
    "maracujá", "maracuja", "abacate"
]

# Palavras que indicam SUBSTITUIÇÃO (ignorar completamente)
PALAVRAS_SUBSTITUICAO = [
    "substituição", "substituicao", "substitui",
    "alternativa", "alternativo",
    "opção", "opcao",
    "variação", "variacao"
]


# =============================================================================
# PROMPT: Extração de dados
# =============================================================================

SYSTEM_INTERPRETACAO = """
Você é um extrator de dados de dietas nutricionais.

FORMATO DE SAÍDA (JSON):
{
  "refeicoes": {
    "cafe_manha": [{"item": "Pão francês", "quantidade": "1 unidade"}, ...],
    "almoco": [...],
    "lanche_tarde": [...],
    "jantar": [...],
    "ceia": [...]
  },
  "dias": 1
}

REGRAS IMPORTANTES:
1. Extraia apenas as REFEIÇÕES PRINCIPAIS (café, almoço, lanche, jantar, ceia)
2. IGNORE completamente seções chamadas "Substituição 1", "Substituição 2", etc.
3. Quando houver "X ou Y ou Z", pegue apenas o PRIMEIRO item (X)
4. Mantenha quantidades exatas: "150g", "2 unidades", "1 pote"
5. dias = 1 para dieta diária

EXEMPLO:
"pão francês (1 unidade) ou pão integral (2 fatias)" → {"item": "Pão francês", "quantidade": "1 unidade"}
"Frango (150g) ou Carne (140g)" → {"item": "Frango", "quantidade": "150g"}

⚠️ NUNCA inclua itens de seções "Substituição"!
"""


SYSTEM_CHAT = """
Você é um assistente de compras. Seja BREVE e DIRETO.

PRIMEIRA MENSAGEM:
"Recebi sua dieta! Pra quantas pessoas é a compra?"

DEPOIS QUE O USUÁRIO RESPONDER:
Diga apenas: "Perfeito! Clique em 'Finalizar' para gerar sua lista de compras. [LISTA_PRONTA]"

⚠️ REGRAS CRÍTICAS:
- NUNCA liste os alimentos no chat
- NUNCA gere uma lista de compras
- NUNCA mencione quantidades
- Apenas diga [LISTA_PRONTA] para o sistema gerar a lista
- O botão "Finalizar" vai gerar a lista automaticamente
"""


# =============================================================================
# INTERPRETAÇÃO DA DIETA
# =============================================================================

def interpretar_dieta(texto: str) -> dict:
    """Interpreta dieta usando IA"""
    print(f"\n[INTERPRETAR] Processando {len(texto)} caracteres...")

    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_INTERPRETACAO},
            {"role": "user", "content": texto}
        ],
        temperature=0
    )

    resposta = r.choices[0].message.content
    resultado = _parsear_json(resposta)

    if not resultado:
        print("[ERRO] Falha ao parsear JSON da IA")
        return {"fixos": [], "escolhas": [], "dias": 1, "refeicoes": {}}

    # Filtrar refeições de substituição
    resultado = _filtrar_substituicoes(resultado)

    # Gerar fixos para compatibilidade
    resultado["fixos"] = _gerar_fixos(resultado)
    resultado["escolhas"] = []

    # Log
    total = sum(len(itens) for itens in resultado.get("refeicoes", {}).values())
    print(f"[INTERPRETAR] {total} itens em {len(resultado.get('refeicoes', {}))} refeições")

    return resultado


def _filtrar_substituicoes(dieta: dict) -> dict:
    """Remove refeições que são substituições"""
    refeicoes = dieta.get("refeicoes", {})

    refeicoes_filtradas = {}
    for nome, itens in refeicoes.items():
        nome_lower = nome.lower()
        eh_substituicao = any(p in nome_lower for p in PALAVRAS_SUBSTITUICAO)

        if eh_substituicao:
            print(f"  [FILTRO] Ignorando '{nome}' (substituição)")
        else:
            refeicoes_filtradas[nome] = itens

    dieta["refeicoes"] = refeicoes_filtradas
    return dieta


def _gerar_fixos(resultado: dict) -> list:
    """Gera lista de fixos para compatibilidade"""
    fixos = []
    for refeicao, itens in resultado.get("refeicoes", {}).items():
        for item in itens:
            nome = item.get("item", "")
            qtd = item.get("quantidade", "")
            fixos.append(f"{nome} ({qtd}) - {refeicao}")
    return fixos


def _parsear_json(resposta: str) -> dict:
    """Parseia JSON de forma robusta"""
    resposta = resposta.strip()

    # Remover markdown
    if "```json" in resposta:
        resposta = resposta.split("```json")[1].split("```")[0]
    elif "```" in resposta:
        resposta = resposta.split("```")[1].split("```")[0]

    # Encontrar JSON
    inicio = resposta.find("{")
    if inicio >= 0:
        resposta = resposta[inicio:]

    try:
        return json.loads(resposta)
    except:
        print(f"[ERRO] JSON inválido: {resposta[:200]}")
        return None


# =============================================================================
# CHAT COM USUÁRIO
# =============================================================================

def conversar_com_usuario(dieta: dict, historico: list) -> str:
    """Conversa com usuário"""
    messages = [
        {"role": "system", "content": SYSTEM_CHAT},
        {"role": "user", "content": f"Dieta do usuário: {json.dumps(dieta, ensure_ascii=False)[:500]}"}
    ]
    messages.extend(historico)

    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.3
    )

    return r.choices[0].message.content


# =============================================================================
# CÁLCULO DE QUANTIDADES (100% Python)
# =============================================================================

def gerar_lista_compras(dieta: dict) -> list:
    """
    Gera lista de compras com cálculos em Python.

    Lógica:
    1. Soma todas as quantidades por item (agregando por nome)
    2. Multiplica por 7 dias
    3. Multiplica por número de pessoas
    """
    refeicoes = dieta.get("refeicoes", {})
    dias = dieta.get("dias", 1)
    pessoas = dieta.get("pessoas", 1)
    alimentos_em_casa = [a.lower() for a in dieta.get("alimentos_em_casa", [])]

    # Se dias=1, é dieta DIÁRIA, multiplicar por 7 para semana
    multiplicador_dias = 7 if dias == 1 else dias

    print(f"\n[CALC] Gerando lista de compras...")
    print(f"  - Dias informados: {dias} → multiplicador: {multiplicador_dias}")
    print(f"  - Pessoas: {pessoas}")
    print(f"  - Refeições: {list(refeicoes.keys())}")

    # Agregar quantidades por item
    agregado = defaultdict(lambda: {"qtd": 0, "unidade": "", "refeicoes": set()})

    for nome_refeicao, itens in refeicoes.items():
        print(f"  - {nome_refeicao}: {len(itens)} itens")

        for item in itens:
            nome_item = item.get("item", "").strip()
            qtd_str = item.get("quantidade", "").strip().lower()

            if not nome_item:
                continue

            # Pular "a vontade"
            if "vontade" in qtd_str or not qtd_str:
                continue

            # Verificar se já tem em casa
            if any(casa in nome_item.lower() for casa in alimentos_em_casa):
                continue

            # Extrair número e unidade
            qtd_num, unidade = _extrair_quantidade(qtd_str)

            # Agregar
            chave = nome_item.lower()
            agregado[chave]["nome"] = nome_item
            agregado[chave]["qtd"] += qtd_num
            agregado[chave]["unidade"] = unidade
            agregado[chave]["refeicoes"].add(nome_refeicao)

    # Calcular quantidade final
    lista = []

    print(f"\n[CALC] Calculando quantidades finais:")

    for chave, dados in agregado.items():
        qtd_diaria = dados["qtd"]
        qtd_semanal = qtd_diaria * multiplicador_dias * pessoas
        unidade = dados["unidade"]

        qtd_formatada = _formatar_quantidade(chave, qtd_semanal, unidade)
        refeicoes_list = list(dados["refeicoes"])

        motivo = f"{'+'.join(refeicoes_list)} ({qtd_diaria:.0f}/dia × {multiplicador_dias} dias × {pessoas} pessoa(s))"

        lista.append({
            "nome": dados["nome"],
            "quantidade": qtd_formatada,
            "motivo": motivo
        })

        print(f"  - {dados['nome']}: {qtd_diaria}/dia × {multiplicador_dias} × {pessoas} = {qtd_formatada}")

    print(f"\n[CALC] Lista gerada: {len(lista)} itens")
    return lista


def _extrair_quantidade(qtd_str: str) -> tuple:
    """Extrai número e unidade"""
    qtd_str = qtd_str.lower().strip()

    # Padrões comuns
    match = re.search(r'(\d+\.?\d*)\s*(g|kg|ml|l|unidade|unidades|pote|potes|colher|colheres|fatia|fatias|grama)?', qtd_str)

    if not match:
        # Tentar pegar só o número
        match_num = re.search(r'(\d+)', qtd_str)
        if match_num:
            return float(match_num.group(1)), "unidade"
        return 0, "unidade"

    qtd = float(match.group(1))
    unidade = match.group(2) or "unidade"

    # Normalizar
    if unidade in ["unidades", "grama"]:
        unidade = "unidade" if "unidades" in unidade else "g"
    if unidade == "grama":
        unidade = "g"
    if unidade in ["potes"]:
        unidade = "pote"
    if unidade in ["colheres"]:
        unidade = "colher"
    if unidade in ["fatias"]:
        unidade = "fatia"
    if unidade == "l":
        unidade = "ml"
        qtd *= 1000
    if unidade == "kg":
        unidade = "g"
        qtd *= 1000

    return qtd, unidade


def _formatar_quantidade(nome: str, qtd: float, unidade: str) -> str:
    """Formata quantidade para exibição"""
    nome_lower = nome.lower()

    if unidade == "g":
        if qtd >= 1000:
            kg = qtd / 1000
            return f"{kg:.1f}kg".replace(".0kg", "kg")
        return f"{int(qtd)}g"

    if unidade == "unidade":
        qtd_int = int(round(qtd))
        if "ovo" in nome_lower:
            duzias = qtd_int / 12
            if duzias <= 1:
                return "1 dúzia"
            return f"{int(round(duzias))} dúzias"
        return f"{qtd_int} unidades"

    if unidade == "pote":
        return f"{int(round(qtd))} potes"

    if unidade == "colher":
        if "azeite" in nome_lower:
            ml = qtd * 15
            return "1 litro" if ml >= 500 else "500ml"
        return f"{int(qtd)} colheres"

    if unidade == "fatia":
        return f"{int(qtd)} fatias"

    if unidade == "ml":
        if qtd >= 1000:
            return f"{qtd/1000:.1f}L".replace(".0L", "L")
        return f"{int(qtd)}ml"

    return f"{int(qtd)} {unidade}"
