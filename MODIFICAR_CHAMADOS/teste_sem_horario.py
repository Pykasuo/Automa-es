# -*- coding: utf-8 -*-
"""
TESTE - Versão do script SEM restrição de horário (útil para debug)
Use este arquivo para testar o robô independente do horário
"""

import os
import re
import sys
import time
import unicodedata
import requests
import oracledb
import socket
from dotenv import load_dotenv
from datetime import datetime, time as dt_time

load_dotenv()

# =========================
# ClickUp config
# =========================
CLICKUP_TOKEN = os.getenv("CLICKUP_TOKEN")
CLICKUP_LIST_ID = os.getenv("CLICKUP_LIST_ID") or "901324341007"
CLICKUP_BASE_URL = os.getenv("CLICKUP_BASE_URL", "https://api.clickup.com/api/v2")

CLICKUP_STATUS_TODO = (os.getenv("CLICKUP_STATUS_TODO") or "em rascunho").strip().lower()
CLICKUP_STATUS_DONE = (os.getenv("CLICKUP_STATUS_DONE") or "finalizada").strip().lower()

FIELD_ACAO_ID = os.getenv("CLICKUP_FIELD_ACAO_ID") or "a6a965c2-01f2-444a-afbc-570e85b3b6d7"
FIELD_CHAMADOS_ID = os.getenv("CLICKUP_FIELD_CHAMADOS_ID") or "ed01473c-8b23-4230-b8f1-a25a15ba7bce"

if not CLICKUP_TOKEN:
    sys.exit("❌ Falta CLICKUP_TOKEN no .env")

# =========================
# Oracle config
# =========================
ORACLE_USER = os.getenv("ORACLE_USER")
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD")
ORACLE_DSN = os.getenv("ORACLE_DSN")
ORACLE_CLIENT = os.getenv("ORACLE_CLIENT")

if not ORACLE_USER or not ORACLE_PASSWORD or not ORACLE_DSN:
    sys.exit("❌ Faltam variáveis Oracle no .env: ORACLE_USER, ORACLE_PASSWORD, ORACLE_DSN")

if not ORACLE_CLIENT:
    print("⚠️ ORACLE_CLIENT não configurado no .env (pasta do Instant Client).")
    print("ℹ️ O script tentará usar o Oracle Client do sistema ou modo thin.")
else:
    try:
        oracledb.init_oracle_client(lib_dir=ORACLE_CLIENT)
        print(f"✅ Oracle Client inicializado: {ORACLE_CLIENT}")
    except Exception as e:
        print(f"⚠️ Erro ao inicializar Oracle Client: {e}")
        print("ℹ️ O script tentará usar o modo thin (conexão direta sem cliente local).")

# =========================
# Utils
# =========================
def norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))

# =========================
# Oracle functions
# =========================
def criar_conexao_oracle():
    try:
        print(f"Tentando conectar com: {ORACLE_DSN}")
        conn = oracledb.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=ORACLE_DSN)
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM DUAL")
            if cursor.fetchone()[0] == 1:
                print("✅ Conexão e teste bem-sucedidos")
        return conn
    except oracledb.DatabaseError as e:
        error, = e.args
        print(f"⚠️ Falha na conexão: {error.message}")
    print("❌ Não foi possível conectar ao banco de dados")
    return None

def executar_procedure(conn, numero, tipo):
    with conn.cursor() as cursor:
        if tipo == "CANCELAR":
            print(f"Executando: aero.pkg_nivel1.cancelar_chamado('{numero}')")
            cursor.callproc("aero.pkg_nivel1.cancelar_chamado", [numero])
        elif tipo == "REABRIR":
            print(f"Executando: aero.pkg_nivel1.abrir_chamado('{numero}')")
            cursor.callproc("aero.pkg_nivel1.abrir_chamado", [numero])
    conn.commit()

