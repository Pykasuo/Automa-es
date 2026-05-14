# 📋 MODIFICAR CHAMADOS - Automação ClickUp -> Oracle

## 📝 Descrição

Automação que processa tasks do ClickUp e executa operações no Oracle:
- **CANCELAR**: Cancela chamados no sistema
- **REABRIR**: Reabre chamados no sistema

## 📁 Arquivos

### Scripts Principais
- `modificar chamados.py` - Script principal (executa entre 08h-12h e 13h-18h)
- `teste_sem_horario.py` - Versão para testes fora do horário comercial

### Ferramentas de Diagnóstico
- `diagnose_detalhado.py` - Diagnóstico completo com análise detalhada
- `diagnose_clickup.py` - Diagnóstico rápido

## 🚀 Como Usar

### 1. Executar a Automação
```powershell
python "modificar chamados.py"
```

### 2. Testar Fora do Horário
```powershell
python teste_sem_horario.py
```

### 3. Diagnosticar Problemas
```powershell
python diagnose_detalhado.py
```

## ✅ Checklist de Configuração

Ante de executar, certifique-se de:

- [ ] Task tem status = "em rascunho"
- [ ] Task **NÃO tem responsável** atribuído
- [ ] Campo "Ação" = "CANCELAR" ou "REABRIR"
- [ ] Campo "Chamados" com números válidos (6-15 dígitos)
- [ ] `.env` contém:
  - `CLICKUP_TOKEN`
  - `ORACLE_USER`
  - `ORACLE_PASSWORD`
  - `ORACLE_DSN`

## 🔍 Troubleshooting

### A task não está sendo processada?

1. **Status errado** (70% dos casos)
   - Verifique se status = "em rascunho"

2. **Task tem responsável** (20% dos casos)
   - Remova o responsável atribuído

3. **Campos vazios** (5% dos casos)
   - Preencha "Ação" e "Chamados"

4. **Fora do horário** (3% dos casos)
   - Use `teste_sem_horario.py`

5. **Credenciais inválidas** (2% dos casos)
   - Gere novo CLICKUP_TOKEN

## 📞 Suporte

Para mais informações, execute o diagnóstico:
```powershell
python diagnose_detalhado.py
```
