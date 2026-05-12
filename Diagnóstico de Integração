# -*- coding: utf-8 -*-
"""
Script para diagnosticar por que as tasks não estão sendo processadas
"""
import os
import sys
import requests
import unicodedata
from dotenv import load_dotenv
from datetime import datetime, time as dt_time

load_dotenv()

CLICKUP_TOKEN = os.getenv("CLICKUP_TOKEN")
CLICKUP_LIST_ID = os.getenv("CLICKUP_LIST_ID") or "901324341007"
CLICKUP_BASE_URL = os.getenv("CLICKUP_BASE_URL", "https://api.clickup.com/api/v2")

CLICKUP_STATUS_TODO = (os.getenv("CLICKUP_STATUS_TODO") or "em rascunho").strip().lower()
CLICKUP_STATUS_DONE = (os.getenv("CLICKUP_STATUS_DONE") or "finalizada").strip().lower()

FIELD_ACAO_ID = os.getenv("CLICKUP_FIELD_ACAO_ID") or "a6a965c2-01f2-444a-afbc-570e85b3b6d7"
FIELD_CHAMADOS_ID = os.getenv("CLICKUP_FIELD_CHAMADOS_ID") or "ed01473c-8b23-4230-b8f1-a25a15ba7bce"

if not CLICKUP_TOKEN:
    sys.exit("❌ Falta CLICKUP_TOKEN no .env")

def norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))

def headers():
    return {
        "Authorization": CLICKUP_TOKEN,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

def cu_get(url, params=None):
    r = requests.get(url, headers=headers(), params=params, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"❌ GET {url} -> {r.status_code} - {r.text}")
    return r.json()

def dentro_do_horario_comercial():
    agora = datetime.now().time()
    manha_inicio = dt_time(8, 0)
    manha_fim = dt_time(12, 0)
    tarde_inicio = dt_time(13, 0)
    tarde_fim = dt_time(18, 0)
    
    em_manha = (manha_inicio <= agora <= manha_fim)
    em_tarde = (tarde_inicio <= agora <= tarde_fim)
    
    return em_manha or em_tarde

def main():
    print("\n" + "="*80)
    print("🔍 DIAGNÓSTICO DETALHADO - CLICKUP")
    print("="*80)
    
    # Check horário
    agora = datetime.now()
    em_horario = dentro_do_horario_comercial()
    print(f"\n⏰ HORÁRIO COMERCIAL:")
    print(f"   Hora atual: {agora.strftime('%H:%M:%S')} ({agora.strftime('%A')})")
    print(f"   Em horário comercial? {'✅ SIM' if em_horario else '❌ NÃO (o script só rodará entre 08h-12h ou 13h-18h)'}")
    
    # Validar status
    print(f"\n📌 CONFIGURAÇÕES .env:")
    print(f"   CLICKUP_LIST_ID: {CLICKUP_LIST_ID}")
    print(f"   CLICKUP_STATUS_TODO: '{CLICKUP_STATUS_TODO}'")
    print(f"   CLICKUP_STATUS_DONE: '{CLICKUP_STATUS_DONE}'")
    print(f"   FIELD_ACAO_ID: {FIELD_ACAO_ID}")
    print(f"   FIELD_CHAMADOS_ID: {FIELD_CHAMADOS_ID}")
    
    # Get list details
    print(f"\n📋 BUSCANDO DETALHES DA LISTA...")
    try:
        list_data = cu_get(f"{CLICKUP_BASE_URL}/list/{CLICKUP_LIST_ID}")
        print(f"   ✅ Lista: {list_data.get('name')}")
        
        statuses = list_data.get('statuses') or []
        print(f"\n   Status disponíveis na lista:")
        for s in statuses:
            print(f"      - '{s.get('status')}' (type: {s.get('type')})")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return
    
    # Get all tasks
    print(f"\n📑 BUSCANDO TODAS AS TASKS...")
    try:
        tasks_data = cu_get(f"{CLICKUP_BASE_URL}/list/{CLICKUP_LIST_ID}/task", params={"include_closed": "false"})
        all_tasks = tasks_data.get('tasks') or []
        print(f"   Total de tasks abertas: {len(all_tasks)}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return
    
    if not all_tasks:
        print("   ⚠️ Nenhuma task encontrada na lista!")
        return
    
    # Analyze each task
    print(f"\n📊 ANÁLISE DETALHADA DE CADA TASK:")
    print("-" * 80)
    
    candidatas = 0
    
    for idx, t in enumerate(all_tasks, 1):
        t_id = t.get('id')
        t_name = (t.get('name') or "").strip()
        t_status = (t.get('status', {}).get('status') or "").strip().lower()
        t_assignees = t.get('assignees') or []
        
        print(f"\n{idx}. Task: '{t_name}' ({t_id})")
        print(f"   Status: '{t_status}' (esperado: '{CLICKUP_STATUS_TODO}')")
        print(f"   Responsáveis: {len(t_assignees)}", end="")
        if t_assignees:
            print(f" - {[a.get('username', '?') for a in t_assignees]}")
        else:
            print(" (nenhum)")
        
        # Check criteria
        match_status = (t_status == CLICKUP_STATUS_TODO)
        match_assignee = (len(t_assignees) == 0)
        
        print(f"   ✓ Status match: {'✅' if match_status else '❌'}")
        print(f"   ✓ Sem assignee: {'✅' if match_assignee else '❌'}")
        
        # If candidate, show more details
        if match_status and match_assignee:
            candidatas += 1
            print(f"   🎯 SERIA PROCESSADA!")
            
            # Get full task details
            try:
                full_task = cu_get(f"{CLICKUP_BASE_URL}/task/{t_id}")
                
                # Get custom fields
                custom_fields = full_task.get('custom_fields') or []
                print(f"\n   📝 CAMPOS CUSTOMIZADOS:")
                
                for cf in custom_fields:
                    cf_id = cf.get('id')
                    cf_name = cf.get('name')
                    cf_value = cf.get('value')
                    
                    if cf_id == FIELD_ACAO_ID:
                        print(f"      - Ação: '{cf_value}' (ID: {cf_name})")
                    elif cf_id == FIELD_CHAMADOS_ID:
                        print(f"      - Chamados: '{cf_value}' (ID: {cf_name})")
            except Exception as e:
                print(f"   ❌ Erro ao buscar detalhes: {e}")
        else:
            motivos = []
            if not match_status:
                motivos.append(f"Status '{t_status}' != '{CLICKUP_STATUS_TODO}'")
            if not match_assignee:
                motivos.append(f"{len(t_assignees)} responsável(is)")
            print(f"   ❌ NÃO seria processada: {' | '.join(motivos)}")
    
    print("\n" + "="*80)
    print(f"✅ RESUMO: {candidatas} task(s) candidata(s) para processar")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
