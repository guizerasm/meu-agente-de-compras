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
    "substituição", "substituicao", "substitui", "substituir",
    "alternativa", "alternativo",
    "opção", "opcao", "opcion",
    "variação", "variacao",
    "troca", "trocar",
    "ou_então", "ou_entao",
    "_sub", "_alt", "_var", "_opt",
    "opcao_", "opção_",
    "substituicao_", "substituição_",
]


# =============================================================================
# PROMPT: Extração de dados
# =============================================================================

SYSTEM_INTERPRETACAO = """
Você é um extrator especializado de dietas nutricionais brasileiras. Sua tarefa é ler a dieta e retornar um JSON estruturado com as refeições e quantidades.

## FORMATO DE SAÍDA (JSON obrigatório):
{
  "refeicoes": {
    "cafe_manha": [{"item": "Nome do alimento", "quantidade": "valor normalizado"}, ...],
    "lanche_manha": [...],
    "almoco": [...],
    "lanche_tarde": [...],
    "jantar": [...],
    "ceia": [...]
  },
  "dias": 1
}

## MAPEAMENTO DE REFEIÇÕES
Mapeie qualquer variação para as chaves corretas:
- "Café da manhã", "Desjejum", "Pequeno-almoço" → cafe_manha
- "Lanche da manhã", "Colação", "Lanche matinal" → lanche_manha
- "Almoço", "Refeição 1", "Refeição principal" → almoco
- "Lanche da tarde", "Lanche", "Lanche vespertino", "Colação da tarde", "Pré-treino", "Pós-treino" → lanche_tarde
- "Jantar", "Refeição noturna", "Refeição 2" → jantar
- "Ceia", "Lanche noturno", "Antes de dormir" → ceia

## NORMALIZAÇÃO DE QUANTIDADES (CRÍTICO)
Converta SEMPRE para estes formatos antes de retornar:

| Entrada | Retornar |
|---|---|
| 150g, 150 gramas, cento e cinquenta gramas | "150g" |
| 1kg, 1 quilo | "1000g" |
| 200ml, 200 mililitros | "200ml" |
| 1 copo (200ml), 1 copo de água | "200ml" |
| 1 xícara, 1 xic. | "1 xicara" |
| 1/2 xícara, meia xícara | "0.5 xicara" |
| 1 colher de sopa, 1 cs, 1 C.S. | "1 colher_sopa" |
| 1 colher de chá, 1 cc, 1 C.C. | "1 colher_cha" |
| 1 unidade, 1 un, 1 und, 1 uni | "1 unidade" |
| 2 fatias, 2 fts | "2 fatias" |
| 1 pote, 1 pote pequeno | "1 pote" |
| 1 lata | "1 lata" |
| 1 sachê, 1 sache, 1 envelope | "1 sache" |
| 1 caixa | "1 caixa" |
| 1 pacote | "1 pacote" |
| 1 concha, 2 conchas | "100g" por concha (1 concha = 100g) |
| 150-200g (range) | "200g" (pegar o MAIOR valor) |
| "meia" + unidade | "0.5 " + unidade |
| "um quarto de" | "0.25 " + unidade |

## REGRAS DE EXTRAÇÃO

1. **IGNORE completamente** qualquer seção ou bloco que contenha estas palavras no título: "Substituição", "Substituto", "Alternativa", "Opção", "Variação", "OU ENTÃO", "Troca", "Pode trocar por". Isso inclui:
   - Seções separadas: "Substituição 1:", "Substituição do almoço:", "Alternativas:"
   - Sub-blocos dentro de uma refeição
   - Tabelas com "Opção 1 / Opção 2" → use APENAS a Opção 1
   - Qualquer texto após "Pode substituir por", "Ou trocar por", "Alternativa:"
   Se ficar em dúvida, NÃO inclua o item.

2. **Quando houver "X ou Y" / "X / Y"**: pegue APENAS o PRIMEIRO item (X), NUNCA inclua os demais. Exemplos:
   - "Frango (150g) ou Carne (140g) ou Peixe (120g)" → APENAS Frango, 150g
   - "Pão francês / Tapioca / Cuscuz" → APENAS Pão francês
   - "1 fruta (banana, maçã ou pera)" → APENAS Banana, 1 unidade

3. **Alimentos "à vontade" / "livre" / "sem restrição"**: inclua com quantidade "a vontade" (o sistema vai ignorar automaticamente).

4. **Suplementos e temperos**: inclua normalmente (whey, creatina, azeite, sal, etc.) com suas quantidades.

5. **dias**:
   - Dieta DIÁRIA (mesmo cardápio todo dia): use dias=1. NÃO inclua campo "vezes".
   - Dieta SEMANAL (dias diferentes): use dias=7. Inclua TODOS os itens únicos de TODOS os dias, com campo `"vezes": X` indicando em quantos dias da semana aquele item aparece naquela refeição.
   Exemplo de dieta semanal: "Seg: arroz+frango. Ter: macarrão+carne. Qua: arroz+peixe. Qui-Dom: repetir Seg"
   → almoco: [
       {"item": "Arroz", "quantidade": "4 colher_sopa", "estimado": true, "vezes": 6},
       {"item": "Frango", "quantidade": "150g", "estimado": true, "vezes": 5},
       {"item": "Macarrão", "quantidade": "100g", "estimado": true, "vezes": 1},
       {"item": "Carne", "quantidade": "150g", "estimado": true, "vezes": 1},
       {"item": "Peixe", "quantidade": "150g", "estimado": true, "vezes": 1}
   ]
   Contagem: Seg=1, Ter=1, Qua=1, Qui=rep Seg, Sex=rep Seg, Sab=rep Seg, Dom=rep Seg → arroz: Seg+Qua+Qui+Sex+Sab+Dom=6, frango: Seg+Qui+Sex+Sab+Dom=5

6. **Não invente itens**: extraia apenas o que está escrito. **SEMPRE retorne os nomes dos alimentos em PORTUGUÊS**, mesmo que o input esteja em inglês (eggs → Ovo, chicken breast → Peito de frango, sweet potato → Batata doce, milk → Leite, peanut butter → Pasta de amendoim, casein → Caseína).

8. **NUNCA crie refeições duplicadas ou numeradas**. Use APENAS estas chaves: cafe_manha, lanche_manha, almoco, lanche_tarde, jantar, ceia. Se houver "Substituição do Almoço" ou "Almoço 2" ou "Opção 2 do Almoço", IGNORE completamente — não crie chaves como "almoco_2", "almoco_sub", "jantar_alternativo", etc.

7. **Quando a quantidade NÃO está especificada**: use porções padrão brasileiras e marque com `"estimado": true`:
   - Proteínas (frango, carne, peixe, bife): "150g"
   - Arroz: "4 colher_sopa"
   - Feijão: "100g"
   - Pão: "1 unidade"
   - Fruta (banana, maçã, etc.): "1 unidade"
   - Ovo: "1 unidade"
   - Leite: "200ml"
   - Iogurte: "1 pote"
   - Azeite: "1 colher_sopa"
   - Manteiga/margarina/requeijão: "10g"
   - Salada/alface/folhas/legumes: "100g"
   - Sopa (qualquer): "400ml"
   - Whey/suplemento: "30g"
   - Aveia: "2 colher_sopa"
   - Queijo: "30g"
   - Castanhas/nozes/amendoim: "30g"
   - Outros: "1 unidade"
   Exemplo: {"item": "Frango", "quantidade": "150g", "estimado": true}

## EXEMPLOS REAIS

Entrada:
"Café da manhã: Pão francês (1 unidade) + Ovo mexido (2 ovos) + Café com leite (200ml)"

Saída:
{"cafe_manha": [
  {"item": "Pão francês", "quantidade": "1 unidade"},
  {"item": "Ovo", "quantidade": "2 unidades"},
  {"item": "Leite", "quantidade": "200ml"}
]}

---

Entrada:
"ALMOÇO: Arroz (4 colheres de sopa) / Feijão (2 conchas) / Frango grelhado (150g a 180g) / Salada à vontade"

Saída:
{"almoco": [
  {"item": "Arroz", "quantidade": "4 colher_sopa"},
  {"item": "Feijão", "quantidade": "200g"},
  {"item": "Frango grelhado", "quantidade": "180g"},
  {"item": "Salada", "quantidade": "a vontade"}
]}

---

Entrada:
"Lanche: 1 fruta média (banana, maçã ou pera) + Whey protein (1 scoop/30g)"

Saída:
{"lanche_tarde": [
  {"item": "Banana", "quantidade": "1 unidade"},
  {"item": "Whey protein", "quantidade": "30g"}
]}

---

Entrada (dieta complexa com substituições - IGNORAR substitutos):
"Almoço:
Arroz (4 colheres de sopa)
Feijão (1 concha)
Frango grelhado (150g) ou Carne moída (140g) ou Peixe (120g)
Salada verde à vontade
Azeite (1 colher de sopa)

Substituição do Almoço:
Macarrão integral (100g)
Atum (1 lata)
Legumes refogados (150g)"

Saída CORRETA:
{"almoco": [
  {"item": "Arroz", "quantidade": "4 colher_sopa"},
  {"item": "Feijão", "quantidade": "100g"},
  {"item": "Frango grelhado", "quantidade": "150g"},
  {"item": "Salada verde", "quantidade": "a vontade"},
  {"item": "Azeite", "quantidade": "1 colher_sopa"}
]}
(Carne moída, Peixe e toda a "Substituição do Almoço" foram IGNORADOS)

⚠️ Retorne APENAS o JSON, sem explicações, sem markdown.
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
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": SYSTEM_INTERPRETACAO},
            {"role": "user", "content": texto}
        ]
    )

    resposta = r.choices[0].message.content
    resultado = _parsear_json(resposta)

    if not resultado:
        print("[ERRO] Falha ao parsear JSON da IA")
        return {"fixos": [], "escolhas": [], "dias": 1, "refeicoes": {}}

    # Filtrar refeições com nomes fora da lista permitida
    resultado = _filtrar_refeicoes_invalidas(resultado)

    # Filtrar refeições de substituição (por nome da refeição)
    resultado = _filtrar_substituicoes(resultado)

    # Filtrar duplicatas de proteína/carboidrato por refeição (última linha de defesa)
    # NÃO filtrar em dietas semanais — múltiplas proteínas/carbs representam dias diferentes
    if resultado.get("dias", 1) == 1:
        resultado = _filtrar_duplicatas_por_categoria(resultado)

    # Detectar itens com quantidades estimadas
    itens_estimados = []
    for refeicao, itens in resultado.get("refeicoes", {}).items():
        for item in itens:
            if item.get("estimado"):
                itens_estimados.append(item.get("item", ""))
                del item["estimado"]  # limpar flag, não precisa ir pro frontend

    if itens_estimados:
        resultado["tem_estimativas"] = True
        resultado["itens_estimados"] = itens_estimados
        print(f"[INTERPRETAR] {len(itens_estimados)} itens com quantidade estimada: {itens_estimados}")

    # Gerar fixos para compatibilidade
    resultado["fixos"] = _gerar_fixos(resultado)
    resultado["escolhas"] = []

    # Log
    total = sum(len(itens) for itens in resultado.get("refeicoes", {}).values())
    print(f"[INTERPRETAR] {total} itens em {len(resultado.get('refeicoes', {}))} refeições")

    return resultado


REFEICOES_PERMITIDAS = {
    "cafe_manha", "lanche_manha", "almoco",
    "lanche_tarde", "jantar", "ceia",
}

# Mapeamento de refeições extras para a refeição permitida mais próxima
MAPEAMENTO_REFEICOES = {
    # Pré/pós treino
    "pre_treino": "lanche_tarde",
    "pos_treino": "lanche_tarde",
    "pre treino": "lanche_tarde",
    "pos treino": "lanche_tarde",
    "treino": "lanche_tarde",
    # Variações de lanche
    "lanche_noturno": "ceia",
    "lanche_noite": "ceia",
    "lanche_1": "lanche_manha",
    "lanche_2": "lanche_tarde",
    "lanche": "lanche_tarde",
    # Variações de refeições
    "desjejum": "cafe_manha",
    "colacao": "lanche_manha",
    "refeicao_1": "almoco",
    "refeicao_2": "jantar",
    "refeicao_3": "ceia",
    "antes_de_dormir": "ceia",
    "refeicao_noturna": "ceia",
}


def _filtrar_refeicoes_invalidas(dieta: dict) -> dict:
    """Normaliza refeições fora da lista permitida: mapeia para a mais próxima
    ou remove se for substituição/duplicata."""
    refeicoes = dieta.get("refeicoes", {})
    filtradas = {}

    for nome, itens in refeicoes.items():
        if nome in REFEICOES_PERMITIDAS:
            filtradas.setdefault(nome, []).extend(itens)
        elif nome in MAPEAMENTO_REFEICOES:
            destino = MAPEAMENTO_REFEICOES[nome]
            print(f"  [MAPEAMENTO] '{nome}' → '{destino}'")
            filtradas.setdefault(destino, []).extend(itens)
        elif _tentar_mapear_por_similaridade(nome):
            destino = _tentar_mapear_por_similaridade(nome)
            print(f"  [MAPEAMENTO] '{nome}' → '{destino}' (por similaridade)")
            filtradas.setdefault(destino, []).extend(itens)
        else:
            print(f"  [FILTRO] Removendo refeição '{nome}' (não reconhecida)")

    dieta["refeicoes"] = filtradas
    return dieta


def _tentar_mapear_por_similaridade(nome: str) -> str:
    """Tenta mapear uma refeição desconhecida para a permitida mais próxima.
    Retorna string vazia se for provável substituição (numerada)."""
    nome_lower = nome.lower()

    # Refeições numeradas são substituições — NÃO mapear
    if re.search(r'_\d+$|\d+$', nome_lower):
        return ""

    # Detecção por palavras-chave
    mapa_palavras = {
        "cafe": "cafe_manha",
        "manha": "lanche_manha",
        "almoco": "almoco",
        "tarde": "lanche_tarde",
        "treino": "lanche_tarde",
        "jantar": "jantar",
        "noite": "ceia",
        "ceia": "ceia",
        "dormir": "ceia",
    }

    for palavra, destino in mapa_palavras.items():
        if palavra in nome_lower:
            return destino

    return ""


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


def _filtrar_duplicatas_por_categoria(dieta: dict) -> dict:
    """Remove duplicatas de proteína/carboidrato na mesma refeição.
    Se a IA incluiu 'Frango' E 'Carne' E 'Peixe' no almoço,
    mantém apenas o primeiro de cada categoria."""
    refeicoes = dieta.get("refeicoes", {})

    for nome_refeicao, itens in refeicoes.items():
        proteina_encontrada = False
        carboidrato_encontrado = False
        itens_filtrados = []

        for item in itens:
            nome_item = item.get("item", "").lower()

            eh_proteina = any(p in nome_item for p in PROTEINAS)
            eh_carboidrato = any(c in nome_item for c in CARBOIDRATOS)

            if eh_proteina:
                if proteina_encontrada:
                    print(f"  [DUPLICATA] Removendo '{item.get('item')}' de {nome_refeicao} (proteína duplicada)")
                    continue
                proteina_encontrada = True

            if eh_carboidrato:
                if carboidrato_encontrado:
                    print(f"  [DUPLICATA] Removendo '{item.get('item')}' de {nome_refeicao} (carboidrato duplicado)")
                    continue
                carboidrato_encontrado = True

            itens_filtrados.append(item)

        refeicoes[nome_refeicao] = itens_filtrados

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
        model="gpt-5-mini",
        messages=messages
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

    # Se dias=1, é dieta DIÁRIA → multiplicar por 7 para completar a semana
    # Se dias=7, é dieta SEMANAL → IA já somou todos os dias, não multiplicar
    multiplicador_dias = 7 if dias == 1 else 1

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

            # Para dietas semanais, multiplicar pela frequência (vezes/semana)
            vezes = item.get("vezes", 1)

            # Agregar (normalizar nome para agrupar variações)
            # Incluir unidade na chave para NÃO misturar g com unidade
            # (ex: "banana|g" separado de "banana|unidade")
            nome_norm = _normalizar_nome_item(nome_item)
            chave = f"{nome_norm}|{unidade}"
            # Manter o nome mais curto como display name
            if "nome" not in agregado[chave] or len(nome_item) < len(agregado[chave]["nome"]):
                agregado[chave]["nome"] = nome_item
            agregado[chave]["qtd"] += qtd_num * vezes
            agregado[chave]["unidade"] = unidade
            agregado[chave]["refeicoes"].add(nome_refeicao)

    # Mesclar entradas do mesmo item com unidades diferentes (g → unidade)
    # Ex: "banana|g" (80g) + "banana|unidade" (2 un) → "banana|unidade" (3 un)
    PESO_MEDIO_FRUTA = {
        "banana": 80, "maçã": 150, "laranja": 180, "mexerica": 120,
        "manga": 300, "goiaba": 150, "pêra": 170, "pêssego": 130,
        "kiwi": 80, "caqui": 170, "ameixa": 50, "maracujá": 120,
    }
    nomes_no_agregado = set(k.split("|")[0] for k in agregado)
    for nome_norm in nomes_no_agregado:
        chave_g = f"{nome_norm}|g"
        chave_un = f"{nome_norm}|unidade"
        if chave_g in agregado and chave_un in agregado:
            peso = PESO_MEDIO_FRUTA.get(nome_norm)
            if peso:
                # Converter gramas para unidades e somar
                qtd_g = agregado[chave_g]["qtd"]
                qtd_em_un = qtd_g / peso
                agregado[chave_un]["qtd"] += qtd_em_un
                agregado[chave_un]["refeicoes"].update(agregado[chave_g]["refeicoes"])
                # Manter o nome mais curto
                if len(agregado[chave_g].get("nome", "")) < len(agregado[chave_un].get("nome", "")):
                    agregado[chave_un]["nome"] = agregado[chave_g]["nome"]
                print(f"  [MERGE] {nome_norm}: {qtd_g}g → {qtd_em_un:.1f} un (peso médio {peso}g)")
                del agregado[chave_g]

    # Calcular quantidade final
    lista = []

    print(f"\n[CALC] Calculando quantidades finais:")

    for chave, dados in agregado.items():
        qtd_diaria = dados["qtd"]
        qtd_semanal = qtd_diaria * multiplicador_dias * pessoas
        unidade = dados["unidade"]

        # Chave é "nome|unidade", extrair só o nome para formatação
        nome_norm = chave.split("|")[0]
        qtd_formatada = _formatar_quantidade(nome_norm, qtd_semanal, unidade)
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
    """Extrai número e unidade. Suporta g, kg, ml, l, unidade, xícara,
    colher_sopa, colher_cha, fatia, pote, lata, sachê, caixa, pacote, porção."""
    qtd_str = qtd_str.lower().strip()

    # Unidades compostas normalizadas pelo prompt da IA
    UNIDADES_COMPOSTAS = {
        "colher_sopa": ("colher_sopa", 1),
        "colher_cha": ("colher_cha", 1),
        "xicara": ("xicara", 1),
    }

    for alias, (unidade_final, fator) in UNIDADES_COMPOSTAS.items():
        if alias in qtd_str:
            match = re.search(r'(\d+\.?\d*)', qtd_str)
            qtd = float(match.group(1)) if match else 1.0
            return qtd * fator, unidade_final

    # Unidades simples (ordem importa: mais específicas primeiro)
    ALIAS_UNIDADES = [
        (r'colher(?:es)?\s*de\s*sopa', "colher_sopa", 1),
        (r'colher(?:es)?\s*de\s*ch[aá]', "colher_cha", 1),
        (r'x[ií]car[as]?', "xicara", 1),
        (r'kg', "g", 1000),
        (r'gramas?', "g", 1),
        (r'ml', "ml", 1),           # ml antes de l\b para não confundir
        (r'litros?|(?<![a-z])l(?![a-z])', "ml", 1000),
        (r'g\b', "g", 1),
        (r'latas?', "lata", 1),
        (r'sach[eê]s?|envelopes?', "sache", 1),
        (r'caixas?', "caixa", 1),
        (r'pacotes?', "pacote", 1),
        (r'por[çc][oõ]es?|por[çc][aã]o', "porcao", 1),
        (r'conchas?', "g", 100),           # 1 concha ≈ 100g
        (r'potes?', "pote", 1),
        (r'colheres?', "colher_sopa", 1),   # colher sem especificação → sopa
        (r'fatias?', "fatia", 1),
        (r'unidades?|un\.?|und\.?', "unidade", 1),
    ]

    for padrao, unidade_final, fator in ALIAS_UNIDADES:
        match_u = re.search(padrao, qtd_str)
        if match_u:
            match_n = re.search(r'(\d+\.?\d*)', qtd_str)
            qtd = float(match_n.group(1)) if match_n else 1.0
            return qtd * fator, unidade_final

    # Fallback: só número
    match_num = re.search(r'(\d+\.?\d*)', qtd_str)
    if match_num:
        return float(match_num.group(1)), "unidade"

    return 0, "unidade"


# =============================================================================
# NORMALIZAÇÃO DE NOMES DE ITENS (para agregar variações)
# =============================================================================

# Mapeamento: se o nome contém a chave, normaliza para o valor
# Ordem importa: mais específicos primeiro
NORMALIZACAO_NOMES = [
    # Proteínas
    ("peito de frango", "frango"),
    ("frango grelhado", "frango"),
    ("frango desfiado", "frango"),
    ("filé de frango", "frango"),
    ("coxa de frango", "frango"),
    ("sobrecoxa", "frango"),
    ("carne moída", "carne"),
    ("carne vermelha", "carne"),
    ("filé mignon", "carne"),
    ("bife", "carne"),
    ("alcatra", "carne"),
    ("patinho", "carne"),
    ("filé de tilápia", "tilápia"),
    ("tilapia", "tilápia"),
    # Carboidratos
    ("arroz integral", "arroz integral"),
    ("arroz branco", "arroz"),
    ("batata doce", "batata doce"),
    ("batata inglesa", "batata"),
    ("pão integral", "pão integral"),
    ("pão francês", "pão"),
    ("pao frances", "pão"),
    ("pão de forma", "pão"),
    ("macarrão integral", "macarrão integral"),
    # Lácteos
    ("leite desnatado", "leite"),
    ("leite integral", "leite"),
    ("iogurte natural", "iogurte"),
    ("iogurte grego", "iogurte"),
    # Vegetais
    ("salada verde", "salada"),
    ("salada mista", "salada"),
    ("legumes refogados", "legumes"),
    ("legumes cozidos", "legumes"),
    # Suplementos
    ("whey protein", "whey protein"),
    ("manteiga de amendoim", "pasta de amendoim"),
    ("pasta de amendoim", "pasta de amendoim"),
    # Frutas (variações com tipo específico)
    ("banana prata", "banana"),
    ("banana nanica", "banana"),
    ("banana da terra", "banana da terra"),
    ("maçã verde", "maçã"),
    ("maçã fuji", "maçã"),
]


def _normalizar_nome_item(nome: str) -> str:
    """Normaliza nome do item para agregar variações corretamente.
    'Peito de frango' e 'Frango grelhado' viram 'Frango'."""
    nome_lower = nome.lower()
    for variacao, normalizado in NORMALIZACAO_NOMES:
        if variacao in nome_lower:
            return normalizado
    return nome_lower


# Peso médio de 1 colher de sopa por tipo de alimento (em gramas)
PESO_COLHER_SOPA = {
    "arroz": 25,       # 1 colher de sopa de arroz ≈ 25g
    "feijão": 25,      # 1 colher de sopa de feijão ≈ 25g
    "feijao": 25,
    "aveia": 10,       # 1 colher de sopa de aveia ≈ 10g
    "granola": 10,
    "açúcar": 12,
    "acucar": 12,
    "farinha": 15,
    "manteiga": 15,
    "requeijão": 15,
    "requeijao": 15,
    "macarrão": 25,
    "macarrao": 25,
}

# Alimentos que são líquidos (colher = ml)
LIQUIDOS = ["azeite", "óleo", "oleo", "mel", "vinagre", "molho", "leite", "suco"]


def _formatar_quantidade(nome: str, qtd: float, unidade: str) -> str:
    """Formata quantidade para exibição."""
    nome_lower = nome.lower()

    if unidade == "g":
        if qtd >= 1000:
            kg = qtd / 1000
            return f"{kg:.1f}kg".replace(".0kg", "kg")
        return f"{int(qtd)}g"

    if unidade == "ml":
        if qtd >= 1000:
            return f"{qtd/1000:.1f}L".replace(".0L", "L")
        return f"{int(qtd)}ml"

    if unidade in ("colher_sopa", "colher_cha"):
        ml_por_colher = 15 if unidade == "colher_sopa" else 5
        # Líquidos → converter para ml
        if any(liq in nome_lower for liq in LIQUIDOS):
            ml_total = qtd * ml_por_colher
            if ml_total >= 1000:
                return f"{ml_total/1000:.1f}L".replace(".0L", "L")
            return f"{int(ml_total)}ml"
        # Sólidos → converter para gramas
        for alimento, peso in PESO_COLHER_SOPA.items():
            if alimento in nome_lower:
                gramas = qtd * peso
                if gramas >= 1000:
                    return f"{gramas/1000:.1f}kg".replace(".0kg", "kg")
                return f"{int(gramas)}g"
        # Fallback sólido: 1 colher sopa ≈ 20g
        gramas = qtd * 20
        if gramas >= 1000:
            return f"{gramas/1000:.1f}kg".replace(".0kg", "kg")
        return f"{int(gramas)}g"

    if unidade == "unidade":
        qtd_int = int(round(qtd))
        if "ovo" in nome_lower:
            duzias = qtd_int / 12
            if duzias <= 1:
                return "1 dúzia"
            return f"{int(round(duzias))} dúzias"
        return f"{qtd_int} unidades"

    if unidade == "xicara":
        qtd_fmt = int(qtd) if qtd == int(qtd) else qtd
        return f"{qtd_fmt} xícaras" if qtd != 1 else "1 xícara"

    if unidade == "fatia":
        return f"{int(round(qtd))} fatias"

    if unidade == "pote":
        return f"{int(round(qtd))} potes"

    if unidade == "lata":
        return f"{int(round(qtd))} latas"

    if unidade == "sache":
        return f"{int(round(qtd))} sachês"

    if unidade == "caixa":
        return f"{int(round(qtd))} caixas"

    if unidade == "pacote":
        return f"{int(round(qtd))} pacotes"

    if unidade == "porcao":
        return f"{int(round(qtd))} porções"

    return f"{int(round(qtd))} {unidade}"
