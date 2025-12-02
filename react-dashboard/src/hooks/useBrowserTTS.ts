import { useCallback, useEffect, useRef } from 'react';

/**
 * Hook for browser Text-to-Speech using Web Speech Synthesis API.
 *
 * Automatically detects Polish vs English and speaks with appropriate voice.
 * Used for dashboard sessions where RPi speakers are not available.
 */
export const useBrowserTTS = () => {
  const isSpeakingRef = useRef(false);
  const currentUtteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  /**
   * Speak text using browser TTS.
   * @param text - Text to speak
   * @param onEnd - Optional callback when speech finishes
   */
  const speak = useCallback((text: string, onEnd?: () => void) => {
    // Validate text input
    if (!text || typeof text !== 'string' || text.trim().length === 0) {
      console.warn('[BrowserTTS] Invalid text, skipping:', text);
      return;
    }

    if (!window.speechSynthesis) {
      console.warn('[BrowserTTS] Web Speech Synthesis API not available');
      return;
    }

    // Ensure text is a string (handle undefined/null)
    const safeText = String(text).trim();

    // Cancel any ongoing speech
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(safeText);

    // Auto-detect language (Polish vs English)
    // Check 1: Polish special characters
    const hasPolishChars = /[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]/.test(safeText);

    // Check 2: Common Polish words (case-insensitive)
    const polishWords = /\b(jest|która|godzina|teraz|dzisiaj|jutro|wczoraj|tak|nie|proszę|dziękuję|dobry|dzień|rano|wieczór|włącz|wyłącz|temperatura|pogoda)\b/i;
    const hasPolishWords = polishWords.test(safeText);

    // Use Polish if either check matches
    utterance.lang = (hasPolishChars || hasPolishWords) ? 'pl-PL' : 'en-US';
    utterance.rate = 1.1; // Slightly faster for natural speech
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    utterance.onstart = () => {
      isSpeakingRef.current = true;
      console.log(`[BrowserTTS] Speaking: "${safeText.substring(0, 50)}..." (${utterance.lang})`);
    };

    utterance.onend = () => {
      isSpeakingRef.current = false;
      currentUtteranceRef.current = null;
      console.log('[BrowserTTS] Speech finished');
      onEnd?.();
    };

    utterance.onerror = (event) => {
      console.error('[BrowserTTS] Speech error:', event.error);
      isSpeakingRef.current = false;
      currentUtteranceRef.current = null;
    };

    currentUtteranceRef.current = utterance;
    window.speechSynthesis.speak(utterance);
  }, []);

  /**
   * Stop current speech.
   */
  const stop = useCallback(() => {
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
      isSpeakingRef.current = false;
      currentUtteranceRef.current = null;
      console.log('[BrowserTTS] Speech stopped');
    }
  }, []);

  /**
   * Check if currently speaking.
   */
  const isSpeaking = useCallback(() => {
    return isSpeakingRef.current || window.speechSynthesis?.speaking || false;
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  return { speak, stop, isSpeaking };
};
