"""
Global Solution 2026.2 - Computer Organization and Architecture - FIAP
Integrantes: Gabriel Fagundes (RM 569074), Glauco Kelly (RM 572840),
             Thiago Renatino (RM 569073)

Etapa 3 - Geração do histórico de atendimentos (DADOS SIMULADOS)

O enunciado permite dados simulados, desde que identificados. Este script gera o
histórico de um posto de atendimento do Bilhete Único (projeto Citizen Assist AI
Mobilidade) com 1 guichê, das 8h às 17h, durante 30 dias úteis.

Modelo da simulação (premissas declaradas no relatório):
- Chegadas seguem um processo de Poisson com taxa que varia por hora do dia
  (picos às 8h-10h e às 12h-14h).
- O tempo de atendimento segue uma distribuição lognormal. A média muda ao longo do
  dia: é maior nos horários de pico (mais pedidos de 2ª via e cadastro de gratuidade)
  e varia de um dia para o outro (dias com sistema lento).
- Fila única, 1 guichê, ordem de chegada (FIFO).

Para cada pessoa que chega, o script registra o que o ESP32 saberia naquele instante
(pessoas na fila e tempo médio dos últimos 5 atendimentos) e a espera que de fato
aconteceu. Toda linha do arquivo traz a coluna origem = "SIMULADO".

Saída: dados/historico_atendimentos_SIMULADO.csv
"""

from pathlib import Path

import numpy as np
import pandas as pd

SEMENTE = 2026
DIAS = 30
ABERTURA_MIN = 8 * 60
FECHAMENTO_MIN = 17 * 60
JANELA_RECENTE = 5  # o ESP32 guarda os últimos 5 tempos de atendimento

# Chegadas esperadas por hora (pessoas/hora)
TAXA_POR_HORA = {8: 13, 9: 14, 10: 11, 11: 10, 12: 13, 13: 13, 14: 10, 15: 9, 16: 8}
# Tempo médio de atendimento por hora (minutos)
MEDIA_ATEND_POR_HORA = {8: 4.6, 9: 4.8, 10: 4.2, 11: 3.9, 12: 4.5, 13: 4.6, 14: 4.0, 15: 3.8, 16: 3.6}

PASTA = Path(__file__).resolve().parent
ARQUIVO = PASTA / "dados" / "historico_atendimentos_SIMULADO.csv"


def simular_dia(dia: int, rng: np.random.Generator) -> list[dict]:
    # Fator do dia: dias com sistema lento ou mais pedidos complexos
    fator_dia = rng.lognormal(mean=0.0, sigma=0.15)

    # 1) Gera as chegadas (Poisson não homogêneo, hora a hora)
    chegadas = []
    for hora, taxa in TAXA_POR_HORA.items():
        n = rng.poisson(taxa)
        chegadas.extend(np.sort(rng.uniform(hora * 60, (hora + 1) * 60, n)))
    chegadas = np.array(chegadas)

    # 2) Tempo de atendimento de cada pessoa
    atendimentos = []
    for t in chegadas:
        media = MEDIA_ATEND_POR_HORA[int(t // 60)] * fator_dia
        sigma = 0.45
        mu = np.log(media) - sigma ** 2 / 2  # lognormal com a média desejada
        atendimentos.append(rng.lognormal(mu, sigma))
    atendimentos = np.array(atendimentos)

    # 3) Fila FIFO com 1 guichê
    registros = []
    livre_em = ABERTURA_MIN
    inicio = np.zeros(len(chegadas))
    fim = np.zeros(len(chegadas))
    for i, t in enumerate(chegadas):
        inicio[i] = max(t, livre_em)
        fim[i] = inicio[i] + atendimentos[i]
        livre_em = fim[i]

    for i, t in enumerate(chegadas):
        # Pessoas no posto quando a pessoa i chega (aguardando + em atendimento)
        na_fila = int(np.sum((chegadas[:i] <= t) & (fim[:i] > t)))
        # Atendimentos já concluídos até o instante t (o que o ESP32 conhece)
        concluidos = np.where(fim[:i] <= t)[0]
        if len(concluidos) == 0:
            tempo_medio_recente = np.nan
        else:
            ultimos = concluidos[np.argsort(fim[concluidos])][-JANELA_RECENTE:]
            tempo_medio_recente = float(np.mean(atendimentos[ultimos]))
        registros.append({
            "origem": "SIMULADO",
            "dia": dia + 1,
            "hora_chegada": round(t / 60, 3),
            "pessoas_na_fila": na_fila,
            "tempo_medio_recente_min": round(tempo_medio_recente, 3) if not np.isnan(tempo_medio_recente) else np.nan,
            "tempo_atendimento_min": round(float(atendimentos[i]), 3),
            "espera_real_min": round(float(inicio[i] - t), 3),
        })
    return registros


def main():
    rng = np.random.default_rng(SEMENTE)
    todos = []
    for dia in range(DIAS):
        todos.extend(simular_dia(dia, rng))
    dados = pd.DataFrame(todos)

    ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
    dados.to_csv(ARQUIVO, index=False, encoding="utf-8")
    print(f"Registros simulados: {len(dados)} chegadas em {DIAS} dias")
    print(f"Arquivo: {ARQUIVO}")
    print(dados.describe().round(2).to_string())


if __name__ == "__main__":
    main()
