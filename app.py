# app.py
import os
import json
import datetime
import html

from flask import Flask, render_template, request
from dotenv import load_dotenv
import boto3
import psutil
import platform

try:
    import streamlit as st
except ImportError:
    st = None

from expert_system import HardwareExpertSystem

# Carregar variáveis de ambiente do .env em ambiente local
load_dotenv()

app = Flask(__name__)
expert_system = HardwareExpertSystem()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_LOG_BUCKET = os.getenv("S3_LOG_BUCKET")  # bucket para logs de diagnósticos

SYMPTOMS = [
    {
        "value": "nao_liga",
        "label": "Computador não liga",
        "icon": "🔌",
        "hint": "Nenhuma reação ao pressionar o botão de energia",
    },
    {
        "value": "reinicia_sozinho",
        "label": "Reinicia sozinho",
        "icon": "🔄",
        "hint": "Reinicializações inesperadas durante o uso",
    },
    {
        "value": "superaquecendo",
        "label": "Superaquecendo",
        "icon": "🔥",
        "hint": "Carcaça quente ou ventiladores sempre no máximo",
    },
    {
        "value": "lento",
        "label": "Muito lento",
        "icon": "🐢",
        "hint": "Programas demoram a abrir ou travam",
    },
    {
        "value": "uso_disco_alto",
        "label": "Uso de disco muito alto",
        "icon": "💽",
        "hint": "Indicador de disco sempre em 100%",
    },
    {
        "value": "pouca_memoria",
        "label": "Pouca memória disponível",
        "icon": "🧠",
        "hint": "Alertas de memória insuficiente ao abrir apps",
    },
    {
        "value": "sem_video",
        "label": "Sem vídeo",
        "icon": "🖥️",
        "hint": "Monitor sem sinal ou tela preta",
    },
    {
        "value": "ruidos",
        "label": "Ruídos estranhos",
        "icon": "🔉",
        "hint": "Cliques, chiados ou vibrações incomuns",
    },
]

SYMPTOM_LABELS = {item["value"]: item["label"] for item in SYMPTOMS}

CUSTOM_CSS = ""

if st is not None:
    # Configuração da página deve ser a primeira chamada Streamlit quando disponível
    st.set_page_config(
        page_title="Diagnóstico de Hardware Cloud",
        page_icon="🖥️",
        layout="wide"
    )
    CUSTOM_CSS = """
<style>
:root {
    --surface-color: rgba(15, 23, 42, 0.72);
    --surface-border: rgba(148, 163, 184, 0.18);
    --accent-color: #38bdf8;
    --accent-gradient: linear-gradient(135deg, #2563eb 0%, #38bdf8 100%);
}
[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at top left, rgba(56, 189, 248, 0.15), transparent 55%), #0f172a;
    color: #e2e8f0;
}
.hero-card {
    border-radius: 18px;
    padding: 24px 28px;
    margin-bottom: 24px;
    background: rgba(30, 41, 59, 0.72);
    border: 1px solid var(--surface-border);
    display: flex;
    gap: 18px;
    align-items: center;
}
.metric-card, .resource-card, .diagnostic-card {
    background: var(--surface-color);
    border-radius: 16px;
    padding: 18px 20px;
    border: 1px solid var(--surface-border);
    box-shadow: 0 24px 40px -32px rgba(15, 23, 42, 0.9);
}
.metric-card__icon {
    font-size: 26px;
    margin-bottom: 4px;
}
.metric-card__title {
    font-size: 0.85rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.metric-card__value {
    font-size: 1.8rem;
    font-weight: 600;
    margin: 8px 0 4px;
}
.metric-card__subtitle {
    font-size: 0.85rem;
    color: #cbd5f5;
}
.section-caption {
    color: #94a3b8;
    margin-bottom: 12px;
}
.resource-card__header {
    font-weight: 600;
    color: #bae6fd;
    margin-bottom: 6px;
}
.resource-card__value {
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 10px;
}
.resource-card__bar {
    width: 100%;
    height: 8px;
    background: rgba(148, 163, 184, 0.25);
    border-radius: 999px;
    overflow: hidden;
}
.resource-card__bar span {
    display: block;
    height: 100%;
    background: var(--accent-gradient);
}
.diagnostic-card {
    margin-bottom: 12px;
    font-size: 0.95rem;
    line-height: 1.5;
    border-left: 3px solid #38bdf8;
    padding-left: 12px;
}
.diagnostic-card strong {
    color: #f8fafc;
}
</style>
"""
def get_system_info():
    """Retorna informações básicas de hardware do servidor."""
    info = {}

    info["platform"] = platform.system()
    info["platform_release"] = platform.release()
    info["architecture"] = platform.machine()
    info["hostname"] = platform.node()
    info["processor"] = platform.processor()
    info["python_version"] = platform.python_version() # Adicionado para evitar erro

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
        except (PermissionError, FileNotFoundError, OSError, SystemError):
            # Alguns dispositivos virtuais ou montagens especiais podem falhar ao consultar uso
            continue

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
    page_meta = {
        "description": "Execute diagnósticos de hardware em nuvem selecionando sintomas e recebendo recomendações práticas instantaneamente.",
        "keywords": "diagnostico de hardware, suporte tecnico, computador lento, superaquecimento",
        "og_title": "Diagnóstico de Hardware em Nuvem",
        "og_description": "Descubra possíveis causas para falhas no computador com um assistente especialista e visão do servidor.",
        "og_url": request.url,
        "twitter_card": "summary_large_image",
    }
    return render_template("index.html", sintomas=SYMPTOMS, meta=page_meta)


