# -*- coding: utf-8 -*-
"""
ROBÔ ClickUp (Form) -> Oracle (pkg_nivel1)

Regras:
- Só processa tasks da LISTA configurada
- Só processa tasks com status = CLICKUP_STATUS_TODO (default: rascunho)
- Só processa tasks sem assignee
- Identifica ação pelo Custom Field dropdown "Ação no chamado" (FIELD_ACAO_ID)
  - aceita value como UUID da opção OU como índice (0/1-based)
- Extrai chamados do Custom Field texto "Número dos chamados" (FIELD_CHAMADOS_ID)
  - formato preferido: CSV por vírgula (ex: 121212,3243352,224141)
  - fallback: regex 6-15 dígitos
- Executa procedure:
  - CANCELAR -> aero.pkg_nivel1.cancelar_chamado
  - REABRIR  -> aero.pkg_nivel1.abrir_chamado
- Comenta na task e move status para CLICKUP_STATUS_DONE (default: concluído) se sucesso
"""

import os
import re
import sys
import time
import unicodedata
import requests
import oracledb
from dotenv import load_dotenv
from datetime import datetime, time as dt_time

load_dotenv()

# =========================
# ClickUp config
# =========================
CLICKUP_TOKEN = os.getenv("CLICKUP_TOKEN")
CLICKUP_LIST_ID = os.getenv("CLICKUP_LIST_ID") or "901324341007"
CLICKUP_BASE_URL = os.getenv("CLICKUP_BASE_URL", "https://api.clickup.com/api/v2")

CLICKUP_STATUS_TODO = (os.getenv("CLICKUP_STATUS_TODO") or "rascunho").strip().lower()
CLICKUP_STATUS_DONE = (os.getenv("CLICKUP_STATUS_DONE") or "concluído").strip().lower()

# Custom Field IDs (da sua lista)
FIELD_ACAO_ID = os.getenv("CLICKUP_FIELD_ACAO_ID") or "a6a965c2-01f2-444a-afbc-570e85b3b6d7"
FIELD_CHAMADOS_ID = os.getenv("CLICKUP_FIELD_CHAMADOS_ID") or "ed01473c-8b23-4230-b8f1-a25a15ba7bce"

# (Opcional) se quiser usar em regras futuras
FIELD_CLIENTE_ID = os.getenv("CLICKUP_FIELD_CLIENTE_ID") or "18c22e59-165d-40f5-9e4c-f0bf41264e30"

if not CLICKUP_TOKEN:
    sys.exit("❌ Falta CLICKUP_TOKEN no .env")

# =========================
# Oracle config
# =========================
ORACLE_USER = os.getenv("ORACLE_USER")
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD")
ORACLE_DSN = os.getenv("ORACLE_DSN")
ORACLE_CLIENT = os.getenv("ORACLE_CLIENT")

if not ORACLE_CLIENT:
    sys.exit("❌ Falta ORACLE_CLIENT no .env (pasta do Instant Client).")

oracledb.init_oracle_client(lib_dir=ORACLE_CLIENT)

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
        if tipo == "REABRIR":
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
    r = requests.get(url, headers=headers(), params=params, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"❌ GET {url} -> {r.status_code} - {r.text}")
    return r.json()

def cu_post(url, payload):
    r = requests.post(url, headers=headers(), json=payload, timeout=30)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"❌ POST {url} -> {r.status_code} - {r.text}")
    return r.json() if r.text else {}

def cu_put(url, payload):
    r = requests.put(url, headers=headers(), json=payload, timeout=30)
    if r.status_code not in (200, 204):
        raise RuntimeError(f"❌ PUT {url} -> {r.status_code} - {r.text}")
    return r.json() if r.text else {}

def list_fields():
    return (cu_get(f"{CLICKUP_BASE_URL}/list/{CLICKUP_LIST_ID}/field").get("fields") or [])

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
# Dropdown decoding (UUID OU índice)
# =========================
def build_dropdown_option_maps(fields_def):
    """
    maps[field_id] = {
        "by_id": { "uuid": "Option Name", ... },
        "by_index": ["Option Name", ...]  # na ordem do ClickUp
    }
    """
    maps = {}
    for f in fields_def:
        fid = f.get("id")
        if not fid:
            continue
        tc = f.get("type_config") or {}
        opts = tc.get("options") or []
        if not isinstance(opts, list) or not opts:
            continue

        by_id = {}
        by_index = []
        for o in opts:
            oid = o.get("id")
            oname = (o.get("name") or "").strip()
            by_index.append(oname)
            if oid is not None:
                by_id[str(oid)] = oname

        maps[fid] = {"by_id": by_id, "by_index": by_index}
    return maps

