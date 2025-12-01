import { useState, useRef, useCallback, useEffect } from 'react'
import { Mic, MicOff, Send, Loader2, Volume2, VolumeX } from 'lucide-react'
import { gatewayClient } from '../../../api'
import { classNames } from '../../../utils/formatters'

type VoiceState = 'idle' | 'listening' | 'processing' | 'speaking'

export default function VoicePanel() {
  const [state, setState] = useState<VoiceState>('idle')
  const [lastMessage, setLastMessage] = useState<string>('')
  const [lastResponse, setLastResponse] = useState<string>('')
  const [inputText, setInputText] = useState('')
  const [sessionId] = useState(() => `kiosk-${Date.now()}`)
  const [interimTranscript, setInterimTranscript] = useState('')
  const recognitionRef = useRef<SpeechRecognition | null>(null)
  const [isSupported, setIsSupported] = useState(true)
  const [ttsEnabled, setTtsEnabled] = useState(true)
  const [isSpeaking, setIsSpeaking] = useState(false)

  // TTS function
  const speakText = useCallback((text: string) => {
    if (!ttsEnabled || !window.speechSynthesis) return

    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    const hasPolish = /[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]/.test(text)
    utterance.lang = hasPolish ? 'pl-PL' : 'en-US'
    utterance.rate = 1.1

    utterance.onstart = () => setIsSpeaking(true)
    utterance.onend = () => setIsSpeaking(false)
    utterance.onerror = () => setIsSpeaking(false)

    window.speechSynthesis.speak(utterance)
  }, [ttsEnabled])

  const stopSpeaking = useCallback(() => {
    window.speechSynthesis.cancel()
    setIsSpeaking(false)
  }, [])

  // Send text to AI
  const sendText = useCallback(async (text: string) => {
    if (!text.trim()) return

    setLastMessage(text)
    setState('processing')

    try {
      const response = await gatewayClient.conversation(text, sessionId)
      const responseText = response.text || response.message || 'No response'
      setLastResponse(responseText)
      speakText(responseText)
      setState('idle')
    } catch {
      setLastResponse('Error processing request')
      setState('idle')
    }
  }, [sessionId, speakText])

  // Initialize speech recognition
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      setIsSupported(false)
      return
    }

    const recognition = new SpeechRecognition()
    recognition.continuous = false
    recognition.interimResults = true
    recognition.lang = 'pl-PL'

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let finalTranscript = ''
      let interimText = ''

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]
        if (result.isFinal) {
          finalTranscript += result[0].transcript
        } else {
          interimText += result[0].transcript
        }
      }

      setInterimTranscript(interimText)

      if (finalTranscript) {
        setInterimTranscript('')
        sendText(finalTranscript)
      }
    }

    recognition.onend = () => {
      if (state === 'listening') {
        setState('idle')
      }
    }

    recognition.onerror = () => {
      setState('idle')
    }

    recognitionRef.current = recognition

    return () => {
      recognition.abort()
    }
  }, [sendText, state])

  const toggleListening = useCallback(() => {
    if (state === 'listening') {
      recognitionRef.current?.stop()
      setState('idle')
    } else if (state === 'idle') {
      setInterimTranscript('')
      recognitionRef.current?.start()
      setState('listening')
    }
  }, [state])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (inputText.trim()) {
      sendText(inputText)
      setInputText('')
    }
  }

  return (
    <div className="h-full flex flex-col bg-surface rounded-2xl p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-kiosk-xl font-bold">Voice</h2>
        <button
          onClick={() => {
            if (isSpeaking) stopSpeaking()
            setTtsEnabled(!ttsEnabled)
          }}
          className="p-2 rounded-lg hover:bg-surface-light"
        >
          {ttsEnabled ? (
            <Volume2 className="w-5 h-5 text-primary" />
          ) : (
            <VolumeX className="w-5 h-5 text-text-secondary" />
          )}
        </button>
      </div>

      {/* Last conversation */}
      <div className="flex-1 overflow-y-auto space-y-3 mb-4">
        {lastMessage && (
          <div className="p-3 bg-primary/20 rounded-lg">
            <p className="text-sm text-text-secondary mb-1">You</p>
            <p>{lastMessage}</p>
          </div>
        )}
        {lastResponse && (
          <div className="p-3 bg-surface-light rounded-lg">
            <p className="text-sm text-text-secondary mb-1">Assistant</p>
            <p>{lastResponse}</p>
          </div>
        )}
        {interimTranscript && (
          <div className="p-3 bg-surface-light/50 rounded-lg animate-pulse">
            <p className="text-text-secondary">{interimTranscript}</p>
          </div>
        )}
      </div>

      {/* Microphone Button */}
      <div className="flex justify-center mb-4">
        <button
          onClick={toggleListening}
          disabled={!isSupported || state === 'processing'}
          className={classNames(
            'w-20 h-20 rounded-full flex items-center justify-center transition-all',
            state === 'listening'
              ? 'bg-error animate-pulse'
              : state === 'processing'
                ? 'bg-warning'
                : 'bg-primary hover:bg-primary-dark',
            (!isSupported || state === 'processing') && 'opacity-50'
          )}
        >
          {state === 'processing' ? (
            <Loader2 className="w-8 h-8 text-white animate-spin" />
          ) : state === 'listening' ? (
            <MicOff className="w-8 h-8 text-white" />
          ) : (
            <Mic className="w-8 h-8 text-white" />
          )}
        </button>
      </div>

      {/* Text Input */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Type a message..."
          className="flex-1 bg-surface-light rounded-lg px-4 py-3 text-white placeholder-text-secondary"
          disabled={state === 'processing'}
        />
        <button
          type="submit"
          disabled={!inputText.trim() || state === 'processing'}
          className="p-3 bg-primary rounded-lg hover:bg-primary-dark disabled:opacity-50"
        >
          <Send className="w-5 h-5" />
        </button>
      </form>
    </div>
  )
}
