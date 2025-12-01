import { useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Loader2 } from 'lucide-react'
import { ConversationMessage } from '../../../stores/voiceStore'
import { classNames } from '../../../utils/formatters'

interface ChatSectionProps {
  messages: ConversationMessage[]
}

export default function ChatSection({ messages }: ChatSectionProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex-1 flex flex-col justify-end">
      <div className="space-y-3">
          <AnimatePresence initial={false}>
            {messages.map((message) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -20, scale: 0.95 }}
                transition={{
                  type: "spring",
                  stiffness: 400,
                  damping: 25,
                  duration: 0.2
                }}
                className={classNames(
                  'max-w-[85%] p-4 rounded-2xl backdrop-blur-sm transition-all',
                  message.type === 'user'
                    ? 'ml-auto bg-primary/10 border border-primary/20 rounded-br-sm shadow-sm'
                    : 'mr-auto bg-white/5 border border-white/10 rounded-bl-sm shadow-sm'
                )}
              >
                <p className="text-sm text-text-secondary mb-1 opacity-70">
                  {message.type === 'user' ? 'You' : 'Assistant'}
                  {message.sttEngine && (
                    <span className="ml-2 text-xs opacity-60">({message.sttEngine})</span>
                  )}
                </p>
                <p className="text-lg whitespace-pre-wrap break-words leading-relaxed">
                  {message.text}
                  {/* Blinking cursor for streaming messages */}
                  {message.isStreaming && (
                    <span className="inline-block w-[3px] h-5 ml-1 bg-primary animate-pulse align-middle" />
                  )}
                </p>
                {/* Streaming indicator */}
                {message.isStreaming && (
                  <div className="flex items-center gap-2 mt-2 text-xs text-text-secondary opacity-70">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    <span>Streaming...</span>
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
          <div ref={messagesEndRef} />
        </div>
    </div>
  )
}
