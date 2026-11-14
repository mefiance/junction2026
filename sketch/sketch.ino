/*
 * Eurasian Pygmy Owl (Glaucidium passerinum) Call Generator
 */

#include <Arduino_Modulino.h>

ModulinoBuzzer buzzer;

// Plays a single ~300 ms owl whistle with a slight upward onset and tail
void playOwlWhistle(int peakFreq) {
  buzzer.tone(peakFreq - 80, 50);
  delay(35);
  buzzer.tone(peakFreq - 25, 50);
  delay(35);
  buzzer.tone(peakFreq, 190);
  delay(175);
  buzzer.tone(peakFreq - 30, 55);
  delay(55);
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

// Repeated whistle bout (notes spaced ~1.7 - 2.0 seconds apart)
void playAdvertisingBout(int notes, int freq) {
  for (int i = 0; i < notes; i++) {
    playOwlWhistle(freq + random(-5, 6));
    if (i < notes - 1) {
      delay(random(1700, 2050));
    }
  }
}

// Rising 6-note territorial scale call (~1340 Hz -> ~1615 Hz)
void playScaleCall() {
  for (int i = 0; i < 6; i++) {
    playScaleNote(1340 + i * 55);
    if (i < 5) {
      delay(450);
    }
  }
}

void setup() {
  Modulino.begin();
  buzzer.begin();
  delay(1000);
}

void loop() {
  // 1. Standard advertising call bout (~1340 Hz)
  playAdvertisingBout(10, 1340);
  delay(7000);

  // 2. Slightly higher-pitched bout (~1400 Hz)
  playAdvertisingBout(12, 1400);
  delay(6000);

  // 3. Territorial rising scale call
  playScaleCall();

  // Pause before repeating the cycle
  delay(15000);
}
