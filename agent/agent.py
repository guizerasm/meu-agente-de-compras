from agent.ai_parser import (
    interpretar_dieta,
    conversar_com_usuario,
    gerar_lista_compras
)
from agent.pdf_reader import extrair_texto_pdf


def interpretar_dieta_texto(texto: str):
    return interpretar_dieta(texto)


async def interpretar_dieta_pdf(file):
    texto = extrair_texto_pdf(file)
    return interpretar_dieta(texto)


def chat_humano(dieta, historico, mensagem_usuario):
    import re

    historico.append({"role": "user", "content": mensagem_usuario})
    resposta = conversar_com_usuario(dieta, historico)
    historico.append({"role": "assistant", "content": resposta})

    # ✅ EXTRAÇÃO INTELIGENTE: Atualizar dieta com informações da mensagem
    msg_lower = mensagem_usuario.lower()

    # Detectar número de pessoas (1-20)
    match_pessoas = re.search(r'(\d+)\s*pessoa', msg_lower)
    if match_pessoas:
        dieta["pessoas"] = int(match_pessoas.group(1))

    # Detectar dias (variações: "1 dia", "um dia", "7 dias", "semana completa")
    # IMPORTANTE: Só atualizar se usuário EXPLICITAMENTE corrigir
    if "1 dia só" in msg_lower or "dieta é de 1 dia" in msg_lower or "só 1 dia" in msg_lower or "apenas 1 dia" in msg_lower:
        dieta["dias"] = 1
        print(f"[DEBUG] Usuário confirmou: dieta é para 1 dia")
    elif "semana completa" in msg_lower or "já é a semana" in msg_lower or "7 dias completos" in msg_lower:
        dieta["dias"] = 7
        print(f"[DEBUG] Usuário confirmou: dieta é para semana completa (7 dias)")

    # Detectar alimentos que já tem em casa
    if "já tenho" in msg_lower or "tenho em casa" in msg_lower or "já tem" in msg_lower:
        if "alimentos_em_casa" not in dieta:
            dieta["alimentos_em_casa"] = []

        # Lista de alimentos comuns para detecção inteligente
        alimentos_detectaveis = {
            "whey": ["whey", "proteína", "suplemento"],
            "azeite": ["azeite", "óleo", "oliva"],
            "arroz": ["arroz"],
            "feijão": ["feijão", "feijao"],
            "café": ["café", "cafe"],
            "açúcar": ["açúcar", "acucar"],
            "sal": ["sal"],
            "ovos": ["ovo", "ovos"],
            "leite": ["leite"],
            "pão": ["pão", "pao"],
        }

        # Verificar cada alimento detectável
        for alimento_base, variacoes in alimentos_detectaveis.items():
            if any(variacao in msg_lower for variacao in variacoes):
                # Procurar nos fixos qual é o nome completo
                for fixo in dieta.get("fixos", []):
                    fixo_lower = fixo.lower()
                    if any(variacao in fixo_lower for variacao in variacoes):
                        if fixo not in dieta["alimentos_em_casa"]:
                            dieta["alimentos_em_casa"].append(fixo)
                            print(f"[DEBUG] Alimento detectado em casa: {fixo}")
                        break

    # Detectar preferência de proteína
    if "só frango" in msg_lower or "apenas frango" in msg_lower or "prefiro frango" in msg_lower:
        dieta["preferencia_proteina"] = "frango"
    elif "só carne" in msg_lower or "apenas carne" in msg_lower or "prefiro carne" in msg_lower or "carne vermelha" in msg_lower:
        dieta["preferencia_proteina"] = "carne"
    elif "só peixe" in msg_lower or "apenas peixe" in msg_lower or "prefiro peixe" in msg_lower:
        dieta["preferencia_proteina"] = "peixe"
    elif "variar" in msg_lower or "variado" in msg_lower or "mix" in msg_lower or "diferentes" in msg_lower:
        dieta["preferencia_proteina"] = "variado"

    # Detectar preferência de carboidrato
    if "só arroz" in msg_lower or "apenas arroz" in msg_lower or "prefiro arroz" in msg_lower:
        dieta["preferencia_carboidrato"] = "arroz"
    elif "só batata" in msg_lower or "apenas batata" in msg_lower or "prefiro batata" in msg_lower:
        dieta["preferencia_carboidrato"] = "batata"
    elif "só macarrão" in msg_lower or "macarrao" in msg_lower or "prefiro macarrao" in msg_lower or "prefiro macarrão" in msg_lower:
        dieta["preferencia_carboidrato"] = "macarrao"
    elif ("carboidrato" in msg_lower or "carboidratos" in msg_lower) and ("variar" in msg_lower or "variado" in msg_lower):
        dieta["preferencia_carboidrato"] = "variado"

    # Detectar preferência de frutas
    frutas_comuns = ["banana", "maçã", "maca", "uva", "morango", "melão", "melao", "kiwi", "abacaxi", "manga", "laranja"]
    frutas_mencionadas = [fruta for fruta in frutas_comuns if fruta in msg_lower]
    if frutas_mencionadas and ("prefiro" in msg_lower or "gosto de" in msg_lower or "só" in msg_lower):
        dieta["preferencia_frutas"] = ", ".join(frutas_mencionadas)
    elif ("fruta" in msg_lower or "frutas" in msg_lower) and ("variar" in msg_lower or "variado" in msg_lower or "qualquer" in msg_lower):
        dieta["preferencia_frutas"] = "variado"

    # Detectar preferência de vegetais
    if ("vegetal" in msg_lower or "vegetais" in msg_lower or "legume" in msg_lower) and ("não gosto" in msg_lower or "nao gosto" in msg_lower):
        # Capturar o que não gosta
        dieta["preferencia_vegetais"] = mensagem_usuario  # Guardar mensagem completa para AI processar
    elif ("vegetal" in msg_lower or "vegetais" in msg_lower) and ("variar" in msg_lower or "variado" in msg_lower or "qualquer" in msg_lower):
        dieta["preferencia_vegetais"] = "variado"

    # Detectar preferências gerais
    if "integral" in msg_lower or "integrais" in msg_lower:
        dieta["preferencias"] = dieta.get("preferencias", "") + " integrais"
    if "sem lactose" in msg_lower:
        dieta["preferencias"] = dieta.get("preferencias", "") + " sem lactose"
    if "orgânico" in msg_lower or "organico" in msg_lower:
        dieta["preferencias"] = dieta.get("preferencias", "") + " orgânicos"

    # ✅ DETECTAR TROCAS DE ALIMENTOS (ex: "trocar pão francês por pão de forma")
    trocas_detectadas = []

    # Mapeamento de trocas comuns
    TROCAS_POSSIVEIS = {
        "pão de forma": ["pao frances", "pão francês", "pao francês", "pão frances"],
        "pao de forma": ["pao frances", "pão francês", "pao francês", "pão frances"],
        "pão francês": ["pao de forma", "pão de forma"],
        "carne": ["frango", "peixe", "tilapia"],
        "frango": ["carne", "peixe", "tilapia"],
        "peixe": ["frango", "carne"],
        "batata": ["arroz", "macarrão", "macarrao"],
        "arroz": ["batata", "macarrão", "macarrao"],
        "macarrão": ["arroz", "batata"],
    }

    # Detectar pedidos de troca
    palavras_troca = ["trocar", "troca", "mudar", "muda", "prefiro", "quero", "substituir", "substitui"]
    if any(palavra in msg_lower for palavra in palavras_troca):
        # Procurar qual alimento o usuário quer
        for alimento_novo, alimentos_antigos in TROCAS_POSSIVEIS.items():
            if alimento_novo in msg_lower:
                # Verificar se menciona algum alimento antigo ou se é genérico
                for alimento_antigo in alimentos_antigos:
                    # Atualizar nas refeições
                    if "refeicoes" in dieta:
                        for nome_refeicao, itens in dieta["refeicoes"].items():
                            for i, item in enumerate(itens):
                                item_nome = item.get("item", "").lower()
                                if alimento_antigo in item_nome:
                                    # Manter quantidade, trocar nome
                                    qtd = item.get("quantidade", "1 unidade")
                                    dieta["refeicoes"][nome_refeicao][i] = {
                                        "item": alimento_novo.title(),
                                        "quantidade": qtd,
                                        "vezes": 1
                                    }
                                    trocas_detectadas.append(f"{alimento_antigo} → {alimento_novo}")
                                    print(f"[DEBUG] Troca detectada: {alimento_antigo} → {alimento_novo} em {nome_refeicao}")

    if trocas_detectadas:
        print(f"[DEBUG] Total de trocas: {len(trocas_detectadas)}")

    return resposta, historico


def finalizar_compra(dieta_final):
    return gerar_lista_compras(dieta_final)
