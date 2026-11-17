"""
Global Solution 2026.2 - Computer Organization and Architecture - FIAP
Integrantes: Gabriel Fagundes (RM 569074), Glauco Kelly (RM 572840),
             Thiago Renatino (RM 569073)

Etapa 3 - Previsão inteligente de espera: média histórica x regressão linear

Entrada: dados/historico_atendimentos_SIMULADO.csv (gerado por gerar_dados_simulados.py)

Métodos comparados (para uma pessoa que acabou de chegar):
1) Convencional: espera = pessoas_na_fila x média histórica do tempo de atendimento.
2) IA (regressão linear múltipla por mínimos quadrados):
       espera = b0 + b1·fila + b2·(fila x tempo_medio_recente)
   A variável fila x tempo_medio_recente representa a "carga" que está à frente da
   pessoa, medida com os últimos 5 atendimentos (o ESP32 guarda esse histórico).

Treino com os dias 1 a 21 e teste com os dias 22 a 30 (dias que o modelo não viu).
Os coeficientes vão para o firmware em ../firmware/modelo_espera.h, onde o ESP32 faz a
inferência a cada evento (3 multiplicações e 3 somas).

Saídas: resultados/metricas.json, resultados/*.png e ../firmware/modelo_espera.h
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PASTA = Path(__file__).resolve().parent
ARQUIVO = PASTA / "dados" / "historico_atendimentos_SIMULADO.csv"
RESULTADOS = PASTA / "resultados"
CABECALHO_FIRMWARE = PASTA.parent / "firmware" / "modelo_espera.h"
DIA_CORTE = 21


def montar_x(dados: pd.DataFrame) -> np.ndarray:
    fila = dados["pessoas_na_fila"].to_numpy(float)
    carga = fila * dados["tempo_medio_recente_min"].to_numpy(float)
    return np.column_stack([np.ones(len(dados)), fila, carga])


def metricas(real, previsto) -> dict:
    erro = previsto - real
    ss_res = float(np.sum(erro ** 2))
    ss_tot = float(np.sum((real - real.mean()) ** 2))
    return {
        "MAE_min": round(float(np.mean(np.abs(erro))), 3),
        "RMSE_min": round(float(np.sqrt(np.mean(erro ** 2))), 3),
        "R2": round(1 - ss_res / ss_tot, 4),
        "vies_medio_min": round(float(np.mean(erro)), 3),
    }


def main():
    dados = pd.read_csv(ARQUIVO)
    assert (dados["origem"] == "SIMULADO").all()
    # Sem tempo médio recente = início do dia, antes do 1º atendimento concluído.
    # O firmware usa a média histórica nesse caso; aqui as linhas ficam fora do ajuste.
    dados = dados.dropna(subset=["tempo_medio_recente_min"]).reset_index(drop=True)
    treino = dados[dados["dia"] <= DIA_CORTE]
    teste = dados[dados["dia"] > DIA_CORTE]

    # 1) Convencional: média histórica do tempo de atendimento (só dias de treino)
    media_historica = float(treino["tempo_atendimento_min"].mean())
    conv_teste = teste["pessoas_na_fila"].to_numpy() * media_historica

    # 2) Regressão linear por mínimos quadrados (equações normais via lstsq)
    X_treino, y_treino = montar_x(treino), treino["espera_real_min"].to_numpy()
    beta, *_ = np.linalg.lstsq(X_treino, y_treino, rcond=None)
    ia_teste = np.clip(montar_x(teste) @ beta, 0, None)  # espera nunca é negativa

    real = teste["espera_real_min"].to_numpy()
    m_conv = metricas(real, conv_teste)
    m_ia = metricas(real, ia_teste)

    print(f"Registros: treino {len(treino)} (dias 1-{DIA_CORTE}) | teste {len(teste)} (dias {DIA_CORTE + 1}-30)")
    print(f"Média histórica do atendimento: {media_historica:.3f} min")
    print(f"Coeficientes IA: b0 = {beta[0]:.4f} | b1 (fila) = {beta[1]:.4f} | "
          f"b2 (fila x tempo recente) = {beta[2]:.4f}")
    print(f"Convencional (teste): {m_conv}")
    print(f"IA - regressão (teste): {m_ia}")
    ganho = (1 - m_ia["MAE_min"] / m_conv["MAE_min"]) * 100
    print(f"Redução do erro médio absoluto com a IA: {ganho:.1f}%")

    # Erro por tamanho de fila (onde cada método erra mais)
    teste = teste.assign(erro_conv=np.abs(conv_teste - real), erro_ia=np.abs(ia_teste - real))
    faixas = pd.cut(teste["pessoas_na_fila"], [-1, 0, 2, 5, 10, 100], labels=["0", "1-2", "3-5", "6-10", "11+"])
    por_faixa = teste.groupby(faixas, observed=True)[["erro_conv", "erro_ia"]].mean().round(2)
    print("\nErro médio absoluto (min) por tamanho da fila:")
    print(por_faixa.to_string())

    RESULTADOS.mkdir(exist_ok=True)
    resultado = {
        "origem_dos_dados": "SIMULADO",
        "registros_treino": int(len(treino)), "registros_teste": int(len(teste)),
        "media_historica_min": round(media_historica, 4),
        "coeficientes": {"b0": round(float(beta[0]), 6), "b1_fila": round(float(beta[1]), 6),
                         "b2_fila_x_tempo_recente": round(float(beta[2]), 6)},
        "convencional": m_conv, "ia_regressao": m_ia,
        "reducao_mae_pct": round(ganho, 1),
        "erro_por_faixa_de_fila": por_faixa.reset_index().rename(columns={"pessoas_na_fila": "faixa"})
                                             .astype({"faixa": str}).to_dict(orient="records"),
    }
    (RESULTADOS / "metricas.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2),
                                              encoding="utf-8")

    # Gráfico 1: real x previsto
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharex=True, sharey=True)
    for ax, prev, titulo, m, cor in [
        (axes[0], conv_teste, "Convencional (fila x média histórica)", m_conv, "#E07A1F"),
        (axes[1], ia_teste, "IA (regressão linear)", m_ia, "#2E86AB"),
    ]:
        ax.scatter(real, prev, s=8, alpha=0.35, color=cor)
        lim = max(real.max(), prev.max())
        ax.plot([0, lim], [0, lim], color="#333333", lw=1, label="Previsão perfeita")
        ax.set_title(f"{titulo}\nMAE = {m['MAE_min']:.2f} min | R² = {m['R2']:.3f}")
        ax.set_xlabel("Espera real (min)")
        ax.legend(loc="upper left")
    axes[0].set_ylabel("Espera estimada (min)")
    fig.suptitle("Previsão de espera nos dias de teste (dados SIMULADOS)")
    fig.tight_layout()
    fig.savefig(RESULTADOS / "real_x_previsto.png", dpi=150)
    plt.close(fig)

    # Gráfico 2: erro por faixa de fila
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    x = np.arange(len(por_faixa))
    ax.bar(x - 0.2, por_faixa["erro_conv"], 0.4, label="Convencional", color="#E07A1F")
    ax.bar(x + 0.2, por_faixa["erro_ia"], 0.4, label="IA (regressão)", color="#2E86AB")
    ax.set_xticks(x, por_faixa.index.astype(str))
    ax.set_xlabel("Pessoas na fila quando a pessoa chegou")
    ax.set_ylabel("Erro médio absoluto (min)")
    ax.set_title("Erro da estimativa por tamanho da fila (dados SIMULADOS)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(RESULTADOS / "erro_por_fila.png", dpi=150)
    plt.close(fig)

    # Cabeçalho C para o firmware (inferência no ESP32)
    CABECALHO_FIRMWARE.parent.mkdir(exist_ok=True)
    CABECALHO_FIRMWARE.write_text(f"""// Gerado automaticamente por ia/treinar_previsao.py - não editar à mão.
// Modelo treinado com dados SIMULADOS (ia/dados/historico_atendimentos_SIMULADO.csv).
// espera_ia = MODELO_B0 + MODELO_B1 * fila + MODELO_B2 * (fila * tempo_medio_recente)   [minutos]
// (nomes com prefixo MODELO_ porque B0 e B1 já existem no Arduino, em binary.h)
#pragma once

const float MEDIA_HISTORICA_INICIAL_MIN = {media_historica:.4f}f;  // média dos dias de treino
const float MODELO_B0 = {beta[0]:.6f}f;
const float MODELO_B1 = {beta[1]:.6f}f;
const float MODELO_B2 = {beta[2]:.6f}f;
// Teste (dias {DIA_CORTE + 1}-30): MAE convencional = {m_conv['MAE_min']:.2f} min | MAE IA = {m_ia['MAE_min']:.2f} min
""", encoding="utf-8")
    print(f"\nCabeçalho do firmware: {CABECALHO_FIRMWARE}")


if __name__ == "__main__":
    main()