# =========================
# ClickUp API helpers
# =========================
def headers():
    return {
        "Authorization": CLICKUP_TOKEN,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

def cu_get(url, params=None):
    max_tentativas = 3
    delay_inicial = 2
    for tentativa in range(max_tentativas):
        try:
            r = requests.get(url, headers=headers(), params=params, timeout=30)
            if r.status_code != 200:
                raise RuntimeError(f"❌ GET {url} -> {r.status_code} - {r.text}")
            return r.json()
        except (socket.gaierror, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if tentativa < max_tentativas - 1:
                delay = delay_inicial * (2 ** tentativa)
                print(f"⚠️ Erro de conexão (tentativa {tentativa+1}/{max_tentativas}): {type(e).__name__}. Aguardando {delay}s...")
                time.sleep(delay)
            else:
                raise RuntimeError(f"❌ GET {url} falhou após {max_tentativas} tentativas: {e}")
        except Exception as e:
            raise RuntimeError(f"❌ GET {url} -> Erro inesperado: {e}")

def cu_post(url, payload):
    max_tentativas = 3
    delay_inicial = 2
    for tentativa in range(max_tentativas):
        try:
            r = requests.post(url, headers=headers(), json=payload, timeout=30)
            if r.status_code not in (200, 201):
                raise RuntimeError(f"❌ POST {url} -> {r.status_code} - {r.text}")
            return r.json() if r.text else {}
        except (socket.gaierror, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if tentativa < max_tentativas - 1:
                delay = delay_inicial * (2 ** tentativa)
                print(f"⚠️ Erro de conexão (tentativa {tentativa+1}/{max_tentativas}): {type(e).__name__}. Aguardando {delay}s...")
                time.sleep(delay)
            else:
                raise RuntimeError(f"❌ POST {url} falhou após {max_tentativas} tentativas: {e}")
        except Exception as e:
            raise RuntimeError(f"❌ POST {url} -> Erro inesperado: {e}")

def cu_put(url, payload):
    max_tentativas = 3
    delay_inicial = 2
    for tentativa in range(max_tentativas):
        try:
            r = requests.put(url, headers=headers(), json=payload, timeout=30)
            if r.status_code not in (200, 204):
                raise RuntimeError(f"❌ PUT {url} -> {r.status_code} - {r.text}")
            return r.json() if r.text else {}
        except (socket.gaierror, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if tentativa < max_tentativas - 1:
                delay = delay_inicial * (2 ** tentativa)
                print(f"⚠️ Erro de conexão (tentativa {tentativa+1}/{max_tentativas}): {type(e).__name__}. Aguardando {delay}s...")
                time.sleep(delay)
            else:
                raise RuntimeError(f"❌ PUT {url} falhou após {max_tentativas} tentativas: {e}")
        except Exception as e:
            raise RuntimeError(f"❌ PUT {url} -> Erro inesperado: {e}")

def list_fields():
    return (cu_get(f"{CLICKUP_BASE_URL}/list/{CLICKUP_LIST_ID}/field").get("fields") or [])

def get_list_statuses():
    """Busca os status reais da lista para evitar erro de 'Status does not exist'"""
    data = cu_get(f"{CLICKUP_BASE_URL}/list/{CLICKUP_LIST_ID}")
    return data.get("statuses") or []

def find_real_status_name(target_name, statuses):
    """Tenta encontrar o nome exato do status na lista do ClickUp"""
    target_norm = norm(target_name)
    for s in statuses:
        status_real = s.get("status", "")
        if norm(status_real) == target_norm:
            return status_real
    return None

def get_tasks():
    url = f"{CLICKUP_BASE_URL}/list/{CLICKUP_LIST_ID}/task"
    page = 0
    tasks = []
    while True:
        data = cu_get(url, params={"include_closed": "false", "page": page, "subtasks": "true"})
        batch = data.get("tasks") or []
        tasks.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return tasks

def get_task(task_id: str):
    return cu_get(f"{CLICKUP_BASE_URL}/task/{task_id}")

def add_comment(task_id: str, text: str):
    cu_post(f"{CLICKUP_BASE_URL}/task/{task_id}/comment", {"comment_text": text, "notify_all": False})

def update_status(task_id: str, new_status: str):
    cu_put(f"{CLICKUP_BASE_URL}/task/{task_id}", {"status": new_status})

# =========================
# Dropdown decoding
# =========================
def build_dropdown_option_maps(fields_def):
    maps = {}
    for f in fields_def:
        fid = f.get("id")
        if not fid: continue
        tc = f.get("type_config") or {}
        opts = tc.get("options") or []
        if not isinstance(opts, list) or not opts: continue
        by_id = {}
        by_index = []
        for o in opts:
            oid = o.get("id")
            oname = (o.get("name") or "").strip()
            by_index.append(oname)
            if oid is not None: by_id[str(oid)] = oname
        maps[fid] = {"by_id": by_id, "by_index": by_index}
    return maps

def decode_dropdown(value, field_map):
    if value is None: return ""
    if not field_map: return str(value).strip()
    by_id = field_map.get("by_id", {})
    by_index = field_map.get("by_index", [])
    v = str(value).strip()
    if v in by_id: return by_id[v]
    idx = None
    if isinstance(value, int): idx = value
    elif isinstance(value, str) and value.isdigit(): idx = int(value)
    if idx is not None and by_index:
        if 0 <= idx < len(by_index): return by_index[idx]
        if 1 <= idx <= len(by_index): return by_index[idx - 1]
    return v

# =========================
# Form decoding
# =========================
def get_custom_field_value(task, field_id: str):
    for cf in (task.get("custom_fields") or []):
        if cf.get("id") == field_id: return cf.get("value")
    return None

def extrair_tipo_e_chamados(task, dropdown_maps):
    acao_val = get_custom_field_value(task, FIELD_ACAO_ID)
    acao_txt = decode_dropdown(acao_val, dropdown_maps.get(FIELD_ACAO_ID))
    a = norm(acao_txt)
    tipo = None
    if ("cancel" in a) or ("cancelar" in a): tipo = "CANCELAR"
    elif ("reabr" in a) or ("reabrir" in a): tipo = "REABRIR"
    chamados_raw = get_custom_field_value(task, FIELD_CHAMADOS_ID)
    if not isinstance(chamados_raw, str): chamados_raw = "" if chamados_raw is None else str(chamados_raw)
    chamados = []
    if chamados_raw.strip():
        parts = [p.strip() for p in chamados_raw.split(",") if p.strip()]
        for p in parts:
            if p.isdigit() and 6 <= len(p) <= 15: chamados.append(p)
        if not chamados: chamados = re.findall(r"(?<!\d)(\d{6,15})(?!\d)", chamados_raw)
    return tipo, chamados, acao_txt, chamados_raw

# =========================
# Filters / Schedule (SEM RESTRIÇÃO DE HORÁRIO PARA TESTE)
# =========================
def task_candidata_basico(t, status_todo_real):
    status_name = ((t.get("status") or {}).get("status") or "").strip().lower()
    assignees = t.get("assignees") or []
    
    # Debug: mostrar informações da task
    task_id = t.get("id", "???")
    task_name = (t.get("name") or "sem nome").strip()
    
    match_status = (status_name == status_todo_real)
    match_assignee = (len(assignees) == 0)
    
    print(f"   [DEBUG] Task '{task_name[:50]}' - Status: '{status_name}' (esperado: '{status_todo_real}') | Assignees: {len(assignees)}")
    
    if not match_status:
        print(f"           ❌ Status não coincide")
    if not match_assignee:
        print(f"           ❌ Tem {len(assignees)} responsável(is): {[a.get('username', 'desconhecido') for a in assignees]}")
    
    return match_status and match_assignee

# =========================
# Main
# =========================
def main():
    print("\n" + "="*80)
    print("🧪 TESTE DA AUTOMAÇÃO (SEM RESTRIÇÃO DE HORÁRIO)")
    print("="*80 + "\n")
    
    print("🔌 Iniciando conexão com Oracle...")
    conn = criar_conexao_oracle()
    if conn is None: sys.exit("❌ Encerrando script por erro de conexão.")

    print("📌 Validando status da lista no ClickUp...")
    status_todo_real = CLICKUP_STATUS_TODO
    status_done_real = CLICKUP_STATUS_DONE
    
    try:
        all_statuses = get_list_statuses()
        status_todo_real = find_real_status_name(CLICKUP_STATUS_TODO, all_statuses) or CLICKUP_STATUS_TODO
        
        status_done_real = find_real_status_name("concluída", all_statuses)
        if not status_done_real:
            status_done_real = find_real_status_name("finalizada", all_statuses)
        
        if not status_done_real:
            for s in all_statuses:
                if s.get("type") in ["done", "closed"] and norm(s.get("status")) != "cancelada":
                    status_done_real = s.get("status")
                    break
        
        if not status_done_real:
            status_done_real = CLICKUP_STATUS_DONE

        print(f"✅ Status TODO mapeado para: '{status_todo_real}'")
        print(f"✅ Status DONE mapeado para: '{status_done_real}'")
    except Exception as e:
        print(f"⚠️ Erro ao validar status: {e}. Usando padrões.")

    print("📌 Carregando definição de campos...")
    try:
        fields_def = list_fields()
        dropdown_maps = build_dropdown_option_maps(fields_def)
        print("✅ Campos carregados com sucesso")
    except Exception as e:
        print(f"⚠️ Erro ao carregar campos: {e}")
        dropdown_maps = {}

    try:
        print(f"\n⏰ Verificação em {datetime.now().strftime('%H:%M:%S')}")
        try:
            tasks = get_tasks()
            candidatos = [t for t in tasks if task_candidata_basico(t, status_todo_real)]

            if not candidatos:
                print(f"⚠️ Nenhuma task candidata (status '{status_todo_real}' + sem responsável).")
            else:
                print(f"✅ {len(candidatos)} task(s) candidata(s) encontrada(s)!")
                for t in candidatos:
                    task_id = t.get("id")
                    if not task_id: continue
                    try:
                        task = get_task(task_id)
                        nome = (task.get("name") or "").strip()
                        print(f"\n🔍 Task {task_id} - {nome}")
                        
                        task_statuses = task.get("status", {}).get("status")
                        print(f"   Status atual da task: '{task_statuses}'")
                        
                        tipo, chamados, acao_txt, chamados_raw = extrair_tipo_e_chamados(task, dropdown_maps)
                        if not tipo:
                            print(f"⚠️ Não identifiquei ação no campo (valor='{acao_txt}'). Pulando.")
                            continue
                        if not chamados:
                            print(f"⚠️ Não encontrei chamados válidos. Pulando.")
                            continue

                        print(f"➡️  Ação: {tipo} ({acao_txt}) | Chamados: {', '.join(chamados)}")
                        erros = 0
                        for numero in chamados:
                            print(f"⚙️  Executando {tipo.lower()} chamado {numero}")
                            try:
                                executar_procedure(conn, numero, tipo)
                            except Exception as e:
                                erros += 1
                                print(f"❌ Erro ao executar procedure para {numero}: {e}")

                        try:
                            if erros == 0:
                                msg = "Chamados cancelados." if tipo == "CANCELAR" else "Chamados reabertos."
                                add_comment(task_id, msg)
                                
                                print(f"⚙️  Tentando mover para status: '{status_done_real}'")
                                update_status(task_id, status_done_real)
                                print(f"✅ Task movida para '{status_done_real}'.")
                            else:
                                add_comment(task_id, f"⚠️ Processamento concluído com {erros} erro(s).")
                                print("⚠️ Houve erro(s). Mantendo status.")
                        except Exception as e:
                            print(f"❌ Erro ao atualizar ClickUp na task {task_id}: {e}")
                    except Exception as e:
                        print(f"❌ Erro ao processar task {task_id}: {e}")
                        continue
        except Exception as e:
            print(f"⚠️ Erro na iteração de verificação: {e}")

    except KeyboardInterrupt:
        print("\n🛑 Script interrompido")
    finally:
        conn.close()
        print("\n✅ Conexão Oracle fechada.")

if __name__ == "__main__":
    print(f"🚀 Iniciando script de TESTE em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    main()
