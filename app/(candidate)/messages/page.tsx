"use client";

import React, { useState } from 'react';
import { useUser } from '@/context/UserContext';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Send, MessageSquare } from 'lucide-react';
import { Input } from '@/components/ui/FormField';

export default function CandidateMessagesPage() {
  const { messages, addMessage } = useUser();
  const [activeThread, setActiveThread] = useState<number | null>(null);
  const [newMessage, setNewMessage] = useState('');

  // Mock threads for candidate
  const mockThreads = [
    {
      id: 1,
      companyName: 'TechCorp Inc.',
      jobTitle: 'Senior Frontend Engineer',
      lastMessage: 'Hi there! We reviewed your profile and...',
      timestamp: '2 hours ago',
      unread: true,
      history: [
        { sender: 'TechCorp Inc.', text: 'Hi there! We reviewed your profile and were very impressed with your AI fitment score. Are you open for a quick chat next week?', timestamp: '2 hours ago' }
      ]
    },
    {
      id: 2,
      companyName: 'Startup LLC',
      jobTitle: 'Backend Developer',
      lastMessage: 'Thanks for applying.',
      timestamp: '1 day ago',
      unread: false,
      history: [
        { sender: 'Startup LLC', text: 'Thanks for applying. We are currently reviewing applications.', timestamp: '1 day ago' }
      ]
    }
  ];

  const threads = messages.length > 0 ? [] : mockThreads; // Switch to real global state if implemented fully

  const handleSend = () => {
    if (!newMessage.trim() || activeThread === null) return;
    
    // In a real app we'd push to the global state
    // For now we just mock appending to the UI locally
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
      <div className="min-h-[80vh] flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <MessageSquare className="w-16 h-16 text-slate-300 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-slate-900 mb-2">No messages yet</h2>
          <p className="text-slate-500">Apply to jobs to start conversations with employers.</p>
        </div>
      </div>
    );
  }

  const activeThreadData = threads.find(t => t.id === activeThread);

  return (
    <div className="h-[calc(100vh-64px)] flex bg-white">
      {/* Sidebar: Threads List */}
      <div className="w-1/3 border-r border-slate-200 bg-slate-50 flex flex-col">
        <div className="p-4 border-b border-slate-200 bg-white">
          <h2 className="text-xl font-bold text-slate-900">Messages</h2>
        </div>
        <div className="flex-1 overflow-y-auto">
          {threads.map(thread => (
            <div 
              key={thread.id} 
              className={`p-4 border-b border-slate-100 cursor-pointer hover:bg-slate-100 transition-colors ${activeThread === thread.id ? 'bg-blue-50/50' : ''}`}
              onClick={() => setActiveThread(thread.id)}
            >
              <div className="flex justify-between items-start mb-1">
                <h3 className={`font-bold text-sm ${thread.unread ? 'text-slate-900' : 'text-slate-700'}`}>
                  {thread.companyName}
                </h3>
                <span className="text-xs text-slate-400 whitespace-nowrap">{thread.timestamp}</span>
              </div>
              <p className="text-xs text-slate-500 mb-2 font-medium">{thread.jobTitle}</p>
              <p className={`text-sm line-clamp-1 ${thread.unread ? 'text-slate-800 font-medium' : 'text-slate-500'}`}>
                {thread.lastMessage}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-white">
        {activeThread === null ? (
          <div className="flex-1 flex items-center justify-center text-slate-400">
            Select a conversation to start messaging.
          </div>
        ) : (
          <>
            {/* Chat Header */}
            <div className="p-4 border-b border-slate-200 bg-white flex items-center justify-between shadow-sm z-10">
              <div>
                <h3 className="font-bold text-slate-900">{activeThreadData?.companyName}</h3>
                <p className="text-sm text-slate-500">Regarding: {activeThreadData?.jobTitle}</p>
              </div>
            </div>

            {/* Chat History */}
            <div className="flex-1 p-6 overflow-y-auto bg-slate-50 flex flex-col gap-6">
              {activeThreadData?.history.map((msg, i) => (
                <div key={i} className={`flex flex-col max-w-[70%] ${msg.sender === 'You' ? 'self-end items-end' : 'self-start items-start'}`}>
                  <div className="text-xs text-slate-400 mb-1 px-1">{msg.sender} • {msg.timestamp}</div>
                  <div className={`px-4 py-3 rounded-2xl ${msg.sender === 'You' ? 'bg-primary text-white rounded-tr-none' : 'bg-white text-slate-800 border border-slate-200 rounded-tl-none shadow-sm'}`}>
                    {msg.text}
                  </div>
                </div>
              ))}
            </div>

            {/* Message Input */}
            <div className="p-4 border-t border-slate-200 bg-white">
              <div className="flex items-center gap-3">
                <input 
                  type="text" 
                  className="flex-1 border border-slate-200 rounded-full px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm bg-slate-50"
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
