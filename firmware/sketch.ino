/*
 * Global Solution 2026.2 - Computer Organization and Architecture - FIAP
 * Integrantes: Gabriel Fagundes (RM 569074), Glauco Kelly (RM 572840),
 *              Thiago Renatino (RM 569073)
 *
 * Citizen Assist AI - Sistema Inteligente de Gerenciamento de Filas Virtuais
 * Posto de atendimento do Bilhete Único (1 guichê)
 *
 * Hardware (simulado no Wokwi):
 *   CPU ........ ESP32 (Xtensa LX6 dual-core, 240 MHz, 520 KB SRAM, 4 MB flash)
 *   Entradas ... botão VERDE  "chegada"     -> GPIO 15 (interrupção, pull-up interno)
 *                botão AZUL   "atendimento" -> GPIO 13 (interrupção, pull-up interno)
 *                botões virtuais no painel web (comandos MQTT)
 *   Saídas ..... LCD 16x2 I2C (SDA 21, SCL 22) | LED verde GPIO 2 | LED vermelho GPIO 4
 *                Serial Monitor (UART 115200 baud) | painel web (MQTT)
 *   Rede ....... Wi-Fi 802.11 b/g/n -> TCP/IP -> MQTT (broker público) -> painel no navegador
 *
 * Fluxo: ENTRADA (botão/ISR) -> PROCESSAMENTO (fila, histórico, previsão) -> SAÍDA (LCD, LEDs, MQTT)
 *
 * Modo demonstração: 1 segundo real = 1 minuto do posto (ESCALA_DEMO), para que a
 * demonstração caiba no vídeo. Os tempos medidos pelo ESP32 são convertidos para minutos.
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <time.h>
#include "modelo_espera.h"  // coeficientes da regressão (gerado por ia/treinar_previsao.py)

// ---------------- Pinos ----------------
#define BTN_CHEGADA      15
#define BTN_ATENDIMENTO  13
#define LED_VERDE        2
#define LED_VERMELHO     4

// ---------------- Parâmetros ----------------
#define ESCALA_DEMO          60.0f   // 1 s real = 60 s (1 min) do posto
#define DEBOUNCE_MS          50      // tempo que o pino precisa ficar estável para valer
#define PISCA_ERRO_MS        480     // duração do alerta de operação inválida (LED vermelho)
#define MAX_FILA             99      // limite do contador (evita estouro e cabe no LCD)
#define LIMITE_FILA_LONGA    8       // acima disso o LED vermelho acende
#define JANELA_RECENTE       5       // últimos atendimentos usados pela IA
#define TAM_LOG              64      // eventos guardados em RAM (buffer circular)
#define PESO_HISTORICO       20      // peso da média histórica inicial (atendimentos "virtuais")
#define INTERVALO_ESTADO_MS  5000    // publicação periódica do estado

// ---------------- Rede ----------------
const char* WIFI_SSID   = "Wokwi-GUEST";
const char* WIFI_SENHA  = "";
const char* MQTT_BROKER = "broker.hivemq.com";
const int   MQTT_PORTA  = 1883;
const char* TOPICO_BASE = "fiap/gs2026/citizenassist/fila/posto-bu-01";
String TOPICO_ESTADO, TOPICO_EVENTO, TOPICO_COMANDO;

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);
LiquidCrystal_I2C lcd(0x27, 16, 2);

// ---------------- Tipos ----------------
typedef enum : uint8_t { EV_CHEGADA = 0, EV_CONCLUSAO = 1, EV_INVALIDO = 2, EV_FILA_CHEIA = 3 } TipoEvento;
const char* NOME_EVENTO[] = {"CHEGADA", "CONCLUSAO", "SAIDA_FILA_VAZIA", "FILA_CHEIA"};

typedef struct {
  uint32_t epoch;         // horário (NTP) ou segundos desde o boot se sem NTP
  uint32_t ciclo;         // ciclo do loop em que o evento foi processado
  uint8_t  tipo;          // TipoEvento
  uint8_t  origem;        // 0 = botão físico, 1 = painel web
  uint16_t fila;          // pessoas na fila depois do evento
  float    esperaIA;      // estimativa da IA logo após o evento (min)
} Evento;                 // 16 bytes com alinhamento

// Botão com debounce por estado estável:
// a ISR só anota que o pino mudou; o loop() confirma o toque quando o pino
// fica em LOW por DEBOUNCE_MS e antes estava em HIGH (borda de descida real).
// Assim o repique ao SOLTAR o botão não vira um segundo toque.
typedef struct {
  uint8_t           pino;
  volatile uint32_t ultimaBordaMs;   // escrito pela ISR
  volatile bool     houveBorda;      // escrito pela ISR
  bool              estadoEstavel;   // HIGH = solto (pull-up), LOW = apertado
} Botao;

// ---------------- Estado (RAM) ----------------
Botao botaoChegada     = {BTN_CHEGADA, 0, false, HIGH};
Botao botaoAtendimento = {BTN_ATENDIMENTO, 0, false, HIGH};
uint32_t erroAteMs = 0;                  // LED vermelho pisca até este instante (sem delay)

uint16_t fila = 0;
uint32_t concluidos = 0;
uint32_t invalidas = 0;
uint32_t inicioAtendimentoMs = 0;       // quando começou o atendimento atual
float    temposRecentes[JANELA_RECENTE]; // buffer circular dos últimos atendimentos (min)
uint8_t  qtdRecentes = 0, posRecentes = 0;
float    somaHistorica = 0;              // média histórica acumulada
uint32_t nHistorico = 0;

Evento   logEventos[TAM_LOG];
uint16_t qtdLog = 0, posLog = 0;
uint32_t ciclo = 0;
uint32_t ultimoEstadoMs = 0;
bool     ntpOk = false;

// ---------------- ISRs (curtas: só registram que o pino mudou) ----------------
void IRAM_ATTR isrChegada() {
  botaoChegada.ultimaBordaMs = millis();
  botaoChegada.houveBorda = true;
}

void IRAM_ATTR isrAtendimento() {
  botaoAtendimento.ultimaBordaMs = millis();
  botaoAtendimento.houveBorda = true;
}

// Retorna true uma única vez por toque, depois que o sinal estabiliza
bool toqueConfirmado(Botao& b) {
  if (!b.houveBorda || millis() - b.ultimaBordaMs < DEBOUNCE_MS) return false;
  b.houveBorda = false;
  bool leitura = digitalRead(b.pino);
  bool apertou = (b.estadoEstavel == HIGH && leitura == LOW);
  b.estadoEstavel = leitura;
  return apertou;
}

// ---------------- Cálculos ----------------
float mediaHistorica() { return somaHistorica / nHistorico; }

float tempoMedioRecente() {
  if (qtdRecentes == 0) return mediaHistorica();  // sem histórico do dia: usa a média
  float s = 0;
  for (uint8_t i = 0; i < qtdRecentes; i++) s += temposRecentes[i];
  return s / qtdRecentes;
}

// Espera estimada para quem chegar agora (há "fila" pessoas à frente)
float esperaConvencional() { return fila * mediaHistorica(); }

float esperaIA() {
  if (fila == 0) return 0;
  float e = MODELO_B0 + MODELO_B1 * fila + MODELO_B2 * (fila * tempoMedioRecente());
  return e < 0 ? 0 : e;
}

String horario(uint32_t epoch) {
  if (!ntpOk) return String(epoch) + "s";
  time_t t = epoch;
  struct tm tm;
  localtime_r(&t, &tm);
  char buf[20];
  strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", &tm);
  return String(buf);
}

uint32_t agoraEpoch() {
  if (ntpOk) return (uint32_t)time(nullptr);
  return millis() / 1000;
}

// ---------------- Saídas ----------------
void atualizarLeds() {
  digitalWrite(LED_VERDE, fila < LIMITE_FILA_LONGA ? HIGH : LOW);
  digitalWrite(LED_VERMELHO, fila >= LIMITE_FILA_LONGA ? HIGH : LOW);
}

// Alerta sem delay(): o loop continua livre enquanto o LED pisca
void piscarErro() { erroAteMs = millis() + PISCA_ERRO_MS; }

void atualizarAlerta() {
  if (erroAteMs == 0) return;
  if ((int32_t)(millis() - erroAteMs) < 0) {
    digitalWrite(LED_VERMELHO, (millis() / 80) % 2 ? HIGH : LOW);
  } else {
    erroAteMs = 0;
    atualizarLeds();
  }
}

void atualizarLcd() {
  char l1[17], l2[17];
  snprintf(l1, sizeof(l1), "Fila:%02u Ok:%-5lu", fila, (unsigned long)concluidos);
  snprintf(l2, sizeof(l2), "IA:%3.0fm Med:%3.0fm", esperaIA(), esperaConvencional());
  lcd.setCursor(0, 0); lcd.print(l1);
  lcd.setCursor(0, 1); lcd.print(l2);
}

String jsonEstado() {
  String j = "{";
  j += "\"posto\":\"posto-bu-01\",";
  j += "\"fila\":" + String(fila) + ",";
  j += "\"concluidos\":" + String(concluidos) + ",";
  j += "\"operacoes_invalidas\":" + String(invalidas) + ",";
  j += "\"espera_ia_min\":" + String(esperaIA(), 1) + ",";
  j += "\"espera_media_min\":" + String(esperaConvencional(), 1) + ",";
  j += "\"tempo_medio_recente_min\":" + String(tempoMedioRecente(), 2) + ",";
  j += "\"media_historica_min\":" + String(mediaHistorica(), 2) + ",";
  j += "\"ciclo\":" + String(ciclo) + ",";
  j += "\"uptime_s\":" + String(millis() / 1000) + ",";
  j += "\"heap_livre_bytes\":" + String(ESP.getFreeHeap()) + ",";
  j += "\"horario\":\"" + horario(agoraEpoch()) + "\"";
  j += "}";
  return j;
}

void publicarEstado() {
  if (!mqtt.connected()) return;
  mqtt.publish(TOPICO_ESTADO.c_str(), jsonEstado().c_str(), true);  // retain: painel recebe ao abrir
  ultimoEstadoMs = millis();
}

void publicarEvento(const Evento& e) {
  if (!mqtt.connected()) return;
  String j = "{\"tipo\":\"" + String(NOME_EVENTO[e.tipo]) + "\",";
  j += "\"origem\":\"" + String(e.origem ? "web" : "botao") + "\",";
  j += "\"fila\":" + String(e.fila) + ",";
  j += "\"espera_ia_min\":" + String(e.esperaIA, 1) + ",";
  j += "\"ciclo\":" + String(e.ciclo) + ",";
  j += "\"horario\":\"" + horario(e.epoch) + "\"}";
  mqtt.publish(TOPICO_EVENTO.c_str(), j.c_str());
}

// ---------------- Processamento dos eventos ----------------
void registrarEvento(TipoEvento tipo, uint8_t origem) {
  Evento e = {agoraEpoch(), ciclo, (uint8_t)tipo, origem, fila, esperaIA()};
  logEventos[posLog] = e;                  // buffer circular: sobrescreve o mais antigo
  posLog = (posLog + 1) % TAM_LOG;
  if (qtdLog < TAM_LOG) qtdLog++;
  Serial.printf("[EVENT] %s | %s | origem=%s | fila=%u | ciclo=%lu\n", horario(e.epoch).c_str(),
                NOME_EVENTO[tipo], origem ? "web" : "botao", fila, (unsigned long)ciclo);
  publicarEvento(e);
}

void processarChegada(uint8_t origem) {
  Serial.printf("[DATA] Entrada CHEGADA (%s)\n", origem ? "painel web" : "GPIO 15");
  if (fila >= MAX_FILA) {
    Serial.printf("[LOGIC] fila=%u >= MAX_FILA=%d -> operacao invalida (contador no limite)\n", fila, MAX_FILA);
    invalidas++;
    registrarEvento(EV_FILA_CHEIA, origem);
    Serial.println("[ACTION] LED vermelho pisca | chegada recusada");
    piscarErro();
    return;
  }
  if (fila == 0) inicioAtendimentoMs = millis();  // guichê livre: atendimento começa já
  fila++;
  Serial.printf("[LOGIC] fila %u -> %u | espera IA=%.1f min | media=%.1f min\n",
                fila - 1, fila, esperaIA(), esperaConvencional());
  registrarEvento(EV_CHEGADA, origem);
}

void processarAtendimento(uint8_t origem) {
  Serial.printf("[DATA] Entrada ATENDIMENTO CONCLUIDO (%s)\n", origem ? "painel web" : "GPIO 13");
  if (fila == 0) {
    Serial.println("[LOGIC] fila=0 -> saida com fila vazia: operacao invalida, contador nao muda");
    invalidas++;
    registrarEvento(EV_INVALIDO, origem);
    Serial.println("[ACTION] LED vermelho pisca | LCD mantem fila=00");
    piscarErro();
    return;
  }
  // Tempo de atendimento medido pelo ESP32 (convertido para minutos do posto)
  float duracaoMin = (millis() - inicioAtendimentoMs) / 1000.0f * ESCALA_DEMO / 60.0f;
  temposRecentes[posRecentes] = duracaoMin;
  posRecentes = (posRecentes + 1) % JANELA_RECENTE;
  if (qtdRecentes < JANELA_RECENTE) qtdRecentes++;
  somaHistorica += duracaoMin;
  nHistorico++;

  fila--;
  concluidos++;
  if (fila > 0) inicioAtendimentoMs = millis();  // próximo da fila começa a ser atendido
  Serial.printf("[LOGIC] atendimento durou %.1f min | recente=%.2f | historica=%.2f | fila %u -> %u\n",
                duracaoMin, tempoMedioRecente(), mediaHistorica(), fila + 1, fila);
  registrarEvento(EV_CONCLUSAO, origem);
}

void aposEvento() {
  atualizarLeds();
  atualizarLcd();
  Serial.printf("[ACTION] LCD fila=%u | LED %s | MQTT %s\n", fila,
                fila >= LIMITE_FILA_LONGA ? "VERMELHO" : "VERDE",
                mqtt.connected() ? "estado publicado" : "offline (estado mantido localmente)");
  publicarEstado();
}

// Comandos dos botões virtuais do painel (MQTT)
void aoReceberMqtt(char* topico, byte* payload, unsigned int tam) {
  String cmd;
  for (unsigned int i = 0; i < tam; i++) cmd += (char)payload[i];
  cmd.trim();
  Serial.printf("[NET] comando recebido: %s\n", cmd.c_str());
  if (cmd == "chegada")          processarChegada(1);
  else if (cmd == "atendimento") processarAtendimento(1);
  else if (cmd == "estado")      { publicarEstado(); return; }
  else { Serial.println("[LOGIC] comando desconhecido -> ignorado"); return; }
  aposEvento();
}

// ---------------- Rede ----------------
// Rede não bloqueante: os botões e o LCD funcionam mesmo sem Wi-Fi.
// O loop() verifica o estado da conexão a cada volta (polling) e avança as etapas.
bool redeConfigurada = false;
uint32_t ultimoAvisoWifi = 0;

void iniciarWifi() {
  Serial.printf("[NET] Wi-Fi: conectando a %s (em segundo plano)\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_SENHA, 6);
}

void gerenciarWifi() {
  if (WiFi.status() == WL_CONNECTED) {
    if (!redeConfigurada) {
      redeConfigurada = true;
      Serial.printf("[NET] Wi-Fi OK | IP %s | RSSI %d dBm\n", WiFi.localIP().toString().c_str(), WiFi.RSSI());
      configTime(-3 * 3600, 0, "pool.ntp.org", "time.google.com");  // horário de Brasília
    }
    if (!ntpOk && time(nullptr) > 1700000000) {  // relógio já recebeu a hora da internet
      ntpOk = true;
      Serial.printf("[NET] NTP sincronizado: %s\n", horario(agoraEpoch()).c_str());
    }
  } else {
    if (redeConfigurada) {
      redeConfigurada = false;
      Serial.println("[NET] Wi-Fi caiu: sistema segue local, reconectando...");
      WiFi.reconnect();
    }
    if (millis() - ultimoAvisoWifi > 10000) {
      ultimoAvisoWifi = millis();
      Serial.println("[NET] aguardando Wi-Fi (fila continua funcionando localmente)");
    }
  }
}

void conectarMqtt() {
  if (WiFi.status() != WL_CONNECTED || mqtt.connected()) return;
  String id = "citizenassist-fila-" + String((uint32_t)ESP.getEfuseMac(), HEX);
  Serial.printf("[NET] Conectando ao broker MQTT %s:%d ... ", MQTT_BROKER, MQTT_PORTA);
  if (mqtt.connect(id.c_str())) {
    mqtt.subscribe(TOPICO_COMANDO.c_str());
    Serial.println("OK");
    publicarEstado();
  } else {
    Serial.printf("falhou (rc=%d), nova tentativa em 5 s\n", mqtt.state());
  }
}

// ---------------- Setup / Loop ----------------
void setup() {
  Serial.begin(115200);
  pinMode(BTN_CHEGADA, INPUT_PULLUP);
  pinMode(BTN_ATENDIMENTO, INPUT_PULLUP);
  pinMode(LED_VERDE, OUTPUT);
  pinMode(LED_VERMELHO, OUTPUT);
  // Interrupção em qualquer mudança (apertar e soltar): o debounce confirma só a descida
  attachInterrupt(digitalPinToInterrupt(BTN_CHEGADA), isrChegada, CHANGE);
  attachInterrupt(digitalPinToInterrupt(BTN_ATENDIMENTO), isrAtendimento, CHANGE);

  // Histórico inicial: média dos atendimentos simulados, com peso de 20 atendimentos
  somaHistorica = MEDIA_HISTORICA_INICIAL_MIN * PESO_HISTORICO;
  nHistorico = PESO_HISTORICO;

  TOPICO_ESTADO  = String(TOPICO_BASE) + "/estado";
  TOPICO_EVENTO  = String(TOPICO_BASE) + "/evento";
  TOPICO_COMANDO = String(TOPICO_BASE) + "/comando";

  Wire.begin(21, 22);
  lcd.init();
  lcd.backlight();
  lcd.print("Citizen Assist");
  lcd.setCursor(0, 1);
  lcd.print("Fila virtual...");

  Serial.println("[INFO] Citizen Assist AI - Fila Virtual (posto Bilhete Unico)");
  Serial.printf("[INFO] CPU %s rev%d | %d nucleos | Clock %lu MHz\n", ESP.getChipModel(),
                ESP.getChipRevision(), ESP.getChipCores(), (unsigned long)getCpuFrequencyMhz());
  Serial.printf("[INFO] Flash %lu KB | Sketch %lu KB | Heap livre %lu bytes\n",
                (unsigned long)(ESP.getFlashChipSize() / 1024), (unsigned long)(ESP.getSketchSize() / 1024),
                (unsigned long)ESP.getFreeHeap());
  Serial.printf("[INFO] RAM do log de eventos: %u x %u bytes = %u bytes\n",
                TAM_LOG, (unsigned)sizeof(Evento), (unsigned)sizeof(logEventos));
  Serial.printf("[INFO] Modelo IA: b0=%.3f b1=%.3f b2=%.3f | media historica inicial=%.2f min\n",
                MODELO_B0, MODELO_B1, MODELO_B2, MEDIA_HISTORICA_INICIAL_MIN);

  iniciarWifi();
  mqtt.setServer(MQTT_BROKER, MQTT_PORTA);
  mqtt.setCallback(aoReceberMqtt);
  mqtt.setBufferSize(512);

  atualizarLeds();
  atualizarLcd();
  Serial.println("[INFO] Sistema pronto. Botao VERDE = chegada | Botao AZUL = atendimento concluido");
}

uint32_t ultimaTentativaMqtt = 0;

void loop() {
  ciclo++;

  // Botões: a ISR avisou que houve borda; aqui o toque é confirmado (debounce)
  if (toqueConfirmado(botaoChegada)) {
    Serial.printf("[CICLO %lu]\n", (unsigned long)ciclo);
    processarChegada(0);
    aposEvento();
  }
  if (toqueConfirmado(botaoAtendimento)) {
    Serial.printf("[CICLO %lu]\n", (unsigned long)ciclo);
    processarAtendimento(0);
    aposEvento();
  }
  atualizarAlerta();

  // Rede: Wi-Fi, NTP e MQTT verificados por polling a cada volta do loop
  gerenciarWifi();
  if (WiFi.status() == WL_CONNECTED && !mqtt.connected() && millis() - ultimaTentativaMqtt > 5000) {
    ultimaTentativaMqtt = millis();
    conectarMqtt();
  }
  mqtt.loop();

  // Atualização periódica: o tempo passa, a estimativa e o horário mudam
  if (millis() - ultimoEstadoMs > INTERVALO_ESTADO_MS) {
    atualizarLcd();
    publicarEstado();
  }
  delay(10);  // loop curto: os botões não dependem dele (interrupção)
}
