# Roteiro do vídeo – Computer Organization (máx. 5 min)

**Projeto:** Citizen Assist AI – Sistema Inteligente de Gerenciamento de Filas Virtuais
**Integrantes:** Gabriel Fagundes (RM 569074) · Glauco Kelly (RM 572840) · Thiago Renatino (RM 569073)

Antes de gravar: abra o projeto no Wokwi (já iniciado e com o Wi-Fi conectado) e o painel web (`dashboard/index.html`) lado a lado. Deixe o Serial Monitor visível.

| Tempo | O que mostrar na tela | O que falar |
|---|---|---|
| 0:00–0:30 | Capa do relatório | Apresentação do trio e do problema: quem chega ao posto do Bilhete Único não sabe quanto vai esperar. A proposta é uma fila virtual com um ESP32 e uma estimativa de espera feita por IA. |
| 0:30–1:10 | Diagrama de arquitetura (Figura 1) | Fluxo ENTRADA → PROCESSAMENTO → SAÍDA. Botões e painel web são as entradas. CPU, SRAM e flash fazem o processamento. LCD, LEDs e MQTT são as saídas. Relacionar com a arquitetura de Von Neumann. |
| 1:10–2:20 | Wokwi: apertar o verde 3 vezes e o azul 2 vezes | Cada toque gera uma interrupção (ISR na IRAM). O debounce de 50 ms confirma o toque no loop. Mostrar no Serial as linhas [DATA], [LOGIC], [EVENT] e [ACTION] e o número do ciclo. No LCD, a fila e as duas estimativas de espera. Comentar a correção do repique ao soltar o botão, encontrada durante os testes. |
| 2:20–2:50 | Wokwi: esvaziar a fila e apertar o azul mais uma vez | Tratamento de erro: a fila não fica negativa. O LED vermelho pisca e aparece o evento SAIDA_FILA_VAZIA. |
| 2:50–3:40 | Painel web: usar os botões virtuais | O comando vai ao broker por MQTT e o ESP32 é quem valida. Mostrar o evento com origem=web e a atualização do painel em tempo real. |
| 3:40–4:20 | Gráficos da IA (Figuras 3 e 4) | Os dados são simulados e estão identificados como tal. Comparar a regressão linear com a média histórica: o MAE cai de 5,33 para 4,83 min (−9,4%). A inferência no ESP32 custa 3 multiplicações e 3 somas. |
| 4:20–5:00 | Tabelas de memória e protocolos | Hierarquia de memória (registradores, SRAM, flash), consumo de 1 KB do log circular e protocolos GPIO, I2C, UART, Wi-Fi e MQTT. Fechar com as limitações (QoS 0, broker público) e as melhorias possíveis. |

**Dicas:**
- Fale enquanto a ação acontece na tela, sem pausas longas.
- Grave em 1080p e confira se o texto do Serial Monitor está legível.
