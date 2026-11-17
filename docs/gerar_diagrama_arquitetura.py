"""
Global Solution 2026.2 - Computer Organization and Architecture - FIAP
Integrantes: Gabriel Fagundes (RM 569074), Glauco Kelly (RM 572840),
             Thiago Renatino (RM 569073)

Etapa 1 - Diagrama de arquitetura do sistema de fila virtual.
Gera docs/diagrama_arquitetura.png e docs/diagrama_arquitetura.svg.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

PASTA = Path(__file__).resolve().parent

CORES = {
    "entrada": ("#E3F2E9", "#1E8E5A"),
    "cpu": ("#E2ECF8", "#1F5FA8"),
    "memoria": ("#F3E8F8", "#7B3FA0"),
    "saida": ("#FDEFE0", "#C7701B"),
    "rede": ("#E6F4F6", "#1B7F8C"),
    "externo": ("#F1F1F1", "#666666"),
}


def caixa(ax, x, y, w, h, titulo, linhas, tipo, tam_titulo=10.5):
    fundo, borda = CORES[tipo]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                                facecolor=fundo, edgecolor=borda, linewidth=1.6))
    ax.text(x + w / 2, y + h - 0.22, titulo, ha="center", va="top", fontsize=tam_titulo,
            fontweight="bold", color=borda)
    ax.text(x + w / 2, y + h - 0.62, "\n".join(linhas), ha="center", va="top", fontsize=8.2,
            color="#222222", linespacing=1.45)


def seta(ax, x1, y1, x2, y2, rotulo="", cor="#333333", estilo="-|>", rot_off=(0, 0.12), curva=0.0):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=estilo, mutation_scale=14,
                                 color=cor, linewidth=1.4, connectionstyle=f"arc3,rad={curva}"))
    if rotulo:
        ax.text((x1 + x2) / 2 + rot_off[0], (y1 + y2) / 2 + rot_off[1], rotulo, ha="center",
                va="bottom", fontsize=7.6, color=cor,
                bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="none", alpha=0.85))


def main():
    fig, ax = plt.subplots(figsize=(16, 9.6))
    ax.set_xlim(0, 16)
    ax.set_ylim(-0.1, 9.6)
    ax.axis("off")

    ax.text(8, 9.35, "Citizen Assist AI · Arquitetura do Sistema Inteligente de Fila Virtual "
            "(posto do Bilhete Único)", ha="center", fontsize=14, fontweight="bold", color="#1D2733")
    ax.text(8, 8.98, "ENTRADA  →  PROCESSAMENTO  →  SAÍDA  ·  ESP32 simulado no Wokwi  ·  "
            "comunicação Wi-Fi / MQTT com o painel web", ha="center", fontsize=10, color="#5B6878")

    # Fronteira do dispositivo embarcado
    ax.add_patch(FancyBboxPatch((3.35, 1.0), 8.3, 7.55, boxstyle="round,pad=0.02,rounding_size=0.2",
                                facecolor="none", edgecolor="#9AA7B5", linewidth=1.2, linestyle="--"))
    ax.text(3.55, 8.38, "Dispositivo embarcado: placa ESP32 DevKit-C (Wokwi)", fontsize=9,
            color="#5B6878", style="italic")

    # ENTRADAS
    caixa(ax, 0.2, 5.6, 2.9, 2.4, "ENTRADAS", [
        "Botão VERDE · chegada", "GPIO 15 · pull-up interno",
        "Botão AZUL · atendimento", "GPIO 13 · pull-up interno",
        "Borda de descida → interrupção"], "entrada")
    caixa(ax, 0.2, 2.6, 2.9, 2.3, "ENTRADAS VIRTUAIS", [
        "Botões do painel web", "comando MQTT:", "\"chegada\" / \"atendimento\"",
        "mesma validação do ESP32"], "entrada")

    # CONTROLADOR GPIO
    caixa(ax, 3.6, 5.85, 2.3, 1.9, "GPIO + Controlador", [
        "de interrupções", "ISR em IRAM (IRAM_ATTR)", "debounce 250 ms",
        "flag volatile → loop()"], "cpu", 9.6)

    # CPU
    caixa(ax, 6.3, 4.55, 2.9, 3.45, "CPU · Xtensa LX6", [
        "dual-core 32 bits · 240 MHz", "Núcleo 0: pilha Wi-Fi/TCP-IP",
        "Núcleo 1: loop() da aplicação", "ULA: fila ± 1, médias,",
        "regressão (3 mult. + 3 somas)", "UC: busca → decodifica → executa",
        "Clock: contador de ciclos no log"], "cpu")

    # MEMÓRIA
    caixa(ax, 3.6, 1.25, 2.9, 3.0, "MEMÓRIA", [
        "SRAM 520 KB (volátil):", "fila, contadores, 5 tempos recentes,",
        "log circular 64 × 16 B = 1 KB,", "buffers Wi-Fi/MQTT",
        "Flash SPI 4 MB (não volátil):", "firmware + coeficientes do modelo",
        "ROM 448 KB: bootloader"], "memoria")

    # SAÍDAS
    caixa(ax, 9.65, 6.15, 1.85, 1.85, "SAÍDAS", [
        "LCD 16x2 · I2C", "SDA 21 · SCL 22", "LED verde GPIO 2", "LED verm. GPIO 4"], "saida", 9.6)
    caixa(ax, 9.65, 4.0, 1.85, 1.85, "UART", [
        "Serial Monitor", "115200 baud", "logs [DATA] [LOGIC]", "[ACTION] [EVENT]"], "saida", 9.6)

    # REDE (no dispositivo)
    caixa(ax, 6.8, 1.25, 4.65, 2.5, "INTERFACE DE REDE", [
        "Rádio Wi-Fi 802.11 b/g/n · 2,4 GHz (SSID Wokwi-GUEST)",
        "TCP/IP (lwIP) · NTP para o horário dos eventos",
        "Cliente MQTT (PubSubClient) · TCP 1883",
        "publica: …/estado (retain) e …/evento",
        "assina: …/comando"], "rede")

    # EXTERNOS
    caixa(ax, 12.15, 4.6, 3.6, 2.35, "BROKER MQTT", [
        "broker.hivemq.com (público)", "TCP 1883 ⇄ ESP32",
        "WebSocket seguro 8884 ⇄ navegador", "modelo publicar / assinar"], "externo")
    caixa(ax, 12.15, 1.25, 3.6, 2.75, "PAINEL WEB (navegador)", [
        "dashboard/index.html · mqtt.js", "fila atual · concluídos",
        "espera IA × média histórica", "registro de eventos com horário",
        "botões virtuais"], "externo")
    caixa(ax, 12.15, 7.35, 3.6, 1.4, "TREINO DA IA (PC, offline)", [
        "Python · dados SIMULADOS · mínimos quadrados",
        "gera modelo_espera.h → gravado na flash"], "externo", 9.6)

    # Fluxos
    seta(ax, 3.1, 6.8, 3.6, 6.8, "", "#1E8E5A")
    seta(ax, 5.9, 6.8, 6.3, 6.8, "IRQ", "#1F5FA8")
    seta(ax, 7.75, 4.55, 7.75, 3.75, "barramento", "#1B7F8C", "<|-|>", (0.62, -0.12))
    seta(ax, 6.3, 5.0, 6.5, 4.25, "", "#7B3FA0", "<|-|>")
    ax.text(5.5, 4.45, "barramento de\ndados/endereços", fontsize=7.4, color="#7B3FA0", ha="center")
    seta(ax, 9.2, 7.0, 9.65, 7.0, "", "#C7701B")
    seta(ax, 9.2, 4.9, 9.65, 4.9, "", "#C7701B")
    seta(ax, 11.45, 3.1, 12.15, 4.9, "", "#1B7F8C", "<|-|>")
    ax.text(11.58, 2.55, "MQTT\nTCP", fontsize=7.6, color="#1B7F8C", ha="left")
    seta(ax, 13.95, 4.6, 13.95, 4.0, "WSS", "#1B7F8C", "<|-|>", (0.35, -0.1))
    # Botões virtuais: contorna por baixo das caixas (painel -> broker -> ESP32)
    ax.plot([13.95, 13.95, 1.65], [1.25, 0.75, 0.75], color="#1E8E5A", lw=1.4)
    seta(ax, 1.65, 0.75, 1.65, 2.6, "", "#1E8E5A")
    ax.text(7.5, 0.5, "botões virtuais: painel → broker → ESP32 (tópico …/comando)", fontsize=8,
            color="#1E8E5A", ha="center", va="top")
    seta(ax, 13.95, 7.35, 13.95, 6.95, "", "#666666")
    ax.text(14.05, 7.1, "coeficientes", fontsize=7.4, color="#666666")

    # Legenda
    for i, (tipo, nome) in enumerate([("entrada", "Entrada"), ("cpu", "Processamento"),
                                      ("memoria", "Memória"), ("saida", "Saída"),
                                      ("rede", "Comunicação"), ("externo", "Fora do ESP32")]):
        fundo, borda = CORES[tipo]
        ax.add_patch(FancyBboxPatch((0.25 + i * 1.75, 0.08), 0.28, 0.22, boxstyle="round,pad=0.01",
                                    facecolor=fundo, edgecolor=borda))
        ax.text(0.62 + i * 1.75, 0.19, nome, va="center", fontsize=8.2)

    fig.savefig(PASTA / "diagrama_arquitetura.png", dpi=170, bbox_inches="tight")
    fig.savefig(PASTA / "diagrama_arquitetura.svg", bbox_inches="tight")
    print("Diagrama gerado em docs/diagrama_arquitetura.png e .svg")


if __name__ == "__main__":
    main()
