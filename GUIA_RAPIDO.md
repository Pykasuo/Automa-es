# 📋 GUIA RÁPIDO - POR QUE O CARD NÃO ESTÁ SENDO PROCESSADO?

## 🚨 SEU PROBLEMA:
> "Há um card no clickup para reabrir chamados, porém a automação não está buscando ele"

---

## ⚡ SOLUÇÃO RÁPIDA (5 MINUTOS):

### Passo 1: Abra o ClickUp
```
Vá até: https://app.clickup.com/
```

### Passo 2: Encontre a task
```
Liste > Procure pela task que não está sendo processada
```

### Passo 3: Verifique essas 3 coisas:
```
✓ Status = "em rascunho" (não é "finalizada", "cancelada", etc)
✓ Sem responsável (ninguém atribuído à task)
✓ Campo "Ação" = "REABRIR" (ou "CANCELAR")
```

### Passo 4: Se algo estiver errado
```
❌ Status errado? → Clique no status e mude para "em rascunho"
❌ Tem responsável? → Remova clicando no Assignee
❌ Campo vazio? → Preencha com "REABRIR"
```

### Passo 5: Teste
```powershell
cd "c:\Users\user\Downloads\N2\automações N2\automações N2\Automação - Modificar chamados"
python diagnose_detalhado.py
```

Se aparecer ✅ sua task, deve estar funcionando!

---

## 📊 CHECKLIST VISUAL:

```
┌─────────────────────────────────────────┐
│ VERIFICAÇÃO RÁPIDA NO CLICKUP           │
├─────────────────────────────────────────┤
│                                         │
│ Status = "em rascunho"      ☐ OK ☐ ERR │
│ Sem responsável             ☐ OK ☐ ERR │
│ Ação = "REABRIR"            ☐ OK ☐ ERR │
│ Chamado válido (6-15 dig)   ☐ OK ☐ ERR │
│ Horário 08h-18h (com break) ☐ OK ☐ N/A │
│                                         │
└─────────────────────────────────────────┘
```

Se todos marcarem OK → Testa a automação!

---

## 🔧 FERRAMENTAS DE DEBUG:

### Opção 1: Diagnóstico Detalhado
```powershell
python diagnose_detalhado.py
```
✅ Mostra todas as tasks e por que cada uma é ignorada

### Opção 2: Teste Sem Horário
```powershell
python teste_sem_horario.py
```
✅ Executa sem restrição de horário (útil para testes)

### Opção 3: Diagnóstico Original
```powershell
python diagnose_clickup.py
```
✅ Versão mais simples do diagnóstico

---

## 💡 DICAS IMPORTANTES:

1. **O script só roda entre 08:00-12:00 e 13:00-18:00**
   → Use `teste_sem_horario.py` para testar fora disso

2. **Status deve ser EXATO**
   → "em rascunho" ✅
   → "Em Rascunho" ❌
   → "rascunho" ❌

3. **Não pode ter responsável**
   → Remova antes de testar

4. **Campo "Ação" reconhece:**
   → "CANCELAR" ou "REABRIR" (qualquer variação funciona)
   → Detecta automaticamente

---

## 📞 AINDA NÃO FUNCIONA?

Execute na sequência:
```powershell
# 1. Diagnóstico detalhado
python diagnose_detalhado.py

# 2. Copie a saída
# 3. Envie junto com:
#    - Screenshot do ClickUp mostrando a task
#    - Output do diagnóstico
```