@app.route("/diagnosticar", methods=["POST"])
def diagnosticar():
    sintomas_selecionados = request.form.getlist("sintomas")
    descricao_extra = request.form.get("descricao", "").strip()

    # Usa o sistema especialista para obter diagnósticos
    diagnósticos = expert_system.diagnose(sintomas_selecionados)

    sintomas_legiveis = [SYMPTOM_LABELS.get(s, s) for s in sintomas_selecionados]

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

    meta_description = "Resultados do diagnóstico: "
    if sintomas_legiveis:
        meta_description += ", ".join(sintomas_legiveis)
    else:
        meta_description += "nenhum sintoma informado"

    if descricao_extra:
        meta_description += f". Observações adicionais: {descricao_extra[:140]}"

    page_meta = {
        "description": meta_description,
        "keywords": "diagnostico de hardware, resultado, monitoramento",
        "og_title": "Resultado do Diagnóstico | Diagnóstico de Hardware",
        "og_description": meta_description,
        "og_url": request.url,
        "twitter_card": "summary_large_image",
    }

    return render_template(
        "result.html",
        sintomas=sintomas_legiveis,
        descricao_extra=descricao_extra,
        diagnosticos=diagnósticos,
        sysinfo=sysinfo,
        log_status=log_status,
        meta=page_meta,
    )


