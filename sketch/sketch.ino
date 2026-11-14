/*
 *  Pygmy Owl (Glaucidium passerinum) sound imitation & climate node
 *   - ModulinoBuzzer: synthesizes ~2.0-2.2 kHz pygmy owl whistles
 *   - ModulinoThermo: reads ambient temperature (°C) and humidity
 *   - Arduino_RouterBridge: exposes RPC calls to Linux Python (main.py)
 */

#include "Arduino_RouterBridge.h"
#include <Arduino_Modulino.h>

ModulinoBuzzer buzzer;
ModulinoThermo thermo;

// so called ethical weather limits: avoid stressing birds in cold or rain
// just as an example, in reality could be adjusted more acuratelly
const float MIN_SAFE_TEMP_C = -5.0f;
const float MAX_SAFE_HUMIDITY_RH = 95.0f;

// Track when Linux Python last controlled the MCU over Bridge.
// If Python is driving the loop, we disable the standalone fallback timer
// so the buzzer never interrupts microphone recording unannounced.
unsigned long lastBridgeCallMs = 0;
unsigned long lastAutoBoutMs = 0;
// if we dont hear birds for tool long, play pygmy manually.
// again, trying not to stress birds for too much. In reality, internal should be much longer
// (probably hours) however set to 1 minute for prototyping
const unsigned long AUTO_INTERVAL_MS = 60000;

// Plays a single ~250 ms (0.25 ± 0.02 s) owl whistle with a slight upward onset and tail.
// ~ fundamental frequency is 1412 ± 68 Hz. according to the paper by Galeotti et al (see README)
void playOwlWhistle(int peakFreq) {
  buzzer.tone(peakFreq - 60, 35);
  delay(25);
  buzzer.tone(peakFreq - 20, 35);
  delay(25);
  buzzer.tone(peakFreq, 160);
  delay(150);
  buzzer.tone(peakFreq - 25, 50);
  delay(50);
  buzzer.noTone();
}

// Plays an inverted-U note for the territorial rising scale call
void playScaleNote(int baseFreq) {
  buzzer.tone(baseFreq, 70);
  delay(55);
  buzzer.tone(baseFreq + 60, 80);
  delay(65);
  buzzer.tone(baseFreq + 100, 110);
  delay(95);
  buzzer.tone(baseFreq + 40, 80);
  delay(65);
  buzzer.tone(baseFreq - 20, 60);
  delay(60);
  buzzer.noTone();
}

// Repeated whistle bout (interval 1.79 ± 0.17 s => 1620 - 1960 ms apart)
void playAdvertisingBout(int notes, int freq) {
  if (notes < 1) notes = 1;
  if (notes > 15) notes = 15;
  for (int i = 0; i < notes; i++) {
    playOwlWhistle(freq + random(-15, 16));
    if (i < notes - 1) {
      delay(random(1620, 1961));
    }
  }
}

// Rising 6-note territorial scale call (~1440 Hz ==> ~1615 Hz)
void playScaleCall() {
  for (int i = 0; i < 6; i++) {
    playScaleNote(1440 + i * 55);
    if (i < 5) {
      delay(450);
    }
  }
}

// --- Bridge RPC handlers called from Linux Python ---

float get_temperature() {
  lastBridgeCallMs = millis();
  return thermo.getTemperature();
}

float get_humidity() {
  lastBridgeCallMs = millis();
  return thermo.getHumidity();
}

int is_weather_safe() {
  lastBridgeCallMs = millis();
  float t = thermo.getTemperature();
  float h = thermo.getHumidity();
  return (t >= MIN_SAFE_TEMP_C && h <= MAX_SAFE_HUMIDITY_RH) ? 1 : 0;
}

int play_owl_whistle() {
  lastBridgeCallMs = millis();
  if (!is_weather_safe()) {
    return 0;
  }
  playOwlWhistle(1412);
  return 1;
}

int play_owl_bout(int notes) {
  lastBridgeCallMs = millis();
  if (!is_weather_safe()) {
    return 0;
  }
  playAdvertisingBout(notes, 1412);
  return 1;
}

int play_scale_call() {
  lastBridgeCallMs = millis();
  if (!is_weather_safe()) {
    return 0;
  }
  playScaleCall();
  return 1;
}

int stop_buzzer() {
  lastBridgeCallMs = millis();
  buzzer.noTone();
  return 1;
}

void setup() {
  Bridge.begin();
  Modulino.begin();
  buzzer.begin();
  thermo.begin();

  Bridge.provide("get_temperature", get_temperature);
  Bridge.provide("get_humidity", get_humidity);
  Bridge.provide("is_weather_safe", is_weather_safe);
  Bridge.provide("play_owl_whistle", play_owl_whistle);
  Bridge.provide("play_owl_bout", play_owl_bout);
  Bridge.provide("play_scale_call", play_scale_call);
  Bridge.provide("stop_buzzer", stop_buzzer);

  lastAutoBoutMs = millis();
}

void loop() {
  unsigned long now = millis();
  // Standalone fallback: if Linux Python has not called Bridge in the last 90s,
  // play a short lure bout every 60 seconds (just an example, in reality should be longer)
  bool pythonActive = (lastBridgeCallMs > 0) && ((now - lastBridgeCallMs) < 90000);
  if (!pythonActive && (now - lastAutoBoutMs >= AUTO_INTERVAL_MS)) {
    lastAutoBoutMs = now;
    if (is_weather_safe()) {
      playAdvertisingBout(6, 1412);
    }
  }
  delay(50);
}
