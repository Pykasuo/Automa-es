import os
import sys
import requests
from dotenv import load_dotenv
import unicodedata

load_dotenv()

# =========================
# ClickUp config
# =========================
CLICKUP_TOKEN = os.getenv("CLICKUP_TOKEN")
CLICKUP_LIST_ID = os.getenv("CLICKUP_LIST_ID") or "901324341007"
CLICKUP_BASE_URL = os.getenv("CLICKUP_BASE_URL", "https://api.clickup.com/api/v2" )

CLICKUP_STATUS_TODO = (os.getenv("CLICKUP_STATUS_TODO") or "em rascunho").strip().lower()
CLICKUP_STATUS_DONE = (os.getenv("CLICKUP_STATUS_DONE") or "finalizada").strip().lower()

FIELD_ACAO_ID = os.getenv("CLICKUP_FIELD_ACAO_ID") or "a6a965c2-01f2-444a-afbc-570e85b3b6d7"
FIELD_CHAMADOS_ID = os.getenv("CLICKUP_FIELD_CHAMADOS_ID") or "ed01473c-8b23-4230-b8f1-a25a15ba7bce"

if not CLICKUP_TOKEN:
    sys.exit("❌ Falta CLICKUP_TOKEN no .env. Por favor, configure-o.")

def headers():
    return {
        "Authorization": CLICKUP_TOKEN,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

def cu_get(url, params=None):
    try:
        r = requests.get(url, headers=headers(), params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
        sys.exit(1)

def main():
    print("\n--- DIAGNÓSTICO CLICKUP (CORRIGIDO) ---")

    # 1. Detalhes da Lista e Status
    print(f"Buscando detalhes da lista {CLICKUP_LIST_ID}...")
    list_details = cu_get(f"{CLICKUP_BASE_URL}/list/{CLICKUP_LIST_ID}")
    
    print("\n1. Detalhes da Lista:")
    print(f"   Nome da Lista: {list_details.get('name')}")
    print("   Status disponíveis na lista:")
    statuses = list_details.get('statuses') or []
    for s in statuses:
        print(f"     - {s.get('status')} (type: {s.get('type')})")
    
    print(f"\n   Configuração atual no .env:")
    print(f"     Status TODO esperado: '{CLICKUP_STATUS_TODO}'")

    # 2. Campos Customizados
    print(f"\n2. Verificando Campos Customizados:")
    fields_def = cu_get(f"{CLICKUP_BASE_URL}/list/{CLICKUP_LIST_ID}/field").get('fields') or []
    
    found_acao = False
    found_chamados = False
    for f in fields_def:
        fid = f.get('id')
        fname = f.get('name')
        if fid == FIELD_ACAO_ID:
            print(f"   ✅ Campo 'Ação' encontrado: {fname} (ID: {fid})")
            found_acao = True
        if fid == FIELD_CHAMADOS_ID:
            print(f"   ✅ Campo 'Chamados' encontrado: {fname} (ID: {fid})")
            found_chamados = True
    
    if not found_acao: print(f"   ⚠️ Campo Ação (ID: {FIELD_ACAO_ID}) NÃO ENCONTRADO!")
    if not found_chamados: print(f"   ⚠️ Campo Chamados (ID: {FIELD_CHAMADOS_ID}) NÃO ENCONTRADO!")

    # 3. Análise de Tarefas
    print(f"\n3. Analisando tarefas atuais:")
    tasks_data = cu_get(f"{CLICKUP_BASE_URL}/list/{CLICKUP_LIST_ID}/task", params={"include_closed": "false"})
    tasks = tasks_data.get('tasks') or []
    
    for t in tasks:
        t_id = t.get('id')
        t_name = t.get('name')
        t_status = (t.get('status', {}).get('status') or "").strip().lower()
        t_assignees = t.get('assignees') or []
        
        print(f"\n   Task: {t_name} ({t_id})")
        print(f"     Status atual: '{t_status}'")
        print(f"     Responsáveis: {len(t_assignees)}")
        
        # Lógica de filtro do robô
        check_status = (t_status == CLICKUP_STATUS_TODO)
        check_assignee = (len(t_assignees) == 0)
        
        if check_status and check_assignee:
            print("     ✅ Esta task SERIA processada pelo robô.")
        else:
            motivo = []
            if not check_status: motivo.append(f"status '{t_status}' != '{CLICKUP_STATUS_TODO}'")
            if not check_assignee: motivo.append("tem responsável atribuído")
            print(f"     ❌ Ignorada por: {', '.join(motivo)}")

    print("\n--- FIM DO DIAGNÓSTICO ---")

if __name__ == "__main__":
    main()