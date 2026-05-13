import sys
import io
import re
import time
import logging
import subprocess
import requests
import datetime
from typing import List, Dict
from pathlib import Path
from dotenv import load_dotenv
import os
import json
import unicodedata

# -------------------------
# Carrega variáveis do .env
# -------------------------
ENV_PATH = Path(__file__).with_name(".env")
if not ENV_PATH.exists():
    print("[ERRO] Arquivo .env não encontrado em:", ENV_PATH)
    print("Crie o .env nessa pasta com as variáveis necessárias e rode novamente.")
    sys.exit(1)

load_dotenv(dotenv_path=ENV_PATH)

# Configura encoding para UTF-8 (resolve problema com caracteres especiais no Windows)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# --- Configuração de Log ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("automacao_alto_consumo.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# =========================
# ClickUp Config
# =========================
CLICKUP_TOKEN = os.getenv("CLICKUP_TOKEN")
CLICKUP_LIST_ID = os.getenv("CLICKUP_LIST_ID") or "901324341007"
CLICKUP_BASE_URL = os.getenv("CLICKUP_BASE_URL", "https://api.clickup.com/api/v2")

CLICKUP_STATUS_TODO = (os.getenv("CLICKUP_STATUS_TODO") or "em rascunho").strip().lower()
CLICKUP_STATUS_TODO_ALT = (os.getenv("CLICKUP_STATUS_TODO_ALT") or "to do").strip().lower()

# ✅ AJUSTE AQUI: status em português
CLICKUP_STATUS_IN_PROGRESS = (os.getenv("CLICKUP_STATUS_IN_PROGRESS") or "em andamento").strip().lower()

CLICKUP_STATUS_DONE = (os.getenv("CLICKUP_STATUS_DONE") or "finalizada").strip().lower()

if not CLICKUP_TOKEN:
    sys.exit("❌ Falta CLICKUP_TOKEN no .env")

# --- Configurações de Horário ---
INTERVALO_VERIFICACAO = 600  # 10 minutos
HORARIO_INICIO_MANHA = 8
HORARIO_FIM_MANHA = 12
HORARIO_INICIO_TARDE = 13
HORARIO_FIM_TARDE = 18

def dentro_do_horario_permitido():
    agora = datetime.datetime.now()
    h = agora.hour
    return (HORARIO_INICIO_MANHA <= h < HORARIO_FIM_MANHA) or (HORARIO_INICIO_TARDE <= h < HORARIO_FIM_TARDE)

# -------------------------
# Cache local de ajustes
# -------------------------
CACHE_PATH = Path(__file__).with_name("ajustes_cache.json")

def _load_cache() -> Dict[str, str]:
    try:
        if CACHE_PATH.exists():
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Não foi possível carregar cache: {e}")
    return {}

def _save_cache(cache: Dict[str, str]) -> None:
    try:
        tmp = CACHE_PATH.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        tmp.replace(CACHE_PATH)
    except Exception as e:
        logger.error(f"Falha ao salvar cache: {e}")

def _cache_key(task_id: str, device_type: str, imei: str) -> str:
    return f"{task_id}:{device_type}:{imei}"

