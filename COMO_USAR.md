# 🛒 GUIA RÁPIDO - AGENTE DE COMPRAS

## ⚡ Início Rápido (3 passos)

### 1️⃣ Iniciar o Servidor
```bash
python server.py
```

### 2️⃣ Abrir no Navegador
```
http://localhost:8000
```

### 3️⃣ Digitar sua Dieta
Cole sua dieta semanal e clique em "Enviar"!

---

## 📖 Como Funciona

### O que o Agente Faz?

1. **Recebe sua dieta** (texto livre, sem formato específico)
2. **Interpreta automaticamente** usando IA
3. **Identifica todos os alimentos**
4. **Gera lista de compras** com quantidades calculadas para a semana

---

## 💬 Exemplos de Dieta

### Exemplo Simples
```
Segunda: arroz, feijão e frango
Terça: macarrão com carne moída
Quarta: peixe com salada
Quinta: pizza
Sexta: hambúrguer caseiro
```

### Exemplo Completo
```
SEGUNDA-FEIRA
Café: Pão com manteiga e café
Almoço: Arroz, feijão, bife e salada
Jantar: Sopa de legumes

TERÇA-FEIRA
Café: Iogurte com granola
Almoço: Macarrão à bolonhesa
Jantar: Sanduíche natural

... (continue para os outros dias)
```

---

## 🎯 Dicas de Uso

### ✅ O que FAZER

- Escreva de forma natural, como você fala
- Pode incluir café, almoço e jantar
- Pode usar abreviações (ex: "seg", "ter")
- Não precisa ser detalhado demais

### ❌ O que NÃO fazer

- Não precisa colocar quantidades (a IA calcula)
- Não precisa estruturar em formato específico
- Não precisa listar ingredientes individuais

---

## 📱 Usando a Interface Web

### Passo a Passo

1. **Abra:** http://localhost:8000
2. **Digite ou cole** sua dieta na caixa de texto
3. **Clique** em "Enviar Dieta"
4. **Aguarde** alguns segundos (a IA está processando)
5. **Veja** sua lista de compras gerada!

### O que esperar

A lista terá:
- ✅ Nome dos produtos
- ✅ Quantidade recomendada
- ✅ Unidade de medida (kg, litros, pacotes, etc)
- ✅ Motivo (ex: "consumo semanal estimado")

---

## 🔧 Usando via API (para programadores)

### Enviar Dieta
```bash
curl -X POST http://localhost:8000/dieta \
  -d "texto=Segunda: arroz e frango"
```

**Resposta:**
```json
{
  "dieta": {
    "fixos": ["arroz", "frango"],
    "escolhas": []
  },
  "escolhas_pendentes": false,
  "mensagem": "Dieta pronta para gerar lista de compras!"
}
```

### Gerar Lista de Compras
```bash
curl -X POST http://localhost:8000/finalizar \
  -H "Content-Type: application/json" \
  -d '{
    "dieta_final": {
      "fixos": ["arroz", "frango", "feijão"],
      "escolhas": []
    }
  }'
```

**Resposta:**
```json
{
  "lista_compras": [
    {
      "nome": "arroz",
      "quantidade": "5kg",
      "motivo": "Consumo semanal estimado"
    },
    {
      "nome": "frango",
      "quantidade": "2kg",
      "motivo": "Fonte de proteína"
    }
  ]
}
```

---

## 🧪 Executar Testes

### Teste Rápido
```bash
python teste_simples.py
```

### Teste Completo (com dieta de 7 dias)
```bash
python teste_completo_final.py
```

### Teste Sem Servidor (apenas funções)
```bash
python teste_direto.py
```

---

## ⚙️ Comandos Úteis

### Iniciar Servidor
```bash
python server.py
```

### Verificar se está Rodando
```bash
curl http://localhost:8000/health
```
Resposta esperada: `{"status":"ok"}`

