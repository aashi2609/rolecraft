"use client";

import React, { useState } from 'react';
import { useUser } from '@/context/UserContext';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Send, MessageSquare } from 'lucide-react';
import { Input } from '@/components/ui/FormField';

export default function CompanyMessagesPage() {
  const { messages, addMessage } = useUser();
  const [activeThread, setActiveThread] = useState<number | null>(null);
  const [newMessage, setNewMessage] = useState('');

  // Mock threads for company/employer
  const mockThreads = [
    {
      id: 1,
      candidateName: 'Sneha Kapoor',
      jobTitle: 'Product Designer',
      lastMessage: 'Sure, I would be happy to chat next week!',
      timestamp: '2 hours ago',
      unread: true,
      history: [
        { sender: 'You', text: 'Hi Sneha! We reviewed your profile and were very impressed with your AI fitment score. Are you open for a quick chat next week?', timestamp: '3 hours ago' },
        { sender: 'Sneha Kapoor', text: 'Sure, I would be happy to chat next week! Let me know what days work for you.', timestamp: '2 hours ago' }
      ]
    },
    {
      id: 2,
      candidateName: 'Ananya Reddy',
      jobTitle: 'Senior UX Designer',
      lastMessage: 'Thank you for the opportunity.',
      timestamp: '1 day ago',
      unread: false,
      history: [
        { sender: 'You', text: 'Hi Ananya, thanks for applying. We are currently reviewing applications and will get back to you soon.', timestamp: '1 day ago' },
        { sender: 'Ananya Reddy', text: 'Thank you for the opportunity. Looking forward to hearing back.', timestamp: '1 day ago' }
      ]
    }
  ];

  const threads = messages.length > 0 ? [] : mockThreads;

  const handleSend = () => {
    if (!newMessage.trim() || activeThread === null) return;
    
    const thread = threads.find(t => t.id === activeThread);
    if (thread) {
      thread.history.push({
        sender: 'You',
        text: newMessage,
        timestamp: 'Just now'
      });
    }
    setNewMessage('');
  };

  if (threads.length === 0) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center bg-surface-soft">
        <div className="text-center">
          <MessageSquare className="w-16 h-16 text-ink-muted/40 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-ink mb-2">No messages yet</h2>
          <p className="text-ink-muted">Invite candidates to chat or respond to applications to start messaging.</p>
        </div>
      </div>
    );
  }

  const activeThreadData = threads.find(t => t.id === activeThread);

  return (
    <div className="h-[calc(100vh-56px)] flex bg-white">
      {/* Sidebar: Threads List */}
      <div className="w-1/3 border-r border-border-soft bg-surface-soft flex flex-col">
        <div className="p-4 border-b border-border-soft bg-white">
          <h2 className="text-xl font-bold text-ink">Candidate Messages</h2>
        </div>
        <div className="flex-1 overflow-y-auto">
          {threads.map(thread => (
            <div 
              key={thread.id} 
              className={`p-4 border-b border-border-soft cursor-pointer hover:bg-surface-soft transition-colors ${activeThread === thread.id ? 'bg-brand-blue/10' : ''}`}
              onClick={() => setActiveThread(thread.id)}
            >
              <div className="flex justify-between items-start mb-1">
                <h3 className="font-bold text-sm text-ink">
                  {thread.candidateName}
                </h3>
                <span className="text-xs text-ink-muted whitespace-nowrap">{thread.timestamp}</span>
              </div>
              <p className="text-xs text-ink-muted mb-2 font-medium">{thread.jobTitle}</p>
              <p className={`text-sm line-clamp-1 ${thread.unread ? 'text-ink font-medium' : 'text-ink-muted'}`}>
                {thread.lastMessage}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-white">
        {activeThread === null ? (
          <div className="flex-1 flex items-center justify-center text-ink-muted">
            Select a candidate thread to start messaging.
          </div>
        ) : (
          <>
            {/* Chat Header */}
            <div className="p-4 border-b border-border-soft bg-white flex items-center justify-between shadow-sm z-10">
              <div>
                <h3 className="font-bold text-ink">{activeThreadData?.candidateName}</h3>
                <p className="text-sm text-ink-muted">Regarding: {activeThreadData?.jobTitle}</p>
              </div>
            </div>

            {/* Chat History */}
            <div className="flex-1 p-6 overflow-y-auto bg-surface-soft flex flex-col gap-6">
              {activeThreadData?.history.map((msg, i) => (
                <div key={i} className={`flex flex-col max-w-[70%] ${msg.sender === 'You' ? 'self-end items-end' : 'self-start items-start'}`}>
                  <div className="text-xs text-ink-muted mb-1 px-1">{msg.sender} • {msg.timestamp}</div>
                  <div className={`px-4 py-3 rounded-2xl ${msg.sender === 'You' ? 'bg-primary text-white rounded-tr-none' : 'bg-white text-ink border border-border-soft rounded-tl-none shadow-sm'}`}>
                    {msg.text}
                  </div>
                </div>
              ))}
            </div>

            {/* Message Input */}
            <div className="p-4 border-t border-border-soft bg-white">
              <div className="flex items-center gap-3">
                <input 
                  type="text" 
                  className="flex-1 border border-border-soft rounded-full px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm bg-surface-soft"
                  placeholder="Type a message..."
                  value={newMessage}
                  onChange={e => setNewMessage(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleSend()}
                />
                <Button className="rounded-full w-12 h-12 p-0 flex items-center justify-center shrink-0" onClick={handleSend} disabled={!newMessage.trim()}>
                  <Send className="w-5 h-5" />
                </Button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