# -------------------------
# Utilidades
# -------------------------
def _norm(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.strip().lower()

# -------------------------
# ClickUp API
# -------------------------
def _cu_headers():
    return {
        "Authorization": CLICKUP_TOKEN,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

def _cu_get(url: str, params=None) -> dict:
    r = requests.get(url, headers=_cu_headers(), params=params, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"❌ GET {url} -> {r.status_code} - {r.text}")
    return r.json()

def _cu_post(url: str, payload: dict) -> dict:
    r = requests.post(url, headers=_cu_headers(), json=payload, timeout=30)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"❌ POST {url} -> {r.status_code} - {r.text}")
    return r.json() if r.text else {}

def _cu_put(url: str, payload: dict) -> dict:
    r = requests.put(url, headers=_cu_headers(), json=payload, timeout=30)
    if r.status_code not in (200, 204):
        raise RuntimeError(f"❌ PUT {url} -> {r.status_code} - {r.text}")
    return r.json() if r.text else {}

def get_clickup_tasks() -> List[Dict]:
    """
    Busca tasks da lista e filtra:
    - name contém "Alto consumo"
    - status em {em rascunho, to do, em andamento}
    """
    url = f"{CLICKUP_BASE_URL}/list/{CLICKUP_LIST_ID}/task"
    page = 0
    tasks = []

    while True:
        data = _cu_get(url, params={"include_closed": "false", "page": page, "subtasks": "true"})
        batch = data.get("tasks") or []
        tasks.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    wanted_status = {CLICKUP_STATUS_TODO, CLICKUP_STATUS_TODO_ALT, CLICKUP_STATUS_IN_PROGRESS}
    out = []
    for t in tasks:
        name = _norm(t.get("name", ""))
        status = _norm(((t.get("status") or {}).get("status") or ""))
        if "alto consumo" not in name:
            continue
        if status not in wanted_status:
            continue
        out.append(t)
    return out

def get_clickup_task_full(task_id: str) -> Dict:
    return _cu_get(f"{CLICKUP_BASE_URL}/task/{task_id}")

def add_clickup_comment(task_id: str, message: str) -> bool:
    try:
        _cu_post(f"{CLICKUP_BASE_URL}/task/{task_id}/comment", {"comment_text": message, "notify_all": False})
        return True
    except Exception as e:
        logger.error(f"Erro ao comentar task {task_id}: {e}")
        return False

def set_clickup_status(task_id: str, status_name: str) -> bool:
    try:
        _cu_put(f"{CLICKUP_BASE_URL}/task/{task_id}", {"status": status_name})
        logger.info(f"Status atualizado: task={task_id} -> '{status_name}'")
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar status da task {task_id} para '{status_name}': {e}")
        return False

# -------------------------
# Parsing descrição e extração de equipamentos
# -------------------------
def extract_equipments_from_text(raw_text: str) -> List[Dict[str, str]]:
    """
    Aceita pares tipo/imei com separador ';' OU ','
    """
    if not raw_text:
        return []

    text = raw_text.replace("\r", "\n")
    pattern = r"\b((?:K1|K4|G5|G7)\+?)\s*[;,]\s*(\d{8,})\b"
    matches = re.findall(pattern, text, flags=re.IGNORECASE)

    equipments = []
    for tipo, imei in matches:
        tipo = tipo.upper().replace("+", "PLUS")
        tipo_map = {
            "K1": "k1",
            "K1PLUS": "k1+",
            "K4": "k4",
            "G5": "g5",
            "G5PLUS": "g5+",
            "G7": "g7",
        }
        if tipo in tipo_map:
            equipments.append({"tipo": tipo_map[tipo], "imei": imei.strip()})
    return equipments

# -------------------------
# Execução de comandos por dispositivo
# -------------------------
def execute_device_command(device_type: str, imei: str) -> bool:
    py = sys.executable

    command_map = {
        "k1": [py, "comandos_k1_lib.py"],
        "k1+": [py, "comandos_k1plus_lib.py"],
        "k1+_ambiente_k1": [py, "comandos_k1plus_ambiente_k1_lib.py"],
        "k4": [py, "comandos_k4_lib.py"],
        "g5": [py, "comandos_g5_lib.py"],
        "g5+": [py, "comandos_g5plus_lib.py"],
        "g7": [py, "comandos_g7_lib.py"],
    }
    if device_type not in command_map:
        logger.error(f"Tipo de dispositivo inválido: {device_type}")
        return False

    def _run(cmd, label: str) -> bool:
        logger.info(f"Executando comando ({label}) - IMEI: {imei}")
        result = subprocess.run(
            cmd + [imei],
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
        logger.debug(f"Saída do comando ({label}):\n{result.stdout}")
        return result.returncode == 0

    try:
        return _run(command_map[device_type], device_type)

    except subprocess.TimeoutExpired:
        logger.error(f"Timeout ao executar comando para {imei}")
        return False

    except subprocess.CalledProcessError as e:
        logger.error(f"Erro no script (código {e.returncode}):\n{e.stderr}")

        if device_type == "k1+" and int(getattr(e, "returncode", -1)) == 1:
            logger.warning(
                f"K1+ falhou no ambiente padrão (código 1). "
                f"Tentando 1 vez no ambiente K1... IMEI={imei}"
            )
            try:
                ok = _run(command_map["k1+_ambiente_k1"], "k1+_ambiente_k1")
                if ok:
                    logger.info(f"Fallback ambiente K1 para K1+ funcionou. IMEI={imei}")
                return ok
            except subprocess.TimeoutExpired:
                logger.error(f"Timeout no fallback ambiente K1 para {imei}")
                return False
            except subprocess.CalledProcessError as e2:
                logger.error(f"Erro no fallback (código {e2.returncode}):\n{e2.stderr}")
                return False
            except Exception as e2:
                logger.error(f"Erro inesperado no fallback: {str(e2)}")
                return False

        return False

    except Exception as e:
        logger.error(f"Erro inesperado: {str(e)}")
        return False

# -------------------------
# Processamento
# -------------------------
def process_tasks():
    logger.info("Iniciando processamento de tarefas (Alto consumo - ClickUp)...")
    start_time = time.time()
    cache = _load_cache()

    try:
        if not dentro_do_horario_permitido():
            hora_atual = datetime.datetime.now().strftime("%H:%M")
            logger.info(f"Horário atual: {hora_atual} - Fora do período de funcionamento (8h-12h e 13h-18h)")
            return

        while dentro_do_horario_permitido():
            ciclo_inicio = time.time()
            tasks = get_clickup_tasks()

            if not tasks:
                logger.info("Nenhuma tarefa encontrada.")
            else:
                logger.info(f"Tarefas encontradas: {len(tasks)}")

                for t in tasks:
                    if not dentro_do_horario_permitido():
                        logger.info("Horário de trabalho encerrado. Finalizando...")
                        return

                    task_id = t.get("id")
                    status = _norm(((t.get("status") or {}).get("status") or ""))
                    name = t.get("name", "")
                    logger.info(f"\nProcessando {task_id} - '{name}' - Status: {status}")

                    full = get_clickup_task_full(task_id)
                    description = (full.get("description") or "").strip()

                    equipments = extract_equipments_from_text(description)
                    if not equipments:
                        logger.warning("Nenhum equipamento válido encontrado")
                        add_clickup_comment(task_id, "⚠️ Nenhum equipamento no formato 'Tipo; IMEI' encontrado na descrição")
                        continue

                    results = []
                    all_success = True

                    for eq in equipments:
                        if not dentro_do_horario_permitido():
                            logger.info("Horário de trabalho encerrado. Finalizando...")
                            return

                        logger.info(f"Processando {eq['tipo']} - {eq['imei']}")

                        key = _cache_key(task_id, eq["tipo"], eq["imei"])
                        if cache.get(key) == "ok":
                            results.append(f"✅ {eq['tipo'].upper()} {eq['imei']}: Ajustado (mantido)")
                            continue

                        success = execute_device_command(eq["tipo"], eq["imei"])
                        if success:
                            results.append(f"✅ {eq['tipo'].upper()} {eq['imei']}: Ajustado")
                            cache[key] = "ok"
                            _save_cache(cache)
                        else:
                            results.append(f"⚠️ {eq['tipo'].upper()} {eq['imei']}: Falha na execução")
                            all_success = False

                    if results:
                        comment = "Resultados:\n" + "\n".join(results)
                        add_clickup_comment(task_id, comment)

                    # mover rascunho/to do -> em andamento
                    if status in {CLICKUP_STATUS_TODO, CLICKUP_STATUS_TODO_ALT} and any("✅" in r for r in results):
                        logger.info("Pelo menos um ajuste OK -> Movendo para 'Em andamento'")
                        set_clickup_status(task_id, CLICKUP_STATUS_IN_PROGRESS)

                    # mover em andamento -> concluído
                    if status == CLICKUP_STATUS_IN_PROGRESS and all_success:
                        logger.info("Todos ajustes OK -> Movendo para 'Finalizada'")
                        moved = set_clickup_status(task_id, CLICKUP_STATUS_DONE)
                        if moved:
                            to_del = [k for k in list(cache.keys()) if k.startswith(f"{task_id}:")]
                            for k in to_del:
                                cache.pop(k, None)
                            _save_cache(cache)

            tempo_decorrido = time.time() - ciclo_inicio
            tempo_espera = max(0, INTERVALO_VERIFICACAO - tempo_decorrido)
            if tempo_espera > 0:
                logger.info(f"Aguardando {tempo_espera/60:.1f} minutos até a próxima verificação...")
                while tempo_espera > 0 and dentro_do_horario_permitido():
                    tempo_bloco = min(60, tempo_espera)
                    time.sleep(tempo_bloco)
                    tempo_espera -= tempo_bloco

    except Exception as e:
        logger.error(f"Erro crítico: {str(e)}", exc_info=True)
    finally:
        logger.info(f"Processamento concluído em {time.time() - start_time:.2f}s")
        hora_atual = datetime.datetime.now().strftime("%H:%M")
        logger.info(f"Script finalizado às {hora_atual}. Deve ser reiniciado manualmente amanhã.")

if __name__ == "__main__":
    process_tasks()
