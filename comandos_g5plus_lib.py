#!/usr/bin/env python
# -# ===== Parametros de envio =====
CMD_PAUSE_SECONDS = 3           # pausa entre comandos
RETRIES_PER_COMMAND = 1         # tentativas por comando
RETRY_PAUSE_SECONDS = 3         # pausa entre tentativas
TIMEOUT_CONNECT = 60             # timeout de conexao (s)
TIMEOUT_READ = 60               # timeout de leitura (s)ing: utf-8 -*-

import sys
import re
import requests
from time import sleep
from datetime import datetime, timezone, timedelta

# ===== Configuracoes do endpoint =====
URL = "http://10.1.1.71:9080/api/device/sendInstruct"
HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}

# ===== Sequencia de comandos =====
COMMANDS = [
    "ADASSEP,2,0",
    "ADASSEP,3,0",
    "UPLOADSW,LANEDEPARTURE,OFF",
    "UPLOADSW,VEHICLETOOCLOSE,OFF",
    "UPLOADSW,FORWARDCOLLISION,OFF",
    "ADASSW,0",
    "DMS_ALERT_CUSTOM,120,120,1800,120,120,1800",
    "CAMERA,IN,1",
    "CAMERA,OUT,1",
]

# ===== Parametros de envio =====
CMD_PAUSE_SECONDS = 3           # pausa entre comandos
RETRIES_PER_COMMAND = 1         # tentativas por comando
RETRY_PAUSE_SECONDS = 3         # pausa entre tentativas
TIMEOUT_CONNECT = 30            # timeout de conexao (s)
TIMEOUT_READ = 30               # timeout de leitura (s)

# ===== Util =====
def agora_br():
    return (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")

def log(msg):
    # Somente ASCII para nao quebrar no Windows (cp1252)
    print(f"[{agora_br()}] {msg}", flush=True)

def criar_payload(imei, cmd):
    return {
        "imei": imei,
        "cmdContent": cmd,
        "serverFlagId": 0,
        "proNo": 128,
        "platform": "web",
        "requestId": 6,
        "cmdType": "normallns",
        "token": 123,
    }

def tratar_resposta(resp_json, imei, cmd):
    if resp_json.get("msg") == "success":
        log(f"[OK] IMEI {imei}: comando '{cmd}' aceito.")
        return True
    motivo = resp_json.get("data") or resp_json.get("error") or resp_json.get("message") or "Resposta sem sucesso"
    log(f"[WARN] IMEI {imei}: comando '{cmd}' nao confirmado. Detalhe: {motivo}")
    return False

def enviar_comando(imei, cmd):
    payload = criar_payload(imei, cmd)
    for tentativa in range(1, RETRIES_PER_COMMAND + 1):
        try:
            log(f"-> IMEI {imei}: enviando '{cmd}' (tentativa {tentativa}/{RETRIES_PER_COMMAND})")
            r = requests.post(
                URL,
                headers=HEADERS,
                data=payload,
                timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
                allow_redirects=False,
            )
            r.raise_for_status()
            try:
                j = r.json()
            except ValueError:
                txt = r.text or ""
                log(f"[ERR] IMEI {imei}: resposta invalida (nao JSON). Conteudo: {txt[:200]}...")
                if tentativa < RETRIES_PER_COMMAND:
                    sleep(RETRY_PAUSE_SECONDS)
                    continue
                return False
            if tratar_resposta(j, imei, cmd):
                return True
        except requests.exceptions.RequestException as e:
            log(f"[ERR] IMEI {imei}: erro HTTP/rede em '{cmd}': {e}")
        if tentativa < RETRIES_PER_COMMAND:
            sleep(RETRY_PAUSE_SECONDS)
    return False

def main(argv):
    if len(argv) < 2:
        print("Uso: python comandos_g5plus_lib.py <IMEI> [<IMEI2> <IMEI3> ...]")
        return 2

    imeis = []
    for a in argv[1:]:
        a = a.strip().strip(",")
        if not re.fullmatch(r"\d{8,}", a):
            log(f"[WARN] IMEI ignorado (formato invalido): {a}")
            continue
        imeis.append(a)

    if not imeis:
        log("[ERR] Nenhum IMEI valido informado.")
        return 2

    ok_total = True
    for imei in imeis:
        log(f"=== Iniciando IMEI {imei} ===")
        for idx, cmd in enumerate(COMMANDS, 1):
            log(f"[STEP {idx}/{len(COMMANDS)}] Proximo comando: {cmd}")
            ok = enviar_comando(imei, cmd)
            ok_total = ok_total and ok
            sleep(CMD_PAUSE_SECONDS)  # pausa fixa de 3s entre comandos
        log(f"=== Finalizado IMEI {imei} ===")

    if ok_total:
        log("[OK] Todos os comandos aceitos para todos os IMEIs.")
        return 0
    else:
        log("[WARN] Houve falhas em um ou mais comandos/IMEIs.")
        return 1

if __name__ == "__main__":
    sys.exit(main(sys.argv))
