import { useEffect, useCallback, useRef } from 'react';
import { useVoiceStore } from '../stores/voiceStore';
import { mqttService } from '../services/mqttService';

export const useRemoteSTT = () => {
  const roomId = useVoiceStore((state) => state.roomId);
  const hybridSTTEnabled = useVoiceStore((state) => state.hybridSTTEnabled);
  const setBrowserSTTAvailable = useVoiceStore((state) => state.setBrowserSTTAvailable);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      console.warn('[RemoteSTT] Web Speech API not available');
      setBrowserSTTAvailable(false);
      return;
    }

    recognitionRef.current = new SpeechRecognition();
    recognitionRef.current.continuous = false;
    recognitionRef.current.interimResults = false;
    recognitionRef.current.lang = 'pl-PL';

    // Pre-request microphone permission on app load
    requestMicrophonePermission();

    setBrowserSTTAvailable(true);
  }, [setBrowserSTTAvailable]);

  const requestMicrophonePermission = async () => {
    try {
      const SpeechRecognition = window.SpeechRecognition || (window as any).webkitSpeechRecognition;
      const tempRecognition = new SpeechRecognition();
      tempRecognition.start();
      setTimeout(() => tempRecognition.stop(), 100);
      console.log('[RemoteSTT] Microphone permission granted');
    } catch (error) {
      console.error('[RemoteSTT] Microphone permission denied:', error);
      setBrowserSTTAvailable(false);
    }
  };

  const handleSTTRequest = useCallback(async (payload: { sessionId: string; timestamp: number }) => {
    if (!hybridSTTEnabled || !recognitionRef.current) {
      console.warn('[RemoteSTT] Hybrid STT disabled or unavailable');
      return;
    }

    console.log(`[RemoteSTT] Starting browser STT for session: ${payload.sessionId}`);

    const recognition = recognitionRef.current;

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = event.results[0][0].transcript;
      const confidence = event.results[0][0].confidence;

      console.log(`[RemoteSTT] Transcription: "${transcript}" (confidence: ${confidence})`);

      mqttService.publishBrowserSTTResponse(roomId, payload.sessionId, transcript, confidence);
    };

    recognition.onerror = (event: any) => {
      console.error('[RemoteSTT] Speech recognition error:', event.error);
      // Do not publish response - let RPI timeout and fallback
    };

    try {
      recognition.start();
    } catch (error) {
      console.error('[RemoteSTT] Failed to start recognition:', error);
    }
  }, [hybridSTTEnabled, roomId]);

  return { handleSTTRequest };
};
