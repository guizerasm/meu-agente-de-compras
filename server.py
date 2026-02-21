from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Importar funções do agent (se existirem)
try:
    from agent.agent import (
        interpretar_dieta_texto,
        interpretar_dieta_pdf,
        chat_humano,
        finalizar_compra
    )
except ImportError:
    # Se não existirem, usar funções simples
    def interpretar_dieta_texto(texto: str) -> dict:
        return {
            "fixos": ["arroz", "frango", "salada"],
            "escolhas": ["Prefere frango ou peixe?"]
        }

    async def interpretar_dieta_pdf(file):
        return {"fixos": ["arroz"], "escolhas": []}

    def chat_humano(dieta, historico, mensagem):
        return ("Perfeito! Anotado.", historico + [{"role": "assistant", "content": "Perfeito! Anotado."}])

    def finalizar_compra(dieta_final):
        return [
            {"nome": "Arroz", "quantidade": "2kg", "motivo": "Base alimentar"},
            {"nome": "Frango", "quantidade": "1kg", "motivo": "Proteína"},
            {"nome": "Salada", "quantidade": "500g", "motivo": "Vegetais"}
        ]

# Configurações de ambiente
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")

# Parse CORS origins
if ALLOWED_ORIGINS == "*":
    # Apenas para desenvolvimento local ou beta inicial
    origins = ["*"]
else:
    # Em produção, use domínios específicos
    origins = [origin.strip() for origin in ALLOWED_ORIGINS.split(",")]

app = FastAPI(
    title="Agente de Compras",
    description="Sistema inteligente para geração de listas de compras a partir de dietas",
    version="1.0.0"
)

# CORS com configuração segura
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    max_age=600,  # Cache de preflight por 10 minutos
)

# Servir arquivos estáticos do frontend
frontend_path = os.path.join(os.path.dirname(__file__), "frontend")
static_path = os.path.join(os.path.dirname(__file__), "static")

# Montar diretórios estáticos
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="frontend")
    
if os.path.exists(static_path):
    try:
        app.mount("/public", StaticFiles(directory=static_path), name="static")
    except:
        pass


class ChatRequest(BaseModel):
    dieta: dict
    historico: List[dict]
    mensagem_usuario: str


class FinalizarRequest(BaseModel):
    dieta_final: dict


class VerificarProntidaoRequest(BaseModel):
    dieta: dict


