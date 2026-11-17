// Gerado automaticamente por ia/treinar_previsao.py - não editar à mão.
// Modelo treinado com dados SIMULADOS (ia/dados/historico_atendimentos_SIMULADO.csv).
// espera_ia = MODELO_B0 + MODELO_B1 * fila + MODELO_B2 * (fila * tempo_medio_recente)   [minutos]
// (nomes com prefixo MODELO_ porque B0 e B1 já existem no Arduino, em binary.h)
#pragma once

const float MEDIA_HISTORICA_INICIAL_MIN = 4.1734f;  // média dos dias de treino
const float MODELO_B0 = -2.813011f;
const float MODELO_B1 = 3.342074f;
const float MODELO_B2 = 0.356460f;
// Teste (dias 22-30): MAE convencional = 5.33 min | MAE IA = 4.83 min
