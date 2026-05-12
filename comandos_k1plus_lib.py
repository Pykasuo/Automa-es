import sys
import os
import re
import json
import time
import argparse
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ===== Configurações padrão (iguais às do seu script) =====
DEFAULT_CONFIG_PATH = str(Path(__file__).parent / "json" / "K1Plus.json")
URL_PREFIX = 'http://10.1.1.92:6060' 
USER_CMS = "admin"                   

# ===== Parâmetros de envio =====
PAUSE_BETWEEN_IMEIS = 10       # pausa entre IMEIs (segundos), igual ao seu script antigo
RETRIES_PER_IMEI = 1           # tentativas por IMEI
RETRY_PAUSE_SECONDS = 3        # pausa entre retentativas
TIMEOUT_CONNECT = 30           # timeout conexão (s)
TIMEOUT_READ = 30              # timeout leitura (s)

# ===== Util =====
def agora_br():
    return (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")

def log(msg):
    print(f"[{agora_br()}] {msg}", flush=True)

def validar_imei(imei: str) -> bool:
    return bool(re.fullmatch(r"\d{8,}", imei or ""))

def carregar_json(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Arquivo JSON nao encontrado: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def montar_url(imei: str) -> str:
    return f"{URL_PREFIX}/SetConfig/{imei}"

def enviar_json(imei: str, cfg: dict) -> bool:
    """
    Envia o JSON para um IMEI com retentativas.
    Sucesso = HTTP 200.
    """
    url = montar_url(imei)
    headers = {"Content-Type": "application/json"}

    for tentativa in range(1, RETRIES_PER_IMEI + 1):
        try:
            log(f"-> IMEI {imei}: enviando JSON (tentativa {tentativa}/{RETRIES_PER_IMEI})")
            r = requests.post(
                url,
                json=cfg,
                headers=headers,
                timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
                allow_redirects=False,
            )
            if r.status_code == 200:
                log(f"[OK] IMEI {imei}: configuracao aceita (HTTP 200).")
                return True
            else:
                log(f"[WARN] IMEI {imei}: HTTP {r.status_code}. Resposta: {r.text[:200]}")

        except requests.exceptions.RequestException as e:
            log(f"[ERR] IMEI {imei}: erro HTTP/rede: {e}")

        if tentativa < RETRIES_PER_IMEI:
            time.sleep(RETRY_PAUSE_SECONDS)

    log(f"[ERR] IMEI {imei}: falha apos {RETRIES_PER_IMEI} tentativas.")
    return False

# ===== CLI =====
def parse_args(argv):
    p = argparse.ArgumentParser(
        description="Aplica JSON de configuracao (K1+) em 1 ou mais IMEIs (sequencial)."
    )
    p.add_argument("imeis", nargs="+", help="Lista de IMEIs (1 ou mais).")
    p.add_argument("--config", "-c", default=DEFAULT_CONFIG_PATH,
                   help=f"Caminho do arquivo JSON (padrao: {DEFAULT_CONFIG_PATH})")
    return p.parse_args(argv)

def main(argv):
    args = parse_args(argv)

    # valida IMEIs
    imeis = []
    for raw in args.imeis:
        s = (raw or "").strip().strip(",")
        if not validar_imei(s):
            log(f"[WARN] IMEI ignorado (formato invalido): {raw}")
            continue
        imeis.append(s)

    if not imeis:
        log("[ERR] Nenhum IMEI valido informado.")
        log("Uso: python comandos_k1plus_lib.py <IMEI> [<IMEI2> ...] [--config CAMINHO_JSON]")
        return 2

    # carrega JSON de configuracao
    try:
        cfg = carregar_json(args.config)
        log(f"[INFO] Config carregada de: {args.config}")
    except Exception as e:
        log(f"[ERR] Falha ao carregar JSON de configuracao: {e}")
        return 2

    # processa sequencialmente (1 IMEI por vez)
    ok_total = True
    for idx, imei in enumerate(imeis, 1):
        log(f"=== ({idx}/{len(imeis)}) Iniciando IMEI {imei} ===")
        ok = enviar_json(imei, cfg)
        ok_total = ok_total and ok
        log(f"=== Finalizado IMEI {imei} ===")
        if idx < len(imeis):
            time.sleep(PAUSE_BETWEEN_IMEIS)

    if ok_total:
        log("[OK] JSON aplicado com sucesso a todos os IMEIs.")
        return 0
    else:
        log("[WARN] Houve falhas em um ou mais IMEIs.")
        return 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
