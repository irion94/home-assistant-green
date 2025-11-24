import { useState, useRef, useCallback, useEffect } from 'react'
import { Mic, MicOff, Send, Loader2, Volume2, VolumeX } from 'lucide-react'
import { Button } from '../components/common'
import { gatewayClient } from '../api'
import { classNames } from '../utils/formatters'

type VoiceState = 'idle' | 'listening' | 'processing' | 'speaking'

interface Message {
  id: string
  type: 'user' | 'assistant'
  text: string
  timestamp: Date
}

// Web Speech API types
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList
  resultIndex: number
}

interface SpeechRecognitionResultList {
  length: number
  item(index: number): SpeechRecognitionResult
  [index: number]: SpeechRecognitionResult
}

interface SpeechRecognitionResult {
  isFinal: boolean
  length: number
  item(index: number): SpeechRecognitionAlternative
  [index: number]: SpeechRecognitionAlternative
}

interface SpeechRecognitionAlternative {
  transcript: string
  confidence: number
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean
  interimResults: boolean
  lang: string
  start(): void
  stop(): void
  abort(): void
  onresult: ((event: SpeechRecognitionEvent) => void) | null
  onerror: ((event: Event & { error: string }) => void) | null
  onend: (() => void) | null
  onstart: (() => void) | null
}

declare global {
  interface Window {
    SpeechRecognition: new () => SpeechRecognition
    webkitSpeechRecognition: new () => SpeechRecognition
  }
}