def main():
    if st is None:
        raise RuntimeError("Streamlit não está instalado. Execute `pip install streamlit` para usar a interface Streamlit.")

    st.title("🖥️ Diagnóstico de Hardware e Rede")
    st.markdown("---")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # Informações do Sistema
    system_info = get_system_info()

    def render_metric_card(title: str, value: str, subtitle: str, icon: str) -> None:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-card__icon">{icon}</div>
                <div class="metric-card__title">{title}</div>
                <div class="metric-card__value">{value}</div>
                <div class="metric-card__subtitle">{subtitle}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    def render_resource_card(title: str, percent: float, icon: str) -> None:
        safe_percent = max(0, min(100, round(percent)))
        st.markdown(
            f"""
            <div class="resource-card">
                <div class="resource-card__header">{icon} {title}</div>
                <div class="resource-card__value">{safe_percent}% em uso</div>
                <div class="resource-card__bar">
                    <span style="width:{safe_percent}%"></span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    cpu_usage = system_info["cpu_usage_percent"]
    memory_usage = system_info["memory_usage_percent"]
    root_usage = psutil.disk_usage(os.path.abspath(os.sep))
    uptime_delta = datetime.datetime.now() - datetime.datetime.strptime(system_info["boot_time"], "%Y-%m-%d %H:%M:%S")
    uptime_days = uptime_delta.days
    uptime_hours = uptime_delta.seconds // 3600
    uptime_minutes = (uptime_delta.seconds % 3600) // 60
    uptime_label = f"{uptime_days}d {uptime_hours}h" if uptime_days else f"{uptime_hours}h {uptime_minutes}m"

    st.markdown(
        """
        <div class="hero-card">
            <div style="font-size:44px">⚡</div>
            <div>
                <h3 style="margin:0; color:#f8fafc">Visão rápida do servidor</h3>
                <p style="margin:6px 0 0; color:#cbd5f5">
                    Monitore o estado da máquina e aplique o diagnóstico inteligente de hardware sem sair daqui.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metric_cols = st.columns(3)
    with metric_cols[0]:
        render_metric_card("Uso de CPU", f"{cpu_usage:.0f}%", "Carga instantânea", "🧠")
    with metric_cols[1]:
        render_metric_card(
            "Memória disponível",
            f"{system_info['available_memory'] / (1024 ** 3):.1f} GB",
            f"Uso atual {memory_usage:.0f}%",
            "🧬",
        )
    with metric_cols[2]:
        render_metric_card(
            "Tempo de atividade",
            uptime_label,
            f"Iniciado em {system_info['boot_time']}",
            "⏱️",
        )

    st.markdown("### Diagnóstico de Sintomas")
    st.markdown(
        "<p class='section-caption'>Informe os sinais observados para receber recomendações personalizadas.</p>",
        unsafe_allow_html=True,
    )
    sintomas_selecionados = st.multiselect(
        "Selecione os sintomas que você está enfrentando:",
        options=[s["value"] for s in SYMPTOMS],
        format_func=lambda value: SYMPTOM_LABELS.get(value, value),
    )

    descricao_extra = st.text_area("Descrição adicional do problema:")

    if st.button("Diagnosticar"):
        if not sintomas_selecionados:
            st.warning("Por favor, selecione pelo menos um sintoma.")
        else:
            with st.spinner("Realizando diagnóstico..."):
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

                st.success("Diagnóstico realizado com sucesso!")
                st.subheader("Diagnósticos Sugeridos")
                for diag in diagnósticos:
                    st.markdown(
                        f"<div class='diagnostic-card'>💡 {html.escape(diag)}</div>",
                        unsafe_allow_html=True,
                    )

                st.markdown("---")
                st.write(log_status)

    if st.button("🔄 Atualizar Dados"):
        st.rerun()

    # Seção de Hardware do Servidor (Oculta por padrão)
    with st.expander("📊 Visualizar Resumo do Hardware do Servidor", expanded=False):
        st.subheader("Detalhes do Servidor")
        col1, col2, col3, col4 = st.columns(4)
        
        # Corrigido chaves do dicionário para bater com get_system_info()
        with col1:
            st.metric("Sistema", f"{system_info['platform']} {system_info['platform_release']}")
        with col2:
            st.metric("Processador", system_info['processor'])
        with col3:
            st.metric("Arquitetura", system_info['architecture'])
        with col4:
            st.metric("Python", system_info['python_version'])

        st.markdown("#### Uso de Recursos")
        c1, c2, c3 = st.columns(3)
        with c1:
            render_resource_card("CPU", cpu_usage, "🧠")
        with c2:
            render_resource_card("Memória", memory_usage, "🧬")
        with c3:
            render_resource_card("Disco", root_usage.percent, "💾")

        st.markdown("---")
        st.markdown("#### Informações Detalhadas")
        st.write(f"**Hostname:** {system_info['hostname']}")
        st.write(f"**Núcleos da CPU:** {system_info['cpu_count']}")
        st.write(f"**Frequência da CPU:** {system_info['cpu_freq_current']} MHz")
        st.write(f"**Memória Total:** {system_info['total_memory'] / (1024 ** 3):.2f} GB")
        st.write(f"**Memória Disponível:** {system_info['available_memory'] / (1024 ** 3):.2f} GB")
        st.write(f"**Disco:**")
        for disk in system_info["disks"]:
            st.write(f"  - {disk['device']} ({disk['fstype']}): {disk['total'] / (1024 ** 3):.2f} GB")

    st.markdown("---")
    

if __name__ == "__main__":
    # Para rodar a interface visual (Streamlit), execute: streamlit run app.py
    # O comando abaixo chama a função main() quando executado pelo Streamlit
    main()
    
    # Para rodar a API Flask, descomente a linha abaixo e execute: python app.py
    # app.run(host="0.0.0.0", port=5000, debug=True)
