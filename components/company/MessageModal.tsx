"use client";

import React, { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { X, Send } from 'lucide-react';

interface MessageModalProps {
  candidateName: string;
  isOpen: boolean;
  onClose: () => void;
}

export function MessageModal({ candidateName, isOpen, onClose }: MessageModalProps) {
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<{sender: string, text: string}[]>([]);

  if (!isOpen) return null;

  const handleSend = () => {
    if (!message.trim()) return;
    setMessages([...messages, { sender: 'You', text: message }]);
    setMessage('');
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg overflow-hidden flex flex-col h-[500px]">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
          <div>
            <h3 className="font-bold text-slate-900">Message {candidateName}</h3>
            <p className="text-xs text-slate-500">Typically replies within 24 hours</p>
          </div>
          <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-200">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Chat Area */}
        <div className="flex-1 p-6 overflow-y-auto bg-white flex flex-col gap-4">
          {messages.length === 0 ? (
            <div className="flex-1 flex items-center justify-center text-slate-400 text-sm text-center">
              Send a message to start the conversation with {candidateName}.
            </div>
          ) : (
            messages.map((msg, i) => (
              <div key={i} className={`flex flex-col max-w-[80%] ${msg.sender === 'You' ? 'self-end items-end' : 'self-start items-start'}`}>
                <div className="text-xs text-slate-400 mb-1 px-1">{msg.sender}</div>
                <div className={`px-4 py-2 rounded-2xl ${msg.sender === 'You' ? 'bg-primary text-white rounded-tr-none' : 'bg-slate-100 text-slate-800 rounded-tl-none'}`}>
                  {msg.text}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-slate-100 bg-slate-50 flex gap-2">
          <input 
            type="text" 
            className="flex-1 border border-slate-200 rounded-full px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary text-sm"
            placeholder="Type your message..."
            value={message}
            onChange={e => setMessage(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
          />
          <Button className="rounded-full px-4" onClick={handleSend} disabled={!message.trim()}>
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
