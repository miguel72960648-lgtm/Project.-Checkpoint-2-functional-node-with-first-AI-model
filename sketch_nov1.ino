#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <HTTPClient.h>

#define SS_PIN 5
#define RST_PIN 22

const char* WIFI_SSID = "";
const char* WIFI_PASS = "";
const char* SERVIDOR  = "";

MFRC522 rfid(SS_PIN, RST_PIN);
String ultimoTrabajador = "";
unsigned long ultimoTrabajadorMs = 0;
const unsigned long VENTANA_MS = 30000;  

String leerUID() {
  String uid = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    if (rfid.uid.uidByte[i] < 0x10) uid += "0";
    uid += String(rfid.uid.uidByte[i], HEX);
  }
  uid.toUpperCase();
  return uid;
}

void conectarWiFi() {
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Conectando a WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi conectado. IP del ESP32: " + WiFi.localIP().toString());
}

void enviarEvento(String trabajador, String herramienta) {
  if (WiFi.status() != WL_CONNECTED) conectarWiFi();

  HTTPClient http;
  http.begin(SERVIDOR);
  http.addHeader("Content-Type", "application/x-www-form-urlencoded");
  String body = "trabajador_uid=" + trabajador + "&herramienta_uid=" + herramienta;
  int codigo = http.POST(body);
  String respuesta = http.getString();
  Serial.print("HTTP ");
  Serial.print(codigo);
  Serial.print(" -> ");
  Serial.println(respuesta);
  http.end();
}

void setup() {
  Serial.begin(115200);
  SPI.begin();
  rfid.PCD_Init();
  conectarWiFi();
  Serial.println("Listo. Acerca tarjeta de trabajador y luego la herramienta.");
}

void loop() {
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) return;

  String uid = leerUID();
  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();

  // Tarjeta de trabajador: se identifica con la tarjeta blanca registrada
  if (uid == "8496898E") {
    ultimoTrabajador = uid;
    ultimoTrabajadorMs = millis();
    Serial.println("Trabajador identificado: " + uid + ". Ahora acerca la herramienta.");
    return;
  }

  // Cualquier otro tag se toma como herramienta
  if (ultimoTrabajador != "" && millis() - ultimoTrabajadorMs < VENTANA_MS) {
    Serial.println("Herramienta: " + uid);
    enviarEvento(ultimoTrabajador, uid);
    ultimoTrabajador = "";
  } else {
    Serial.println("Primero acerca la tarjeta del trabajador.");
  }
  delay(1500);  // evita leer el mismo tag varias veces seguidas
}