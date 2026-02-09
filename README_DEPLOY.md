# 🚀 Deploy no Render - Agente de Compras

Guia completo e seguro para deploy em produção.

## 📋 Pré-requisitos

- [ ] Conta no GitHub
- [ ] Conta no Render (https://render.com - gratuita)
- [ ] API Key da OpenAI (https://platform.openai.com/api-keys)
- [ ] Código commited no GitHub (SEM o arquivo .env!)

---

## 🔐 CHECKLIST DE SEGURANÇA (CRUCIAL!)

Antes de fazer o deploy, verifique:

### ✅ 1. Arquivo `.env` NÃO está no Git
```bash
# Verificar se .env está no .gitignore
cat .gitignore | grep .env

# NUNCA commite o .env!
git status
# Se .env aparecer, adicione ao .gitignore imediatamente
```

### ✅ 2. `.gitignore` está configurado
```bash
# Deve conter:
.env
.env.local
venv/
__pycache__/
```

### ✅ 3. Variáveis de ambiente estão configuradas
- OpenAI API Key está em .env LOCAL
- NÃO hardcode a API key no código
- Use `os.getenv("OPENAI_API_KEY")` sempre

---

## 🚀 Passo a Passo do Deploy

### 1. Preparar Repositório Git

```bash
# 1.1 - Inicializar Git (se ainda não tiver)
git init

# 1.2 - Adicionar arquivos (exceto .env!)
git add .

# 1.3 - Verificar o que será commitado
git status
# ⚠️ SE .env APARECER, PARE! Adicione ao .gitignore primeiro

# 1.4 - Commit
git commit -m "Preparar deploy no Render com segurança"

# 1.5 - Criar repositório no GitHub
# Vá em: https://github.com/new
# Nome: meu-agente-de-compras (ou outro de sua escolha)
# Privado: SIM (recomendado para beta)

# 1.6 - Conectar com GitHub
git remote add origin https://github.com/SEU-USUARIO/meu-agente-de-compras.git
git branch -M main
git push -u origin main
```

### 2. Deploy no Render

#### 2.1 - Criar conta e conectar GitHub

1. Acesse https://render.com
2. Clique em "Sign Up" → "GitHub"
3. Autorize o Render a acessar seu repositório

#### 2.2 - Criar Web Service

1. No dashboard do Render, clique em "New +"
2. Selecione "Web Service"
3. Conecte seu repositório `meu-agente-de-compras`
4. Configure:

```yaml
Name: agente-de-compras
Region: Oregon (US West) ou Frankfurt (EU Central)
Branch: main
Runtime: Python 3
Build Command: pip install --upgrade pip && pip install -r requirements.txt
Start Command: uvicorn server:app --host 0.0.0.0 --port $PORT
Instance Type: Free (para começar)
```

#### 2.3 - 🔐 Configurar Variáveis de Ambiente (CRÍTICO!)

Na seção **Environment Variables**, adicione:

| Key | Value | Nota |
|-----|-------|------|
| `OPENAI_API_KEY` | `sk-proj-xxxx...` | **Cole sua API key da OpenAI** |
| `ENVIRONMENT` | `production` | Modo produção |
| `PYTHON_VERSION` | `3.11` | Versão Python |
| `ALLOWED_ORIGINS` | `*` | Para beta; depois liste domínios específicos |

**⚠️ IMPORTANTE:**
- A `OPENAI_API_KEY` é **OBRIGATÓRIA**
- Nunca compartilhe essa chave publicamente
- No Render, ela fica criptografada e segura

#### 2.4 - Deploy

1. Clique em "Create Web Service"
2. Aguarde o build (~5-10 minutos na primeira vez)
3. Quando ver "Live", seu app está no ar! 🎉

### 3. Testar a Aplicação

Seu app estará disponível em:
```
https://agente-de-compras-XXXX.onrender.com
```

Teste:
- Health check: https://agente-de-compras-XXXX.onrender.com/health
- Página principal: https://agente-de-compras-XXXX.onrender.com

---

## 🔒 Boas Práticas de Segurança em Produção

### 1. **CORS Restritivo** (Após Beta)

Quando sair da fase beta, atualize o CORS para aceitar apenas SEU domínio:

No Render, edite a variável `ALLOWED_ORIGINS`:
```
ALLOWED_ORIGINS=https://seu-dominio.com,https://www.seu-dominio.com
```

### 2. **Monitoramento de Custos OpenAI**

1. Acesse: https://platform.openai.com/usage
2. Configure **Usage Limits** para evitar surpresas:
   - Hard limit: $10/mês (ou o que preferir)
   - Email alert: $5

### 3. **Rate Limiting** (Para implementar depois)

Protege contra abuso:
```python
# Adicione no requirements.txt:
# slowapi==0.1.9

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/dieta")
@limiter.limit("10/minute")  # Máximo 10 requisições por minuto
async def receber_dieta(...):
    ...
```

### 4. **Logs e Monitoramento**

- Render oferece logs integrados
- Monitore erros e performance
- Configure alertas para downtime

---

## 🆙 Updates e Atualizações

### Atualizar código em produção:

```bash
# 1. Fazer mudanças no código
# 2. Testar localmente
python server.py

# 3. Commit e push
git add .
git commit -m "Descrição das mudanças"
git push origin main

# 4. Render fará deploy automático! 🚀
```

---

## 🐛 Troubleshooting

### Deploy falhou?

1. **Verifique os logs no Render**
   - Dashboard → seu service → "Logs"
   - Procure por erros em vermelho

2. **Erro: "No module named 'X'"**
   - Faltou adicionar dependência no `requirements.txt`
   - Adicione e faça push novamente

3. **Erro: "OPENAI_API_KEY not found"**
   - Variável de ambiente não configurada
   - Vá em Settings → Environment → Adicione a chave

4. **Cold Start lento (30s+)**
   - Normal no plano Free do Render
   - Para remover: upgrade para paid plan ($7/mês)

### App não responde?

1. Verifique se está "Suspended" (inatividade)
2. Acesse a URL para "acordar" o serviço
3. Consider upgrade se precisar de uptime 100%

---

## 💰 Custos Estimados

| Item | Free Tier | Uso Esperado (Beta) | Custo |
|------|-----------|---------------------|-------|
| **Render** | 750h/mês | ~720h/mês | **$0** |
| **OpenAI (GPT-4o-mini)** | $0.150/1M tokens input | ~10-50 dietas/dia | **~$5-15/mês** |
| **Total Beta** | - | - | **~$5-15/mês** |

**Após sucesso e crescimento:**
- Render Pro: $7/mês (sem cold start)
- Scaling: ~$19/mês para mais RAM
- Total: ~$25-35/mês para app profissional

---

## 🎯 Próximos Passos Após Deploy

1. **Compartilhe o link** com beta testers selecionados
2. **Configure analytics** (Google Analytics, Mixpanel)
3. **Implemente feedback** dos usuários
4. **Monitore custos** OpenAI diariamente
5. **Adicione rate limiting** se houver abuso
6. **Configure domínio custom** (após validação)

---

## 📞 Suporte

- **Render Docs**: https://render.com/docs
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **OpenAI Issues**: https://platform.openai.com/docs

---

## ✅ Checklist Final Antes do Deploy

- [ ] `.env` está no `.gitignore`
- [ ] `.env` NÃO foi commitado
- [ ] `requirements.txt` tem todas as dependências
- [ ] `server.py` tem configuração de CORS
- [ ] Testado localmente e funcionando
- [ ] Repositório no GitHub (privado recomendado)
- [ ] OpenAI API Key copiada e pronta
- [ ] Conta Render criada
- [ ] Variáveis de ambiente configuradas no Render
- [ ] Deploy concluído e testado

---

## 🎉 Pronto!

Seu Agente de Compras está no ar e seguro!

Próximo: divulgar para beta testers e coletar feedback 🚀