def decode_dropdown(value, field_map):
    if value is None:
        return ""

    if not field_map:
        return str(value).strip()

    by_id = field_map.get("by_id", {})
    by_index = field_map.get("by_index", [])

    v = str(value).strip()

    # 1) UUID direto
    if v in by_id:
        return by_id[v]

    # 2) Índice numérico (0-based ou 1-based)
    idx = None
    if isinstance(value, int):
        idx = value
    elif isinstance(value, str) and value.isdigit():
        idx = int(value)

    if idx is not None and by_index:
        if 0 <= idx < len(by_index):
            return by_index[idx]
        if 1 <= idx <= len(by_index):
            return by_index[idx - 1]

    return v

# =========================
# Form decoding (by Field IDs)
# =========================
def get_custom_field_value(task, field_id: str):
    for cf in (task.get("custom_fields") or []):
        if cf.get("id") == field_id:
            return cf.get("value")
    return None

def extrair_tipo_e_chamados(task, dropdown_maps):
    """
    Identifica:
      - tipo via dropdown FIELD_ACAO_ID
      - chamados via texto FIELD_CHAMADOS_ID
    """
    # 1) Ação
    acao_val = get_custom_field_value(task, FIELD_ACAO_ID)
    acao_txt = decode_dropdown(acao_val, dropdown_maps.get(FIELD_ACAO_ID))
    a = norm(acao_txt)

    tipo = None
    if ("reabr" in a) or ("reabrir" in a):
        tipo = "REABRIR"

    # 2) Chamados (CSV)
    chamados_raw = get_custom_field_value(task, FIELD_CHAMADOS_ID)
    if not isinstance(chamados_raw, str):
        chamados_raw = "" if chamados_raw is None else str(chamados_raw)

    chamados = []
    if chamados_raw.strip():
        parts = [p.strip() for p in chamados_raw.split(",") if p.strip()]
        for p in parts:
            if p.isdigit() and 6 <= len(p) <= 15:
                chamados.append(p)

        if not chamados:
            chamados = re.findall(r"(?<!\d)(\d{6,15})(?!\d)", chamados_raw)

    return tipo, chamados, acao_txt, chamados_raw

# =========================
# Filters / Schedule
# =========================
def dentro_do_horario_comercial():
    agora = datetime.now().time()
    manha_inicio = dt_time(8, 0)
    manha_fim = dt_time(12, 0)
    tarde_inicio = dt_time(13, 0)
    tarde_fim = dt_time(18, 0)
    return ((manha_inicio <= agora <= manha_fim) or (tarde_inicio <= agora <= tarde_fim))

def task_candidata_basico(t):
    status_name = ((t.get("status") or {}).get("status") or "").strip().lower()
    assignees = t.get("assignees") or []
    return (status_name == CLICKUP_STATUS_TODO) and (not assignees)

# =========================
# Main
# =========================
def main():
    print("🔌 Iniciando conexão com Oracle...")
    conn = criar_conexao_oracle()
    if conn is None:
        sys.exit("❌ Encerrando script por erro de conexão.")

    print("📌 Carregando definição de campos (pra decodificar dropdown)...")
    fields_def = list_fields()
    dropdown_maps = build_dropdown_option_maps(fields_def)

    try:
        while dentro_do_horario_comercial():
            print(f"\n⏰ Verificação em {datetime.now().strftime('%H:%M:%S')}")

            tasks = get_tasks()
            candidatos = [t for t in tasks if task_candidata_basico(t)]

            if not candidatos:
                print("⚠️ Nenhuma task candidata (status alvo + sem responsável).")
            else:
                for t in candidatos:
                    task_id = t.get("id")
                    if not task_id:
                        continue

                    task = get_task(task_id)
                    nome = (task.get("name") or "").strip()

                    print(f"\n🔍 Task {task_id} - {nome}")

                    tipo, chamados, acao_txt, chamados_raw = extrair_tipo_e_chamados(task, dropdown_maps)

                    if not tipo:
                        print(f"⚠️ Não identifiquei ação no campo (valor='{acao_txt}'). Pulando.")
                        continue
                    if not chamados:
                        print(f"⚠️ Não encontrei chamados válidos no campo. Conteúdo='{chamados_raw}'. Pulando.")
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

            print("\n⏳ Aguardando 10 minutos para próxima verificação...")
            time.sleep(600)

    except KeyboardInterrupt:
        print("\n🛑 Script interrompido manualmente pelo usuário")
    finally:
        conn.close()
        print("\n✅ Processamento concluído. Conexão com Oracle fechada.")

if __name__ == "__main__":
    print(f"🚀 Iniciando script em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    main()
    print(f"⏹️ Script finalizado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
