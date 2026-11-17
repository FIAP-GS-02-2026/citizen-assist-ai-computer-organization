"""
Global Solution 2026.2 - Computer Organization and Architecture - FIAP
Integrantes: Gabriel Fagundes (RM 569074), Glauco Kelly (RM 572840),
             Thiago Renatino (RM 569073)

Gera docs/relatorio_tecnico_fila_virtual.pdf a partir de:
- docs/diagrama_arquitetura.png (gerar_diagrama_arquitetura.py)
- ia/resultados/metricas.json, real_x_previsto.png, erro_por_fila.png (treinar_previsao.py)
- docs/evidencias/: testes.json, serial_testes.txt e capturas de tela do Wokwi e do painel
"""

import json
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, Preformatted, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

DOCS = Path(__file__).resolve().parent
RAIZ = DOCS.parent
EVID = DOCS / "evidencias"
IA = RAIZ / "ia" / "resultados"
SAIDA = DOCS / "relatorio_tecnico_fila_virtual.pdf"

INTEGRANTES = [("Gabriel Fagundes", "RM 569074"), ("Glauco Kelly", "RM 572840"),
               ("Thiago Renatino", "RM 569073")]

AZUL = colors.HexColor("#1F4E79")
CINZA = colors.HexColor("#F2F2F2")


def registrar_fontes():
    candidatos = [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/consola.ttf"),
    ]
    for normal, negrito, mono in candidatos:
        try:
            pdfmetrics.registerFont(TTFont("Texto", normal))
            pdfmetrics.registerFont(TTFont("Texto-Negrito", negrito))
            pdfmetrics.registerFont(TTFont("Mono", mono))
            pdfmetrics.registerFontFamily("Texto", normal="Texto", bold="Texto-Negrito")
            return "Texto", "Texto-Negrito", "Mono"
        except Exception:
            continue
    return "Helvetica", "Helvetica-Bold", "Courier"


FT, FN, FM = registrar_fontes()
base = getSampleStyleSheet()
CORPO = ParagraphStyle("c", parent=base["Normal"], fontName=FT, fontSize=9.8, leading=14,
                       alignment=TA_JUSTIFY, spaceAfter=6)
H1 = ParagraphStyle("h1", parent=CORPO, fontName=FN, fontSize=14, leading=18, textColor=AZUL,
                    spaceBefore=10, spaceAfter=8, alignment=0, keepWithNext=1)
H2 = ParagraphStyle("h2", parent=H1, fontSize=11.5, leading=15, spaceBefore=8, spaceAfter=5)
LEG = ParagraphStyle("leg", parent=CORPO, fontSize=8.3, leading=11, alignment=TA_CENTER,
                     textColor=colors.HexColor("#555555"), spaceAfter=10)
CEL = ParagraphStyle("cel", parent=CORPO, fontSize=8.4, leading=11, alignment=0, spaceAfter=0)
BUL = ParagraphStyle("bul", parent=CORPO, leftIndent=12)
DEST = ParagraphStyle("dest", parent=CORPO, backColor=colors.HexColor("#EAF1F8"), borderPadding=(6, 6, 6, 6),
                      borderColor=AZUL, borderWidth=0.6, spaceBefore=6, spaceAfter=12)
MONO = ParagraphStyle("mono", parent=CORPO, fontName=FM, fontSize=7.1, leading=9.2, alignment=0,
                      backColor=colors.HexColor("#F6F8FA"), borderPadding=(5, 5, 5, 5), spaceAfter=10)


def p(t, e=CORPO):
    return Paragraph(t, e)


def bullets(itens):
    return [p(f"• {i}", BUL) for i in itens]


def tabela(linhas, larguras, cab=True):
    dados = [[Paragraph(str(c), CEL) for c in l] for l in linhas]
    t = Table(dados, colWidths=larguras, hAlign="CENTER", repeatRows=1 if cab else 0)
    est = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BFBFBF")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
           ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if cab:
        est.append(("BACKGROUND", (0, 0), (-1, 0), CINZA))
    t.setStyle(TableStyle(est))
    return t


def figura(caminho, largura_cm, legenda):
    caminho = Path(caminho)
    if not caminho.exists():
        return p(f"[figura ausente: {caminho.name}]", LEG)
    img = Image(str(caminho))
    prop = img.imageHeight / img.imageWidth
    img.drawWidth, img.drawHeight = largura_cm * cm, largura_cm * cm * prop
    if img.drawHeight > 21 * cm:
        img.drawHeight, img.drawWidth = 21 * cm, 21 * cm / prop
    return KeepTogether([img, p(legenda, LEG)])


def com_legenda(tab, legenda):
    return KeepTogether([tab, p(legenda, LEG)])