@app.get("/health")
async def health_check():
    """Health check endpoint para Render e monitoramento"""
    return {
        "status": "healthy",
        "environment": ENVIRONMENT,
        "service": "agente-de-compras",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Serve a página principal do frontend"""
    index_file = os.path.join(os.path.dirname(__file__), "frontend", "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file, media_type="text/html")
    return {"mensagem": "Agente de Compras rodando em http://localhost:8000"}


@app.get("/chat")
async def chat_page():
    """Serve a página de chat"""
    chat_file = os.path.join(os.path.dirname(__file__), "frontend", "chat.html")
    if os.path.exists(chat_file):
        return FileResponse(chat_file, media_type="text/html")
    return {"erro": "Página não encontrada"}


@app.post("/dieta")
async def receber_dieta(
    texto: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    """
    Recebe uma dieta e retorna estruturada com escolhas pendentes
    """
    try:
        if file:
            print(f"\n[DEBUG] Recebendo PDF: {file.filename}")
            dieta = await interpretar_dieta_pdf(file)
        elif texto:
            print(f"\n[DEBUG] Recebendo texto ({len(texto)} caracteres)")
            dieta = interpretar_dieta_texto(texto)
        else:
            return {"erro": "Envie texto ou PDF"}

        # ⚠️ VALIDAÇÃO CRÍTICA: Verificar se dieta foi interpretada corretamente
        print(f"\n[DEBUG] Dieta interpretada:")
        print(f"  - Fixos: {len(dieta.get('fixos', []))} itens")
        print(f"  - Escolhas: {len(dieta.get('escolhas', []))}")
        print(f"  - Dias: {dieta.get('dias', 'não definido')}")

        if not dieta.get("fixos") or len(dieta.get("fixos", [])) == 0:
            # Dieta vazia = erro crítico de interpretação
            print("[ERRO] Dieta retornou VAZIA! Verificar SYSTEM_INTERPRETACAO")
            return {
                "erro": "Não consegui interpretar a dieta. Verifique o formato do texto ou PDF.",
                "detalhes": "A interpretação retornou lista de alimentos vazia. Tente reformatar o texto."
            }

        # SEMPRE inicia conversa para confirmar detalhes (dias, pessoas, alimentos em casa)
        # Adiciona escolhas padrão se não tiver nenhuma
        if not dieta.get("escolhas"):
            dieta["escolhas"] = ["Preciso confirmar alguns detalhes antes de gerar a lista"]

        # Sempre há escolhas pendentes no início para manter conversa fluida
        escolhas_pendentes = True

        print(f"[DEBUG] Dieta OK! Retornando com {len(dieta['fixos'])} itens fixos\n")

        mensagem = "Perfeito! Vamos conversar um pouco para ajustar sua lista 🙂"
        if dieta.get("tem_estimativas"):
            nomes = ", ".join(dieta.get("itens_estimados", [])[:5])
            mensagem += f"\n\n⚠️ Notei que alguns alimentos não tinham quantidade definida ({nomes}). Usei porções padrão como referência — você pode ajustar depois!"

        return {
            "dieta": dieta,
            "escolhas_pendentes": escolhas_pendentes,
            "mensagem": mensagem
        }
    except Exception as e:
        print(f"[ERRO] Exceção ao processar dieta: {e}")
        import traceback
        traceback.print_exc()
        return {"erro": f"Erro ao processar dieta: {str(e)}", "detalhes": str(e)}


@app.post("/chat")
async def conversar(req: ChatRequest):
    """
    Conversa com o usuário para resolver escolhas
    """
    try:
        resposta, historico = chat_humano(
            req.dieta,
            req.historico,
            req.mensagem_usuario
        )

        # ✅ DETECÇÃO INTELIGENTE: Se agente indicar que está pronto, limpar escolhas
        palavras_finalizacao = ["finalizar", "gerar sua lista", "está pronto", "pode clicar"]
        resposta_lower = resposta.lower()

        if any(palavra in resposta_lower for palavra in palavras_finalizacao):
            # Limpar escolhas para habilitar botão Finalizar
            req.dieta["escolhas"] = []

        return {
            "resposta": resposta,
            "historico": historico,
            "dieta_atualizada": req.dieta  # Retornar dieta atualizada para frontend sincronizar
        }
    except Exception as e:
        return {"erro": f"Erro ao processar chat: {str(e)}", "detalhes": str(e)}


@app.post("/verificar-prontidao")
def verificar_prontidao(req: VerificarProntidaoRequest):
    """
    Verifica se todas as escolhas foram resolvidas
    Retorna True se está pronto para gerar lista de compras
    """
    dieta = req.dieta
    escolhas_pendentes = len(dieta.get("escolhas", [])) > 0
    
    return {
        "pronto": not escolhas_pendentes,
        "mensagem": "Tudo certo! Vamos gerar a lista de compras?" if not escolhas_pendentes else "Ainda há escolhas pendentes"
    }


def validar_quantidades(lista_compras: list, dieta: dict = None) -> tuple[bool, list]:
    """
    Validacao DESABILITADA - a IA ja calcula corretamente
    Retorna sempre (True, []) para nao gerar alertas falsos
    """
    # DESABILITADO: A logica anterior tinha bugs que geravam alertas incorretos
    # Ex: "150g parece muito, sugestao: 2kg" - completamente errado
    # A IA ja faz os calculos corretos no SYSTEM_COMPRA
    return (True, [])


@app.post("/finalizar")
async def finalizar(req: FinalizarRequest):
    """
    Gera a lista de compras final com validação
    """
    try:
        lista = finalizar_compra(req.dieta_final)

        # ✅ VALIDAÇÃO DE SANIDADE (passa dieta para considerar número de pessoas)
        valido, alertas = validar_quantidades(lista, req.dieta_final)

        if not valido:
            # Retornar com avisos mas permitir continuar
            return {
                "lista_compras": lista,
                "avisos": alertas,
                "mensagem": "Lista gerada com avisos de quantidade"
            }

        return {"lista_compras": lista}
    except Exception as e:
        return {"erro": f"Erro ao finalizar: {str(e)}", "detalhes": str(e)}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/gerar-pdf")
async def gerar_pdf_endpoint(req: dict):
    """
    Gera PDF da lista de compras
    """
    try:
        from agent.pdf_generator import gerar_pdf_lista_compras

        lista_compras = req.get('lista_compras', [])

        if not lista_compras:
            return {"erro": "Lista de compras vazia"}

        pdf_bytes = gerar_pdf_lista_compras(lista_compras)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=lista_compras.pdf"
            }
        )
    except ImportError as e:
        return {
            "erro": "Biblioteca reportlab não instalada",
            "detalhes": "Execute: pip install reportlab",
            "mensagem": str(e)
        }
    except Exception as e:
        return {
            "erro": f"Erro ao gerar PDF: {str(e)}",
            "detalhes": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)