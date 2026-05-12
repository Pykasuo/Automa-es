# 🔴 PROBLEMA: Card não está sendo buscado pela automação

## 🎯 CAUSAS MAIS PROVÁVEIS (em ordem de probabilidade):

### 1️⃣ **STATUS DA TASK ERRADO** (Probabilidade: 70%)
A task tem status diferente de "em rascunho"

**Como verificar:**
- Abra ClickUp
- Clique na task
- Veja o status no topo

**Como corrigir:**
```
Clique no status → Selecione "em rascunho"
```

---

### 2️⃣ **TASK TEM RESPONSÁVEL** (Probabilidade: 20%)
O script ignora tasks com responsável atribuído

**Como verificar:**
- Abra ClickUp → Task
- Procure por "Assignee" ou "Responsável"
- Se tiver alguém → É esse o problema

**Como corrigir:**
```
Clique no Assignee → Remova a pessoa atribuída
```

---

### 3️⃣ **CAMPO "AÇÃO" VAZIO OU ERRADO** (Probabilidade: 5%)
O campo customizado "Ação no chamado" precisa estar preenchido

**Como verificar:**
- Abra ClickUp → Task
- Procure por "Ação no chamado"
- Verifique o valor

**Como corrigir:**
```
Se vazio: Preencha com "CANCELAR" ou "REABRIR"
Se errado: Mude para o valor correto
```

---

### 4️⃣ **SCRIPT RODANDO FORA DO HORÁRIO** (Probabilidade: 3%)
O script só executa entre 08:00-12:00 e 13:00-18:00

**Como verificar:**
```powershell
Get-Date  # Veja a hora
```

**Como corrigir:**
```
Use teste_sem_horario.py para testes fora do horário
```

---

### 5️⃣ **CREDENCIAIS INVÁLIDAS** (Probabilidade: 2%)
Token ClickUp expirou ou incorreto

**Como verificar:**
```
No .env, verifique CLICKUP_TOKEN
Gere um novo em: https://app.clickup.com/settings/apps/
```

---

## 🧪 TESTE RÁPIDO:

1. Abra PowerShell na pasta da automação
2. Execute:
```powershell
python diagnose_detalhado.py
```

3. Se a task aparecer com "🎯 SERIA PROCESSADA!" → Pode ser erro de status/responsável
4. Se não aparecer → Verifique os motivos listados

---

## ✅ CHECKLIST ANTES DE CHAMAR SUPORTE:

- [ ] Task status = "em rascunho"?
- [ ] Task sem responsável?
- [ ] Campo "Ação" preenchido?
- [ ] Rodou diagnóstico?
- [ ] Verificou logs do diagnóstico?
- [ ] Testou com teste_sem_horario.py?

