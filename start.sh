#!/bin/bash
# Script para iniciar o Agente de Compras com ambiente configurado

echo "🛒 AGENTE DE COMPRAS - Inicialização"
echo "===================================="
echo ""

# Verificar Python
echo "✓ Verificando Python..."
python --version
if [ $? -ne 0 ]; then
    echo "❌ Python não encontrado. Instale Python 3.8+"
    exit 1
fi

# Verificar pip
echo "✓ Verificando pip..."
pip --version
if [ $? -ne 0 ]; then
    echo "❌ pip não encontrado"
    exit 1
fi

# Instalar/atualizar dependências
echo ""
echo "📦 Instalando dependências..."
if [ -f "requirements.txt" ]; then
    pip install -q -r requirements.txt
    echo "✓ Dependências instaladas"
else
    echo "❌ requirements.txt não encontrado"
    exit 1
fi

# Verificar OPENAI_API_KEY
echo ""
echo "🔑 Verificando chave OpenAI..."
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY não está definida"
    echo ""
    echo "Configure com:"
    echo "  export OPENAI_API_KEY=sk-..."
    echo ""
    read -p "Deseja continuar sem validação? (s/n): " choice
    if [ "$choice" != "s" ] && [ "$choice" != "S" ]; then
        exit 1
    fi
else
    echo "✓ OPENAI_API_KEY configurada"
fi

# Iniciar servidor
echo ""
echo "🚀 Iniciando servidor..."
echo "   Acesse: http://localhost:8000"
echo ""
echo "Pressione Ctrl+C para parar"
echo "===================================="
echo ""

python server.py --reload
