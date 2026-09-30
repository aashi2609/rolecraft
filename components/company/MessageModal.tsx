"use client";

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/Button';
import { X, Send, Loader2 } from 'lucide-react';
import { messagesApi } from '@/lib/api';

interface MessageModalProps {
  candidateId?: string;
  candidateName: string;
  isOpen: boolean;
  onClose: () => void;
}

export function MessageModal({ candidateId, candidateName, isOpen, onClose }: MessageModalProps) {
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<{sender: string, text: string}[]>([]);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(null);

  if (!isOpen) return null;

  // If there's a way to find existing threads for this candidate, we could do that here
  // For now we'll just start a new thread if we don't have one

  const handleSend = async () => {
    if (!message.trim() || !candidateId) return;
    setSending(true);
    try {
      if (!threadId) {
        const msg = await messagesApi.start(message.trim(), candidateId);
        setThreadId(msg.conversation_id || msg.thread_id);
        setMessages([...messages, { sender: 'You', text: message }]);
      } else {
        await messagesApi.send(threadId, message.trim(), candidateId);
        setMessages([...messages, { sender: 'You', text: message }]);
      }
      setMessage('');
    } catch (e) {
      console.error('Failed to send message:', e);
      alert('Failed to send message');
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-ink/50 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg overflow-hidden flex flex-col h-[500px]">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-border-soft flex justify-between items-center bg-surface-soft">
          <div>
            <h3 className="font-bold text-ink">Message {candidateName}</h3>
            <p className="text-xs text-ink-muted">Typically replies within 24 hours</p>
          </div>
          <button onClick={onClose} className="p-2 text-ink-muted hover:text-ink-muted rounded-full hover:bg-border-soft">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Chat Area */}
        <div className="flex-1 p-6 overflow-y-auto bg-white flex flex-col gap-4">
          {messages.length === 0 ? (
            <div className="flex-1 flex items-center justify-center text-ink-muted text-sm text-center">
              Send a message to start the conversation with {candidateName}.
            </div>
          ) : (
            messages.map((msg, i) => (
              <div key={i} className={`flex flex-col max-w-[80%] ${msg.sender === 'You' ? 'self-end items-end' : 'self-start items-start'}`}>
                <div className="text-xs text-ink-muted mb-1 px-1">{msg.sender}</div>
                <div className={`px-4 py-2 rounded-2xl ${msg.sender === 'You' ? 'bg-primary text-white rounded-tr-none' : 'bg-surface-soft text-ink rounded-tl-none'}`}>
                  {msg.text}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-border-soft bg-surface-soft flex gap-2">
          <input 
            type="text" 
            className="flex-1 border border-border-soft rounded-full px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary text-sm"
            placeholder="Type your message..."
            value={message}
            onChange={e => setMessage(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
            disabled={sending || !candidateId}
          />
          <Button className="rounded-full px-4" onClick={handleSend} disabled={!message.trim() || sending || !candidateId}>
            {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </Button>
        </div>
      </div>
    </div>
  );
}