def fmt(v, casas=2):
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def rodape(c, doc):
    c.saveState()
    c.setFont(FT, 7.5)
    c.setFillColor(colors.HexColor("#777777"))
    c.drawString(2 * cm, 1.2 * cm, "Citizen Assist AI · Fila Virtual · Computer Organization and Architecture · GS 2026.2")
    c.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Página {doc.page}")
    c.restoreState()


def main():
    m = json.loads((IA / "metricas.json").read_text(encoding="utf-8"))
    testes = json.loads((EVID / "testes.json").read_text(encoding="utf-8"))
    medidas = testes["medidas"]
    serial = (EVID / "serial_testes.txt").read_text(encoding="utf-8") if (EVID / "serial_testes.txt").exists() else ""
    co, ia, cf = m["convencional"], m["ia_regressao"], m["coeficientes"]

    s = []
    # ---------------------------------------------------------------- CAPA
    s += [Spacer(1, 2.6 * cm),
          p("Relatório Técnico", ParagraphStyle("t0", parent=H1, fontSize=12, alignment=TA_CENTER,
                                                textColor=colors.HexColor("#555555"))),
          p("Sistema Inteligente de Gerenciamento de Filas Virtuais",
            ParagraphStyle("t1", parent=H1, fontSize=21, leading=27, alignment=TA_CENTER)),
          p("Citizen Assist AI · posto de atendimento do Bilhete Único",
            ParagraphStyle("t2", parent=CORPO, fontSize=12.5, alignment=TA_CENTER)),
          Spacer(1, 1.3 * cm),
          p("Global Solution 2026.2 · Desafio CitizenTech<br/>Disciplina: Computer Organization and Architecture "
            "(Arquitetura e Organização de Computadores)<br/>1CC-FEV · FIAP",
            ParagraphStyle("t3", parent=CORPO, alignment=TA_CENTER)),
          Spacer(1, 1 * cm),
          tabela([["Integrante", "RM"]] + [list(x) for x in INTEGRANTES], [9 * cm, 4 * cm]),
          Spacer(1, 1.3 * cm),
          p(f"Protótipo: ESP32 simulado no Wokwi · painel web com MQTT · previsão com regressão linear<br/>"
            f"Projeto no Wokwi: https://wokwi.com/projects/480962115318032385<br/>"
            f"São Paulo, {date.today().strftime('%d/%m/%Y')}",
            ParagraphStyle("t4", parent=CORPO, alignment=TA_CENTER, fontSize=9)),
          PageBreak()]

    # ---------------------------------------------------------------- RESUMO
    s.append(p("Resumo", H1))
    s.append(p(
        "Este trabalho apresenta um protótipo de fila virtual para um posto de atendimento do Bilhete Único, "
        "dentro do projeto Citizen Assist AI Mobilidade. Um microcontrolador ESP32, simulado no Wokwi, recebe dois "
        "botões físicos (chegada de um cidadão e conclusão de um atendimento) por interrupção, mantém a contagem da "
        "fila sem permitir valores negativos, registra cada evento com horário obtido por NTP e mostra o estado em um "
        "display LCD 16x2 e em dois LEDs. Pela rede Wi-Fi, o ESP32 publica o estado em um broker MQTT, e um painel "
        "web aberto no navegador exibe a fila, os atendimentos concluídos e o tempo estimado de espera, além de "
        "enviar comandos de volta por botões virtuais."))
    s.append(p(
        f"O tempo de espera é estimado de duas formas, como pede o enunciado: pela média histórica (fila × tempo "
        f"médio de atendimento) e por uma regressão linear treinada com {m['registros_treino'] + m['registros_teste']:,} "
        f"chegadas simuladas e identificadas como tais. Nos dias de teste, a regressão reduziu o erro médio absoluto "
        f"de {fmt(co['MAE_min'])} para {fmt(ia['MAE_min'])} minutos ({fmt(m['reducao_mae_pct'], 1)}%). "
        f"O ESP32 executa essa inferência a cada evento, com 3 multiplicações e 3 somas em ponto flutuante. "
        f"Os quatro testes mínimos do enunciado foram executados no simulador e todos tiveram o resultado esperado."
        .replace(",", ".", 1)))

    # ---------------------------------------------------------------- 1. CONTEXTO
    s.append(p("1. Contexto e objetivo", H1))
    s.append(p(
        "Postos de atendimento de serviços públicos costumam ter filas sem informação: o cidadão não sabe quantas "
        "pessoas estão à frente nem quanto vai esperar. O Citizen Assist AI Mobilidade orienta sobre Bilhete Único "
        "e gratuidades no transporte, e muitos desses pedidos exigem ir a um posto presencial. O protótipo mostra, em "
        "tempo real e pela internet, o tamanho da fila e uma estimativa de espera, para que a pessoa possa decidir "
        "a melhor hora de ir."))
    s.append(p(
        "O objetivo da disciplina é demonstrar como hardware e software trabalham juntos: dispositivos de entrada "
        "geram sinais, a CPU os processa com dados guardados na memória, e o resultado chega às saídas locais e à "
        "rede. Por isso cada decisão de projeto abaixo é explicada em termos de CPU, memória, entrada e saída e "
        "comunicação."))

    # ---------------------------------------------------------------- 2. ARQUITETURA
    s.append(PageBreak())
    s.append(p("2. Arquitetura do sistema (Etapa 1)", H1))
    s.append(figura(DOCS / "diagrama_arquitetura.png", 17,
                    "Figura 1 – Diagrama de arquitetura: componentes computacionais e suas conexões."))
    s.append(com_legenda(tabela([
        ["Bloco", "Componente no protótipo", "Papel na arquitetura"],
        ["CPU", "ESP32 (Xtensa LX6, 2 núcleos, 240 MHz)", "Executa o firmware: trata as interrupções, atualiza a "
                                                          "fila, calcula as estimativas e coordena E/S e rede."],
        ["Memória RAM", "SRAM interna de 520 KB", "Dados voláteis em uso: contadores, últimos 5 tempos, log circular "
                                                  "de eventos, pilhas do Wi-Fi/TCP/MQTT."],
        ["Armazenamento", "Flash SPI de 4 MB + ROM de 448 KB", "Não volátil: bootloader (ROM), firmware e "
                                                               "coeficientes do modelo (flash)."],
        ["Entradas", "2 botões (GPIO 15 e 13) + botões virtuais", "Geram os eventos de chegada e de conclusão."],
        ["Saídas", "LCD 16x2 I2C, LED verde e vermelho, Serial", "Mostram fila, estimativas, alertas e o log de "
                                                                 "processamento."],
        ["Comunicação", "Wi-Fi 802.11 b/g/n + MQTT", "Envia o estado ao painel web e recebe os comandos dos "
                                                     "botões virtuais."],
    ], [2.6 * cm, 5.4 * cm, 8.6 * cm]), "Tabela 1 – Componentes do sistema."))
    s.append(p("Fluxo de informações", H2))
    s.append(p(
        "O fluxo segue o modelo ENTRADA → PROCESSAMENTO → SAÍDA visto em aula (Semana 07), sobre a arquitetura de "
        "programa armazenado de Von Neumann (Aula 01): as instruções do firmware ficam na flash e os dados em uso, "
        "na SRAM, e a CPU busca, decodifica e executa as instruções."))
    s += bullets([
        "<b>Entrada.</b> Ao apertar o botão, o pino vai a 0 V (o resistor de pull-up interno o mantém em 3,3 V "
        "quando solto). O controlador de GPIO detecta a mudança de nível e gera uma interrupção.",
        "<b>Interrupção.</b> A CPU suspende o loop e executa a ISR, que fica na RAM interna (IRAM_ATTR) para "
        "responder mais rápido. A ISR só anota, em variáveis <i>volatile</i>, que o pino mudou e quando.",
        "<b>Debounce.</b> No loop(), o toque só é confirmado quando o pino fica estável em 0 V por 50 ms e antes "
        "estava em 3,3 V. Assim, os repiques mecânicos ao apertar e ao soltar viram um único evento.",
        "<b>Processamento.</b> Confirmado o toque, a CPU aplica as regras da fila (não aceita "
        "saída com fila vazia nem ultrapassar 99 pessoas), mede o tempo do atendimento e recalcula as duas "
        "estimativas de espera com a ULA e a unidade de ponto flutuante.",
        "<b>Memória.</b> Cada evento vira um registro de 16 bytes (horário, ciclo, tipo, origem, fila e espera "
        "estimada) gravado em um buffer circular de 64 posições na SRAM.",
        "<b>Saída local.</b> A CPU atualiza o LCD pelo barramento I2C, acende o LED correspondente e escreve o "
        "log na UART (Serial Monitor, 115.200 baud).",
        "<b>Saída em rede.</b> O estado é convertido em JSON e publicado por MQTT/TCP pelo rádio Wi-Fi; o broker "
        "o repassa ao navegador por WebSocket seguro.",
    ])

    # ---------------------------------------------------------------- 3. FILA
    s.append(PageBreak())
    s.append(p("3. Implementação da fila virtual (Etapa 2)", H1))
    s.append(p("O projeto completo pode ser aberto e executado em https://wokwi.com/projects/480962115318032385."))
    s.append(figura(EVID / "wokwi_circuito.png", 15.5,
                    "Figura 2 – Circuito no Wokwi: ESP32, LCD 16x2 I2C, botões de chegada (verde) e de atendimento "
                    "(azul) e LEDs de status."))
    s.append(com_legenda(tabela([
        ["Requisito do enunciado", "Como foi implementado"],
        ["Registrar a chegada por um botão", "Botão verde no GPIO 15 com INPUT_PULLUP; interrupção a cada "
                                             "mudança do pino (attachInterrupt, CHANGE) e confirmação do toque "
                                             "por debounce de 50 ms."],
        ["Registrar a conclusão por outro botão", "Botão azul no GPIO 13, mesma técnica."],
        ["Atualizar automaticamente a quantidade aguardando", "Fila incrementada ou decrementada no loop() a cada "
                                                               "toque confirmado; LCD, LEDs e painel atualizados "
                                                               "em seguida."],
        ["Impedir contagens negativas e operações inválidas", "Conclusão com fila = 0 é recusada (evento "
                                                              "SAIDA_FILA_VAZIA, LED vermelho pisca); chegada com "
                                                              "fila = 99 é recusada (FILA_CHEIA); debounce evita "
                                                              "contagem dupla; comandos desconhecidos são ignorados."],
        ["Exibir o total de pessoas na fila", "LCD (linha 1), painel web e Serial Monitor."],
        ["Registrar eventos e horários", "Buffer circular de 64 eventos na SRAM, com horário NTP e número do "
                                         "ciclo; cada evento também é publicado no tópico …/evento."],
    ], [5.4 * cm, 11.2 * cm]), "Tabela 2 – Requisitos da Etapa 2 e implementação."))
    s.append(p("Interrupção × polling", H2))
    s.append(p(
        "Seguindo a comparação da Semana 07, os botões usam <b>interrupção</b>: a CPU não gasta ciclos perguntando "
        "pelo estado dos pinos e não perde um toque rápido, mesmo quando está ocupada com a rede ou piscando o LED de "
        "erro. Já a rede usa <b>polling</b>: a cada volta do loop() o firmware verifica o Wi-Fi, o relógio NTP e o "
        "cliente MQTT. O polling é adequado aqui porque essas tarefas não exigem resposta imediata e a "
        "biblioteca de MQTT foi projetada para esse modelo."))
    s.append(p(
        "A conexão Wi-Fi também foi feita de forma não bloqueante. Na primeira versão, o setup() esperava até 15 s "
        "pela rede, e os botões ficavam sem atendimento nesse período. Na versão final, a fila funciona desde o boot, "
        "sem rede, e a conexão é concluída em segundo plano."))
    s.append(p("Correção encontrada nos testes: repique ao soltar o botão", H2))
    s.append(p(
        "Os botões do circuito simulam o repique mecânico real (atributo <i>bounce</i> do Wokwi). Na primeira "
        "versão, a ISR reagia só à borda de descida e ignorava novas bordas por 250 ms. No teste, cada toque "
        "longo contou duas vezes: três toques no botão verde geraram seis chegadas. O motivo é que, ao soltar o "
        "botão depois de 250 ms, o repique produz uma nova borda de descida, que a ISR tratava como outro toque. "
        "A correção foi trocar o filtro por tempo pelo <b>debounce por estado estável</b>: a ISR só anota a "
        "mudança, e o loop() confirma o toque quando o pino permanece em 0 V por 50 ms e estava em 3,3 V antes. "
        "Os testes da Seção 7 foram refeitos com essa versão. Na mesma revisão, o pisca-pisca de erro deixou de "
        "usar delay() e passou a ser controlado por millis(), sem bloquear o loop."))
    s.append(p("Registro de eventos na memória", H2))
    s.append(p(
        "Cada evento é guardado em uma <i>struct</i> de 16 bytes (Aula 02): <font name='Mono'>uint32_t epoch, "
        "uint32_t ciclo, uint8_t tipo, uint8_t origem, uint16_t fila, float esperaIA</font>. A ordem dos campos "
        "evita bytes de preenchimento (padding): os campos de 4 bytes ficam alinhados e os dois de 1 byte somados "
        "ao de 2 bytes completam outra palavra de 4 bytes. São 64 posições em buffer circular, ou seja, 1.024 bytes "
        "fixos de SRAM, valor que o próprio ESP32 informa no boot."))

    # ---------------------------------------------------------------- 4. PREVISÃO
    s.append(PageBreak())
    s.append(p("4. Previsão inteligente de espera (Etapa 3)", H1))
    s.append(p(
        "<b>Dados simulados.</b> O enunciado permite dados simulados, desde que identificados. O script "
        "<font name='Mono'>ia/gerar_dados_simulados.py</font> gera o histórico de 30 dias úteis de um posto com 1 "
        "guichê (8h às 17h), e toda linha do arquivo traz <font name='Mono'>origem = SIMULADO</font>. As chegadas "
        "seguem um processo de Poisson com picos às 8h–10h e 12h–14h; o tempo de atendimento segue uma distribuição "
        "lognormal, com média maior nos horários de pico e variação de um dia para o outro. Para cada chegada, o "
        "arquivo registra o que o ESP32 saberia naquele instante (pessoas na fila e média dos últimos 5 "
        "atendimentos) e a espera que de fato aconteceu."))
    s.append(com_legenda(tabela([
        ["Método", "Fórmula (espera em minutos)", "MAE", "RMSE", "R²"],
        ["Convencional (média histórica)", f"fila × {fmt(m['media_historica_min'], 2)}",
         f"{fmt(co['MAE_min'])} min", f"{fmt(co['RMSE_min'])} min", fmt(co['R2'], 3)],
        ["IA (regressão linear múltipla)",
         f"{fmt(cf['b0'], 3)} + {fmt(cf['b1_fila'], 3)}·fila + {fmt(cf['b2_fila_x_tempo_recente'], 3)}·(fila × "
         f"tempo médio recente)", f"<b>{fmt(ia['MAE_min'])} min</b>", f"<b>{fmt(ia['RMSE_min'])} min</b>",
         f"<b>{fmt(ia['R2'], 3)}</b>"],
    ], [4.2 * cm, 6.6 * cm, 2 * cm, 2 * cm, 1.8 * cm]),
        f"Tabela 3 – Comparação nos dias de teste (dias 22 a 30, {m['registros_teste']} chegadas que o modelo não "
        f"viu no treino)."))
    s.append(figura(IA / "real_x_previsto.png", 16, "Figura 3 – Espera real × estimada nos dias de teste."))
    s.append(figura(IA / "erro_por_fila.png", 11.5, "Figura 4 – Erro médio absoluto por tamanho da fila."))
    s.append(p(
        f"<b>Interpretação.</b> A estimativa convencional supõe que cada pessoa à frente ocupa um atendimento inteiro, "
        f"mas quem está no guichê já está no meio do atendimento. Por isso ela erra mais com filas curtas. A regressão "
        f"aprende essa diferença (intercepto negativo) e usa o tempo médio dos últimos 5 atendimentos, o que a deixa "
        f"reagir a dias lentos. A IA erra menos em todas as faixas de fila, e o erro médio absoluto caiu "
        f"{fmt(m['reducao_mae_pct'], 1)}%. O ganho é moderado: as duas estimativas pioram com filas longas, porque a "
        f"incerteza se acumula a cada pessoa à frente."))
    s.append(p(
        "<b>Onde a IA roda.</b> O treino é feito uma vez no computador, por mínimos quadrados, e gera o arquivo "
        "<font name='Mono'>firmware/modelo_espera.h</font> com os coeficientes. Eles são gravados na flash junto com "
        "o firmware. No ESP32, a inferência é só "
        "<font name='Mono'>b0 + b1·fila + b2·(fila × tempo_recente)</font>, ou seja, 3 multiplicações e 3 somas. É "
        "a mesma operação de multiplicação e acúmulo (MAC) que a TPU executa em massa (Aula 01), aqui em escala "
        "mínima e sem precisar de acelerador. A média histórica começa com o valor dos dados simulados (peso de 20 "
        "atendimentos) e é atualizada com cada atendimento real medido pelo ESP32."))
    s.append(p(
        "<b>Modo demonstração.</b> Para a demonstração caber no vídeo, 1 segundo real equivale a 1 minuto do posto "
        "(constante <font name='Mono'>ESCALA_DEMO</font>). Em uma instalação real, basta trocá-la por 1."))

    # ---------------------------------------------------------------- 5. COMUNICAÇÃO
    s.append(PageBreak())
    s.append(p("5. Comunicação e visualização (Etapa 4)", H1))
    s.append(p(
        "O ESP32 conecta-se ao Wi-Fi e usa o protocolo MQTT, de publicação e assinatura: o dispositivo publica em "
        "tópicos e o painel assina esses tópicos, sem precisar saber o endereço IP um do outro. O broker público "
        "HiveMQ faz a intermediação. O ESP32 usa MQTT sobre TCP (porta 1883), e o navegador usa MQTT sobre "
        "WebSocket seguro (porta 8884), porque páginas web não abrem conexões TCP diretas."))
    s.append(com_legenda(tabela([
        ["Tópico (prefixo fiap/gs2026/citizenassist/fila/posto-bu-01)", "Sentido", "Conteúdo"],
        ["…/estado (retain)", "ESP32 → painel", "fila, concluídos, operações inválidas, espera IA e média, tempos "
                                                "médios, ciclo, tempo ligado, heap livre e horário. Publicado a cada "
                                                "evento e a cada 5 s."],
        ["…/evento", "ESP32 → painel", "tipo do evento, origem (botão ou web), fila, espera estimada, ciclo e "
                                       "horário."],
        ["…/comando", "painel → ESP32", "\"chegada\", \"atendimento\" ou \"estado\"."],
    ], [6.2 * cm, 2.6 * cm, 7.8 * cm]), "Tabela 4 – Tópicos MQTT e mensagens."))
    s.append(p(
        "A mensagem de estado é publicada com <i>retain</i>, então o painel recebe o último estado assim que abre, "
        "sem esperar o próximo evento. Os botões virtuais enviam comandos ao ESP32, mas a validação continua no "
        "dispositivo: uma saída com fila vazia pedida pelo painel é recusada da mesma forma que pelo botão físico."))
    s.append(figura(EVID / "painel_web.png", 16,
                    "Figura 5 – Painel web recebendo os dados do ESP32 simulado: fila, esperas estimadas, "
                    "atendimentos concluídos, dados do dispositivo e registro de eventos."))

    # ---------------------------------------------------------------- 6. ANÁLISE
    s.append(PageBreak())
    s.append(p("6. Análise da arquitetura computacional (Etapa 5)", H1))
    s.append(p("6.1 Processador", H2))
    s.append(p(
        f"O ESP32 do simulador identifica-se como <b>{medidas['chip']}</b>, com {medidas['nucleos']} núcleos a "
        f"{medidas['clock_mhz']} MHz (valores lidos pelo próprio firmware no boot). Os núcleos são Xtensa LX6 de "
        "32 bits, uma arquitetura do tipo RISC (Semana 04): instruções simples, de tamanho reduzido, adequadas a "
        "pipeline e a baixo consumo, típicas de sistemas embarcados. O chip tem unidade de ponto flutuante de "
        "precisão simples, usada nos cálculos de média e regressão com <i>float</i>."))
    s.append(p(
        "Na prática, o framework Arduino distribui o trabalho entre os núcleos: a pilha Wi-Fi e TCP/IP roda no "
        "núcleo 0, e a função loop() da aplicação, no núcleo 1. É um exemplo, em escala menor, da orquestração de "
        "tarefas vista na Aula 01: cada unidade cuida do que faz melhor. A CPU prioriza latência (responder rápido "
        "a cada toque), e não vazão. Por isso uma CPU generalista é a escolha certa, e GPU ou TPU seriam "
        "desnecessárias para este volume de cálculo."))
    s.append(p("6.2 Organização da memória e estimativa de uso", H2))
    s.append(com_legenda(tabela([
        ["Nível (hierarquia, Aula 03)", "Tamanho", "O que guarda neste projeto", "Uso medido / estimado"],
        ["Registradores e cache", "–", "Operandos das instruções em execução; cache da flash (execução "
                                        "direto da flash)", "gerido pelo hardware"],
        ["SRAM interna (volátil)", "520 KB", "fila, contadores, 5 tempos recentes, log circular, buffers de rede",
         f"heap livre: {fmt(medidas['heap_boot_bytes'], 0)} B no boot e {fmt(medidas['heap_rede_bytes'], 0)} B "
         f"com Wi-Fi e MQTT ativos"],
        ["  · log de eventos", "1.024 B", "64 eventos × 16 B", "fixo (alocação estática)"],
        ["  · buffer MQTT", "512 B", "uma mensagem JSON de estado (cerca de 330 B)", "fixo"],
        ["  · dados da aplicação", "≈ 0,2 KB", "contadores, tempos, nomes dos tópicos", "estimado"],
        ["ROM (não volátil)", "448 KB", "bootloader de primeiro estágio", "somente leitura"],
        ["Flash SPI externa (não volátil)", f"{medidas['flash_kb'] // 1024} MB",
         "firmware, bibliotecas e coeficientes do modelo",
         f"programa: {medidas['sketch_kb']} KB (cerca de 72% da partição de aplicação de 1,25 MB)"],
    ], [3.6 * cm, 1.7 * cm, 6 * cm, 5.3 * cm]), "Tabela 5 – Memória do ESP32 e uso pelo protótipo."))
    s.append(p(
        f"O consumo próprio da aplicação é pequeno (menos de 2 KB de SRAM). A maior parte da memória é usada pela "
        f"pilha de rede: o heap livre cai cerca de {fmt((medidas['heap_boot_bytes'] - medidas['heap_rede_bytes']) / 1024, 0)} KB "
        f"quando o Wi-Fi e o MQTT entram em operação. O programa fica na flash, que é não volátil, e é executado "
        f"por meio da cache, como na Aula 04: o armazenamento guarda, a RAM disponibiliza, a cache aproxima e a CPU "
        f"processa. Como o log está na SRAM, ele é perdido ao reiniciar. Gravá-lo na flash é uma evolução possível, "
        f"lembrando que a flash tem número limitado de ciclos de escrita."))
    s.append(p("6.3 Operações de entrada, processamento e saída", H2))
    s.append(com_legenda(tabela([
        ["Operação", "Dispositivo / interface", "Como a CPU acessa"],
        ["Entrada digital", "Botões nos GPIO 15 e 13", "Interrupção a cada mudança de nível (CHANGE); ISR em IRAM; "
                                                       "debounce de 50 ms confirma o toque no loop."],
        ["Entrada pela rede", "Comando MQTT", "Polling do cliente MQTT no loop; callback ao chegar mensagem."],
        ["Processamento", "ULA e FPU do Xtensa LX6", "Comparações (fila = 0? fila ≥ 99?), soma e subtração da "
                                                     "fila, médias e regressão."],
        ["Saída digital", "LEDs nos GPIO 2 e 4 (resistor de 220 Ω)", "Escrita nos registradores de saída do "
                                                                     "GPIO (digitalWrite)."],
        ["Saída de texto", "LCD 16x2 com módulo I2C (endereço 0x27)", "Barramento I2C (SDA 21, SCL 22)."],
        ["Saída de depuração", "Serial Monitor", "UART 115.200 baud."],
        ["Saída em rede", "Painel web", "JSON publicado via MQTT/TCP pelo Wi-Fi."],
    ], [3.3 * cm, 5.3 * cm, 8 * cm]), "Tabela 6 – Entrada, processamento e saída."))
    s.append(p("6.4 Comunicação entre dispositivos e protocolos", H2))
    s.append(com_legenda(tabela([
        ["Protocolo", "Tipo", "Uso no projeto"],
        ["GPIO + interrupção", "sinal digital, nível lógico 0/1", "botões → CPU"],
        ["I2C", "serial síncrona, 2 fios (dados e clock), com endereço", "CPU → LCD"],
        ["UART 8N1", "serial assíncrona: start bit, 8 bits com o menos significativo primeiro, stop bit "
                     "(Semana 06)", "CPU → Serial Monitor"],
        ["Wi-Fi 802.11 b/g/n", "rádio 2,4 GHz", "ESP32 → ponto de acesso Wokwi-GUEST"],
        ["TCP/IP", "transporte confiável", "base do MQTT"],
        ["NTP (UDP)", "sincronização de relógio", "horário dos eventos"],
        ["MQTT 3.1.1", "publicação/assinatura, QoS 0", "ESP32 ⇄ broker ⇄ painel"],
        ["WebSocket seguro", "MQTT dentro de HTTPS", "broker ⇄ navegador"],
    ], [3.4 * cm, 6.6 * cm, 6.6 * cm]), "Tabela 7 – Protocolos utilizados."))
    s.append(p(
        "Assim como no exemplo da Semana 06, em que a CPU lê os registradores DATA e STATUS de um controlador, o "
        "firmware não manipula diretamente os sinais elétricos do rádio ou do I2C: ele usa controladores "
        "dedicados do ESP32, e a CPU apenas lê e escreve nos registradores deles pelos barramentos de endereço, "
        "dados e controle."))
    s.append(p("6.5 Limitações de desempenho, memória e conectividade", H2))
    s += bullets([
        "<b>Desempenho.</b> O loop() tem um delay(10) por volta, o que limita a cerca de 100 voltas por segundo; "
        "é suficiente para pessoas apertando botões e reduz o uso da CPU. A escrita no LCD por I2C é lenta "
        "comparada à CPU, e por isso só acontece quando o estado muda ou a cada 5 s. O debounce de 50 ms acrescenta "
        "essa latência mínima entre o toque e o registro, imperceptível para o usuário.",
        "<b>Memória.</b> O log guarda só os 64 eventos mais recentes e é perdido ao reiniciar. A montagem do JSON "
        "com objetos String aloca memória dinamicamente e pode fragmentar o heap em uso prolongado; buffers de "
        "tamanho fixo seriam mais robustos.",
        "<b>Conectividade.</b> O broker é público e sem autenticação, o que serve a um protótipo mas não a um "
        "serviço real. Com QoS 0, uma mensagem enviada enquanto o ESP32 está desconectado se perde. Isso foi "
        "observado durante os testes: um comando do painel enviado com a simulação pausada não chegou e precisou "
        "ser reenviado. Sem Wi-Fi, a fila continua funcionando localmente; sem NTP, os eventos são marcados em "
        "segundos desde o boot.",
        "<b>Simulação.</b> No Wokwi, a velocidade da simulação varia conforme o computador e a aba do navegador. Por "
        "isso todos os tempos do firmware usam millis(), o relógio do próprio ESP32, e não o tempo real do "
        "computador.",
    ])

    # ---------------------------------------------------------------- 7. TESTES
    s.append(PageBreak())
    s.append(p("7. Testes e resultados", H1))
    s.append(p(
        "Os quatro testes mínimos do enunciado foram executados no Wokwi com o firmware final. As entradas foram "
        "aplicadas nos botões físicos simulados. O resultado observado foi copiado do Serial Monitor (Anexo A) e "
        "conferido no painel web."))
    linhas = [["Teste", "Entrada", "Resultado esperado", "Resultado observado", "Situação"]]
    for t in testes["testes"]:
        linhas.append([t["teste"], t["entrada"], t["esperado"], t["observado"], f"<b>{t['situacao']}</b>"])
    s.append(com_legenda(tabela(linhas, [2.6 * cm, 2.9 * cm, 3.7 * cm, 5.0 * cm, 2.4 * cm]),
                         "Tabela 8 – Testes mínimos do enunciado."))
    if testes.get("extras"):
        linhas = [["Teste complementar", "Resultado observado", "Situação"]]
        for t in testes["extras"]:
            linhas.append([t["teste"], t["observado"], f"<b>{t['situacao']}</b>"])
        s.append(com_legenda(tabela(linhas, [4.8 * cm, 9.4 * cm, 2.4 * cm]), "Tabela 9 – Testes complementares."))
    s.append(figura(EVID / "wokwi_resultado.png", 15.5,
                    "Figura 6 – Wokwi ao final dos testes: LCD com a fila e os atendimentos concluídos, e o Serial "
                    "Monitor com os logs."))

    # ---------------------------------------------------------------- 8. CONCLUSÃO
    s.append(p("8. Conclusão", H1))
    s.append(p(
        "O protótipo cumpre as cinco etapas do enunciado. O mesmo dado (um toque no botão) percorre todo o "
        "sistema: vira um sinal elétrico, uma interrupção, uma instrução executada pela CPU, um registro na "
        "memória, uma mensagem nas saídas locais e um pacote na rede até o navegador. A previsão com regressão "
        "linear melhora a estimativa convencional de forma mensurável e roda no próprio microcontrolador, com custo "
        "computacional mínimo. Como próximos passos, propomos persistir o log na flash, usar um broker com "
        "autenticação e TLS e re-treinar o modelo com o histórico real de um posto."))

    s.append(p("Referências", H1))
    s += bullets([
        "Apostilas da disciplina (FIAP, Prof. Dr. Érick Toshio Yamamoto): Aula 01 – Evolução do Processamento: "
        "CPU, GPU e TPU; Aula 02 – Fundamentos de Organização de Dados; Aula 03 – Hierarquia de Memória; Aula 04 – "
        "Memória Secundária; Semana 04 – Arquitetura e Organização de Computadores; Semana 05 – Sistemas Digitais; "
        "Semana 06 – Comunicação entre Periféricos e Processador; Semana 07 – Monitoramento da Comunicação no Wokwi.",
        "ESPRESSIF SYSTEMS. ESP32 Series Datasheet. Disponível em: "
        "https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf.",
        "WOKWI. ESP32 Simulation e Wokwi-GUEST Wi-Fi. Disponível em: https://docs.wokwi.com.",
        "OASIS. MQTT Version 3.1.1. Disponível em: https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/mqtt-v3.1.1.html.",
    ])

    if serial:
        s.append(PageBreak())
        s.append(p("Anexo A – Log do Serial Monitor durante os testes", H1))
        s.append(Preformatted(serial.strip(), MONO, maxLineLength=118))

    doc = SimpleDocTemplate(str(SAIDA), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm,
                            bottomMargin=2 * cm, title="Relatório Técnico - Fila Virtual - Citizen Assist AI",
                            author=", ".join(n for n, _ in INTEGRANTES))
    doc.build(s, onFirstPage=lambda c, d: None, onLaterPages=rodape)
    print(f"Relatório gerado em {SAIDA}")


if __name__ == "__main__":
    main()