### Parar Servidor
- **Windows:** `Ctrl + C` no terminal
- **Linux/Mac:** `Ctrl + C` no terminal

---

## 🚨 Solução de Problemas

### Erro: "Porta 8000 já em uso"
```bash
# Windows
netstat -ano | findstr :8000
# Anote o PID e execute:
taskkill /F /PID <número>

# Linux/Mac
lsof -ti:8000 | xargs kill -9
```

### Erro: "API key inválida"
1. Verifique se o arquivo `.env` existe
2. Confirme que tem a linha: `OPENAI_API_KEY=sk-...`
3. Reinicie o servidor

### Erro: "Módulo não encontrado"
```bash
pip install -r requirements.txt
```

---

## 📊 Exemplo de Resultado Completo

### Entrada:
```
Segunda: Arroz, feijão e frango
Terça: Macarrão com molho
Quarta: Peixe com salada
Quinta: Pizza
Sexta: Hambúrguer
Sábado: Churrasco
Domingo: Feijoada
```

### Saída (Lista de Compras):
```
1. ARROZ          - 3kg
2. FEIJÃO         - 1kg
3. FRANGO         - 1.5kg
4. MACARRÃO       - 1kg
5. MOLHO TOMATE   - 2 latas
6. PEIXE          - 1kg
7. SALADA         - 1 pacote
8. PIZZA (MASSA)  - 2 pacotes
9. CARNE MOÍDA    - 500g
10. PÃO HAMBÚRGUER - 1 pacote
11. CARNE CHURRASCO - 2kg
12. FEIJÃO PRETO   - 1kg
```

---

## 💡 Recursos Avançados

### Conversar com o Agente
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "dieta": {"fixos": ["arroz"], "escolhas": []},
    "historico": [],
    "mensagem_usuario": "Prefiro frango orgânico"
  }'
```

### Verificar Prontidão
```bash
curl -X POST http://localhost:8000/verificar-prontidao \
  -H "Content-Type: application/json" \
  -d '{"dieta": {"fixos": ["arroz"], "escolhas": []}}'
```

---

## 📁 Estrutura do Projeto

```
meu-agente-de-compras/
├── server.py              # Servidor principal
├── .env                   # Chave API (NÃO COMMITAR!)
├── agent/
│   ├── ai_parser.py       # Lógica de IA
│   ├── agent.py           # Funções auxiliares
│   └── openai_client.py   # Cliente OpenAI
├── frontend/
│   ├── chat.html          # Interface web
│   └── index.html         # Página inicial
└── testes/
    ├── teste_simples.py   # Teste básico
    └── teste_completo_final.py  # Teste completo
```

---

## 🎓 Entendendo o Fluxo

```
┌─────────────┐
│   USUÁRIO   │
│  digita     │
│   dieta     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  SERVIDOR   │
│ (server.py) │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   AI        │
│ interpreta  │
│ (ai_parser) │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  OPENAI     │
│  processa   │
│   com GPT   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   LISTA     │
│    DE       │
│  COMPRAS    │
└─────────────┘
```

---

## ✅ Checklist de Uso Diário

- [ ] Servidor rodando?
- [ ] Navegador aberto em localhost:8000?
- [ ] Dieta pronta para copiar?
- [ ] Enviou a dieta?
- [ ] Lista de compras gerada?
- [ ] Copiou para usar no mercado?

---

## 🆘 Suporte

### Documentação Completa
- `CORRECOES_APLICADAS_AGORA.md` - Correções técnicas
- `INDICE_TESTES.md` - Guia de testes
- `GUIA_PASSO_A_PASSO_TESTES.md` - Tutorial detalhado

### Arquivos de Teste
- `teste_simples.py` - Teste básico
- `teste_direto.py` - Teste sem servidor
- `teste_completo_final.py` - Teste avançado

---

**🎉 Pronto para usar! Boa sorte com suas compras!**

**Desenvolvido com ❤️ - Agente de Compras v2.0**
