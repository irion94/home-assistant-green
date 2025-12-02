/**
 * Browser STT Service - Web Speech API wrapper
 *
 * Provides browser-based speech-to-text using the Web Speech API.
 * Works on Chrome, Safari, and other WebKit-based browsers.
 */

export interface BrowserSTTOptions {
  onStart?: () => void;
  onInterim?: (transcript: string) => void;
  onFinal?: (transcript: string) => void;
  onError?: (error: string) => void;
  onEnd?: () => void;
  lang?: string;
  continuous?: boolean;
}

class BrowserSTTService {
  private recognition: SpeechRecognition | null = null;
  private isListening = false;

  constructor() {
    // @ts-ignore - webkitSpeechRecognition exists in WebKit browsers
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.error('[BrowserSTT] Web Speech API not supported');
      return;
    }
    this.recognition = new SpeechRecognition();
  }

  start(options: BrowserSTTOptions): boolean {
    if (!this.recognition) {
      console.error('[BrowserSTT] Recognition not initialized');
      return false;
    }

    if (this.isListening) {
      console.warn('[BrowserSTT] Already listening');
      return false;
    }

    // Configure recognition
    this.recognition.lang = options.lang || 'pl-PL';
    this.recognition.continuous = options.continuous ?? false;
    this.recognition.interimResults = true;

    // Event handlers
    this.recognition.onstart = () => {
      this.isListening = true;
      console.log('[BrowserSTT] Started');
      options.onStart?.();
    };

    this.recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map(result => result[0].transcript)
        .join('');

      if (event.results[event.results.length - 1].isFinal) {
        console.log('[BrowserSTT] Final result:', transcript);
        options.onFinal?.(transcript);
      } else {
        console.log('[BrowserSTT] Interim result:', transcript);
        options.onInterim?.(transcript);
      }
    };

    this.recognition.onerror = (event) => {
      console.error('[BrowserSTT] Error:', event.error);
      options.onError?.(event.error);
    };

    this.recognition.onend = () => {
      this.isListening = false;
      console.log('[BrowserSTT] Ended');
      options.onEnd?.();
    };

    try {
      this.recognition.start();
      return true;
    } catch (error) {
      console.error('[BrowserSTT] Failed to start:', error);
      return false;
    }
  }

  stop() {
    if (this.recognition && this.isListening) {
      console.log('[BrowserSTT] Stopping');
      this.recognition.stop();
    }
  }

  isAvailable(): boolean {
    return this.recognition !== null;
  }

  getIsListening(): boolean {
    return this.isListening;
  }
}

export const browserSTT = new BrowserSTTService();
