#!/usr/bin/env python
"""
🔍 Script de Verificação Pré-Deploy
Verifica se tudo está configurado corretamente antes do deploy
"""
import os
import sys
from pathlib import Path

def verificar_arquivo(nome, obrigatorio=True):
    """Verifica se um arquivo existe"""
    existe = Path(nome).exists()
    status = "✅" if existe else ("❌" if obrigatorio else "⚠️")
    print(f"{status} {nome}: {'Encontrado' if existe else 'NÃO encontrado'}")
    return existe

def verificar_gitignore():
    """Verifica se .gitignore está configurado corretamente"""
    print("\n🔒 Verificando .gitignore...")

    if not verificar_arquivo(".gitignore"):
        print("   ❌ CRÍTICO: .gitignore não existe!")
        return False

    with open(".gitignore", "r") as f:
        conteudo = f.read()

    essenciais = [".env", "venv/", "__pycache__/"]
    faltando = []

    for item in essenciais:
        if item not in conteudo:
            faltando.append(item)
            print(f"   ❌ Faltando: {item}")
        else:
            print(f"   ✅ Protegido: {item}")

    return len(faltando) == 0

def verificar_env():
    """Verifica configuração de variáveis de ambiente"""
    print("\n🔐 Verificando variáveis de ambiente...")

    # Verificar se .env existe (NÃO deve estar no Git)
    env_existe = Path(".env").exists()
    if env_existe:
        print("   ✅ .env existe (LOCAL)")

        # Carregar e verificar
        from dotenv import load_dotenv
        load_dotenv()

        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and openai_key.startswith("sk-"):
            print("   ✅ OPENAI_API_KEY configurada")
        else:
            print("   ❌ OPENAI_API_KEY inválida ou ausente")
            return False
    else:
        print("   ⚠️ .env não encontrado (OK se for primeiro deploy)")

    # Verificar se .env.example existe
    verificar_arquivo(".env.example", obrigatorio=False)

    return True

def verificar_dependencies():
    """Verifica requirements.txt"""
    print("\n📦 Verificando dependências...")

    if not verificar_arquivo("requirements.txt"):
        return False

    with open("requirements.txt", "r") as f:
        deps = f.read()

    essenciais = ["fastapi", "uvicorn", "openai", "python-dotenv", "PyPDF2", "reportlab"]

    for dep in essenciais:
        if dep.lower() in deps.lower():
            print(f"   ✅ {dep}")
        else:
            print(f"   ❌ FALTANDO: {dep}")
            return False

    return True

def verificar_git():
    """Verifica se .env está no Git"""
    print("\n🔍 Verificando Git...")

    # Verificar se .env está tracked
    result = os.popen("git ls-files .env 2>&1").read()

    if ".env" in result:
        print("   ❌ PERIGO! .env está no Git!")
        print("   Execute: git rm --cached .env")
        print("   E adicione ao .gitignore")
        return False
    else:
        print("   ✅ .env NÃO está no Git")

    return True

def main():
    """Executa todas as verificações"""
    print("=" * 60)
    print("🔍 VERIFICAÇÃO PRÉ-DEPLOY - AGENTE DE COMPRAS")
    print("=" * 60)

    checks = [
        ("Arquivos essenciais", lambda: all([
            verificar_arquivo("server.py"),
            verificar_arquivo("requirements.txt"),
            verificar_arquivo("render.yaml"),
            verificar_arquivo("agent/agent.py"),
            verificar_arquivo("agent/ai_parser.py"),
        ])),
        (".gitignore", verificar_gitignore),
        ("Variáveis de ambiente", verificar_env),
        ("Dependências", verificar_dependencies),
        ("Git seguro", verificar_git),
    ]

    resultados = []

    for nome, check in checks:
        try:
            resultado = check()
            resultados.append(resultado)
        except Exception as e:
            print(f"\n❌ Erro em {nome}: {e}")
            resultados.append(False)

    # Resumo final
    print("\n" + "=" * 60)
    print("📊 RESUMO")
    print("=" * 60)

    if all(resultados):
        print("✅ TUDO PRONTO PARA DEPLOY!")
        print("\nPróximo passo:")
        print("1. Commitar código: git add . && git commit -m 'Preparar deploy'")
        print("2. Push para GitHub: git push origin main")
        print("3. Seguir README_DEPLOY.md")
        sys.exit(0)
    else:
        print("❌ PROBLEMAS ENCONTRADOS!")
        print("\nCorreja os erros acima antes do deploy.")
        print("Consulte README_DEPLOY.md para mais detalhes.")
        sys.exit(1)

if __name__ == "__main__":
    main()