export default function VoiceAssistant() {
  const [state, setState] = useState<VoiceState>('idle')
  const [messages, setMessages] = useState<Message[]>([])
  const [inputText, setInputText] = useState('')
  const [sessionId] = useState(() => `session-${Date.now()}`)
  const [error, setError] = useState<string | null>(null)
  const [interimTranscript, setInterimTranscript] = useState('')
  const recognitionRef = useRef<SpeechRecognition | null>(null)
  const [isSupported, setIsSupported] = useState(true)
  const [ttsEnabled, setTtsEnabled] = useState(true)
  const [isSpeaking, setIsSpeaking] = useState(false)

  // Text-to-speech function
  const speakText = useCallback((text: string) => {
    if (!ttsEnabled || !window.speechSynthesis) return

    // Cancel any ongoing speech
    window.speechSynthesis.cancel()

    const utterance = new SpeechSynthesisUtterance(text)

    // Detect language (simple check for Polish characters)
    const hasPolish = /[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]/.test(text)
    utterance.lang = hasPolish ? 'pl-PL' : 'en-US'

    utterance.rate = 1.1 // Slightly faster
    utterance.pitch = 1.0

    utterance.onstart = () => setIsSpeaking(true)
    utterance.onend = () => setIsSpeaking(false)
    utterance.onerror = () => setIsSpeaking(false)

    window.speechSynthesis.speak(utterance)
  }, [ttsEnabled])

  // Stop speaking
  const stopSpeaking = useCallback(() => {
    window.speechSynthesis.cancel()
    setIsSpeaking(false)
  }, [])

  // Initialize speech recognition
  useEffect(() => {
    const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognitionAPI) {
      setIsSupported(false)
      setError('Speech recognition not supported in this browser')
      return
    }

    const recognition = new SpeechRecognitionAPI()
    recognition.continuous = false
    recognition.interimResults = true
    recognition.lang = 'pl-PL' // Polish, change to 'en-US' for English

    recognition.onstart = () => {
      setState('listening')
      setError(null)
      setInterimTranscript('')
    }

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interim = ''
      let final = ''

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript
        if (event.results[i].isFinal) {
          final += transcript
        } else {
          interim += transcript
        }
      }

      setInterimTranscript(interim)

      if (final) {
        setInterimTranscript('')
        handleTranscription(final.trim())
      }
    }

    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error)
      if (event.error === 'no-speech') {
        setError('No speech detected. Try again.')
      } else if (event.error === 'audio-capture') {
        setError('Microphone not available')
      } else if (event.error === 'not-allowed') {
        setError('Microphone permission denied')
      } else {
        setError(`Speech error: ${event.error}`)
      }
      setState('idle')
      setInterimTranscript('')
    }

    recognition.onend = () => {
      if (state === 'listening') {
        setState('idle')
      }
      setInterimTranscript('')
    }

    recognitionRef.current = recognition

    return () => {
      recognition.abort()
    }
  }, [])

  const addMessage = useCallback((type: 'user' | 'assistant', text: string) => {
    setMessages(prev => [
      ...prev,
      {
        id: `${Date.now()}-${Math.random()}`,
        type,
        text,
        timestamp: new Date(),
      },
    ])
  }, [])

  const handleTranscription = async (text: string) => {
    if (!text) return

    // Stop any ongoing speech before processing new command
    stopSpeaking()

    addMessage('user', text)
    setState('processing')

    try {
      const response = await gatewayClient.conversation(text, sessionId)
      const responseText = response.text || response.message || 'No response'
      addMessage('assistant', responseText)

      // Speak the response
      speakText(responseText)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to send command'
      setError(message)
      addMessage('assistant', `Error: ${message}`)
    } finally {
      setState('idle')
    }
  }

  const sendTextCommand = async () => {
    if (!inputText.trim()) return

    const text = inputText.trim()
    setInputText('')
    handleTranscription(text)
  }

  const startListening = () => {
    if (!recognitionRef.current || !isSupported) return

    try {
      setError(null)
      recognitionRef.current.start()
    } catch (err) {
      console.error('Failed to start recognition:', err)
      setError('Failed to start speech recognition')
    }
  }

  const stopListening = () => {
    if (!recognitionRef.current) return
    recognitionRef.current.stop()
  }

  const handleMicClick = () => {
    if (state === 'listening') {
      stopListening()
    } else if (state === 'idle') {
      startListening()
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="mb-4 flex justify-between items-start">
        <div>
          <h1 className="text-kiosk-lg font-bold">Voice Assistant</h1>
          <p className="text-sm text-text-secondary">
            Speak or type your command
          </p>
        </div>
        <button
          onClick={() => {
            if (isSpeaking) {
              stopSpeaking()
            } else {
              setTtsEnabled(!ttsEnabled)
            }
          }}
          className={classNames(
            'p-2 rounded-lg transition-colors',
            ttsEnabled ? 'bg-primary text-white' : 'bg-surface-light text-text-secondary',
            isSpeaking && 'animate-pulse'
          )}
          title={isSpeaking ? 'Stop speaking' : ttsEnabled ? 'TTS enabled' : 'TTS disabled'}
        >
          {ttsEnabled ? (
            <Volume2 className="w-5 h-5" />
          ) : (
            <VolumeX className="w-5 h-5" />
          )}
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-auto space-y-3 mb-4">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <p className="text-text-secondary text-center">
              Tap the microphone to start speaking<br />
              or type a command below
            </p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={classNames(
                'p-3 rounded-xl max-w-[80%]',
                message.type === 'user'
                  ? 'bg-primary ml-auto'
                  : 'bg-surface-light'
              )}
            >
              <p className="text-sm">{message.text}</p>
            </div>
          ))
        )}
      </div>

      {/* Error message */}
      {error && (
        <div className="bg-error/20 text-error px-4 py-2 rounded-lg mb-4 text-sm">
          {error}
        </div>
      )}

      {/* Interim transcript */}
      {interimTranscript && (
        <div className="bg-surface-light/50 px-4 py-2 rounded-lg mb-4 text-sm text-text-secondary italic">
          {interimTranscript}...
        </div>
      )}

      {/* Microphone button */}
      <div className="flex justify-center mb-4">
        <button
          onClick={handleMicClick}
          disabled={state === 'processing' || !isSupported}
          className={classNames(
            'w-20 h-20 rounded-full flex items-center justify-center transition-all duration-300',
            state === 'listening' && 'bg-error animate-pulse',
            state === 'processing' && 'bg-surface-light',
            state === 'idle' && isSupported && 'bg-primary hover:bg-primary-dark active:scale-95',
            !isSupported && 'bg-surface-light opacity-50 cursor-not-allowed'
          )}
        >
          {state === 'listening' ? (
            <MicOff className="w-8 h-8" />
          ) : state === 'processing' ? (
            <Loader2 className="w-8 h-8 animate-spin" />
          ) : (
            <Mic className="w-8 h-8" />
          )}
        </button>
      </div>

      {/* Text input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendTextCommand()}
          placeholder="Type a command..."
          disabled={state !== 'idle'}
          className="flex-1 bg-surface-light rounded-xl px-4 py-3 text-base focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
        />
        <Button
          onClick={sendTextCommand}
          disabled={!inputText.trim() || state !== 'idle'}
        >
          <Send className="w-5 h-5" />
        </Button>
      </div>
    </div>
  )
}
