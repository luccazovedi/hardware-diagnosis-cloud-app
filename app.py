# app.py
import os
import json
import datetime

from flask import Flask, render_template, request
from dotenv import load_dotenv
import boto3
import psutil
import platform

from expert_system import HardwareExpertSystem

# Carregar variáveis de ambiente do .env em ambiente local
load_dotenv()

app = Flask(__name__)
expert_system = HardwareExpertSystem()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_LOG_BUCKET = os.getenv("S3_LOG_BUCKET")  # bucket para logs de diagnósticos


def get_system_info():
    """Retorna informações básicas de hardware do servidor."""
    info = {}

    info["platform"] = platform.system()
    info["platform_release"] = platform.release()
    info["architecture"] = platform.machine()
    info["hostname"] = platform.node()
    info["processor"] = platform.processor()

    # CPU
    info["cpu_count"] = psutil.cpu_count(logical=True)
    try:
        freq = psutil.cpu_freq()
        info["cpu_freq_current"] = freq.current if freq else None
        info["cpu_freq_min"] = freq.min if freq else None
        info["cpu_freq_max"] = freq.max if freq else None
    except Exception:
        info["cpu_freq_current"] = None
        info["cpu_freq_min"] = None
        info["cpu_freq_max"] = None
    info["cpu_usage_percent"] = psutil.cpu_percent(interval=1)

    # Memória
    svmem = psutil.virtual_memory()
    info["total_memory"] = svmem.total
    info["available_memory"] = svmem.available
    info["memory_usage_percent"] = svmem.percent

    # Disco
    partitions = psutil.disk_partitions()
    disks = []
    for p in partitions:
        try:
            usage = psutil.disk_usage(p.mountpoint)
            disks.append(
                {
                    "device": p.device,
                    "mountpoint": p.mountpoint,
                    "fstype": p.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent,
                }
            )
        except PermissionError:
            continue
    info["disks"] = disks

    info["boot_time"] = datetime.datetime.fromtimestamp(
        psutil.boot_time()
    ).strftime("%Y-%m-%d %H:%M:%S")

    return info


def salvar_log_s3(payload: dict) -> None:
    """Salva log da consulta no S3 (se o bucket estiver configurado)."""
    if not S3_LOG_BUCKET:
        # Se não tiver bucket configurado, não faz nada
        return

    session = boto3.session.Session(region_name=AWS_REGION)
    s3 = session.client("s3")

    now = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    key = f"logs/diagnostico_{now}.json"

    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

    s3.put_object(
        Bucket=S3_LOG_BUCKET,
        Key=key,
        Body=body,
        ContentType="application/json; charset=utf-8",
    )


@app.route("/", methods=["GET"])
def index():
    # Lista de sintomas disponíveis pro formulário
    sintomas = [
        ("nao_liga", "Computador não liga"),
        ("reinicia_sozinho", "Reinicia sozinho"),
        ("superaquecendo", "Superaquecendo"),
        ("lento", "Muito lento"),
        ("uso_disco_alto", "Uso de disco muito alto"),
        ("pouca_memoria", "Pouca memória disponível"),
        ("sem_video", "Sem vídeo (monitor sem sinal)"),
        ("ruidos", "Ruídos estranhos (cliques/chiados)"),
    ]
    return render_template("index.html", sintomas=sintomas)


@app.route("/diagnosticar", methods=["POST"])
def diagnosticar():
    sintomas_selecionados = request.form.getlist("sintomas")
    descricao_extra = request.form.get("descricao", "").strip()

    # Usa o sistema especialista para obter diagnósticos
    diagnósticos = expert_system.diagnose(sintomas_selecionados)

    # Coleta info do hardware do servidor
    sysinfo = get_system_info()

    # Monta payload de log
    log_payload = {
        "timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "sintomas": sintomas_selecionados,
        "descricao_extra": descricao_extra,
        "diagnosticos": diagnósticos,
        "resumo_hardware": {
            "hostname": sysinfo["hostname"],
            "platform": sysinfo["platform"],
            "platform_release": sysinfo["platform_release"],
            "cpu_count": sysinfo["cpu_count"],
            "memory_usage_percent": sysinfo["memory_usage_percent"],
        },
    }

    # Tenta salvar no S3 (se configurado)
    try:
        salvar_log_s3(log_payload)
        log_status = "Log registrado em S3 (se configurado corretamente)."
    except Exception as e:
        log_status = f"Não foi possível salvar log no S3: {e}"

    return render_template(
        "result.html",
        sintomas=sintomas_selecionados,
        descricao_extra=descricao_extra,
        diagnosticos=diagnósticos,
        sysinfo=sysinfo,
        log_status=log_status,
    )


if __name__ == "__main__":
    # Para rodar localmente
    app.run(host="0.0.0.0", port=5000, debug=True)
