# 🔧 TROUBLESHOOTING - POR QUE A TASK NÃO ESTÁ SENDO PROCESSADA?

## ❓ PROBLEMA: O card no ClickUp não está sendo buscado/processado

### 🔍 Checklist de Diagnóstico:

#### 1. ✅ HORÁRIO COMERCIAL
O script **APENAS roda entre 08:00-12:00 e 13:00-18:00**

- Se for fora desse horário, o script não faz nada
- Solução: Mude o horário ou remova essa verificação

```python
# Linha ~340 em modificar chamados.py
def dentro_do_horario_comercial():
    # Mude aqui se quiser testar fora do horário
```

---

#### 2. ✅ STATUS DA TASK NO CLICKUP
A task **DEVE ter status exatamente = "em rascunho"** (configurável no .env)

**Problema comum:** Status está "finalizada", "cancelada" ou outro valor
**Solução:** Verificar o .env e trocar o status da task

```
.env:
CLICKUP_STATUS_TODO=em rascunho    ← Task deve ter esse status
CLICKUP_STATUS_DONE=finalizada     ← Task vai para esse status após sucesso
```

---

#### 3. ✅ RESPONSÁVEL (ASSIGNEE)
A task **NÃO pode ter ninguém atribuído**

**Problema comum:** Alguém foi atribuído à task
**Solução:** Remover o responsável da task no ClickUp

---

#### 4. ✅ CAMPO "AÇÃO"
O campo customizado "Ação no chamado" **deve ter valor "CANCELAR" ou "REABRIR"**

**Problema comum:** Campo vazio ou com valor diferente (ex: "Cancelar", "REABRIR ")
**Solução:** Verificar o campo na task

```
IDs dos campos (verificar no .env):
CLICKUP_FIELD_ACAO_ID=a6a965c2-01f2-444a-afbc-570e85b3b6d7
CLICKUP_FIELD_CHAMADOS_ID=ed01473c-8b23-4230-b8f1-a25a15ba7bce
```

---

#### 5. ✅ CAMPO "CHAMADOS"
O campo customizado "Número dos chamados" **deve conter números válidos (6-15 dígitos)**

**Formatos aceitos:**
- CSV: `123456,234567,345678`
- Solto: `123456 234567 345678`
- Qualquer número 6-15 dígitos será extraído

**Problema comum:** Campo vazio ou com texto inválido
**Solução:** Adicionar números de chamado válidos

---

### 🚀 COMO RODAR O DIAGNÓSTICO:

```powershell
# Abra PowerShell e vá para a pasta do script
cd "c:\Users\user\Downloads\N2\automações N2\automações N2\Automação - Modificar chamados"

# Rode o diagnóstico (requere python3 instalado)
python diagnose_detalhado.py

# Ou use o script original
python diagnose_clickup.py
```

---

### 📋 CHECKLIST ANTES DE EXECUTAR A AUTOMAÇÃO:

- [ ] Task tem status = "em rascunho" (exato)
- [ ] Task **NÃO tem responsável** atribuído
- [ ] Campo "Ação" = "CANCELAR" ou "REABRIR" (exato)
- [ ] Campo "Chamados" tem números 6-15 dígitos
- [ ] Está dentro do horário 08h-12h ou 13h-18h
- [ ] `.env` tem todas as credenciais corretas
- [ ] CLICKUP_TOKEN está válido

---

### 🔧 COMO CORRIGIR PROBLEMAS COMUNS:

#### Problema: "Status não coincide"
```
Solução 1: Trocar status da task no ClickUp para "em rascunho"
Solução 2: Mudar CLICKUP_STATUS_TODO no .env para o status real da task
```

#### Problema: "Tem responsável atribuído"
```
Solução: Ir no ClickUp, abrir a task, remover o responsável
```

#### Problema: "Não identifiquei ação no campo"
```
Solução: Verificar se o campo "Ação" está preenchido com "CANCELAR" ou "REABRIR"
```

#### Problema: "Não encontrei chamados válidos"
```
Solução: Preencher campo "Chamados" com números 6-15 dígitos (ex: 2104260170)
```

---

### 📞 CONTATO / LOGS:
Se o script não funciona, rodar o diagnóstico acima e conferir os logs detalhados que aparecem.

