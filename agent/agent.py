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

    return resposta, historico


def finalizar_compra(dieta_final):
    return gerar_lista_compras(dieta_final)
