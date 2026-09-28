"use client";

import React, { useCallback, useEffect, useState, useRef } from 'react';
import { useUser } from '@/context/UserContext';
import { Button } from '@/components/ui/Button';
import { Send, MessageSquare } from 'lucide-react';
import { messagesApi } from '@/lib/api';

type Thread = {
  thread_id: string;
  participant_label: string;
  last_body: string;
  last_sent_at: string;
  other_user_id: string;
  unread_count: number;
};

type ChatMessage = {
  id: string;
  sender_id: string;
  body: string;
  sent_at: string;
  isMine?: boolean;
};

function formatTime(iso?: string) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    const diff = Date.now() - d.getTime();
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return d.toLocaleDateString();
  } catch {
    return '';
  }
}

export default function MessagesPage() {
  const { userId, refreshMessages } = useUser();
  const [threads, setThreads] = useState<Thread[]>([]);
  const [activeThread, setActiveThread] = useState<string | null>(null);
  const [chat, setChat] = useState<ChatMessage[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);

  const pollRef = useRef<NodeJS.Timeout | null>(null);

  const loadThreads = useCallback(async () => {
    try {
      const data = await messagesApi.threads();
      setThreads(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadChatMessages = useCallback(async (threadId: string) => {
    try {
      const rows: ChatMessage[] = await messagesApi.getThread(threadId);
      setChat(
        rows.map((m) => ({
          ...m,
          isMine: String(m.sender_id) === String(userId),
        }))
      );
      refreshMessages();
    } catch {
      setChat([]);
    }
  }, [userId, refreshMessages]);

  const pollActiveThread = useCallback(async () => {
    if (activeThread) {
      await loadChatMessages(activeThread);
    }
    await loadThreads();
  }, [activeThread, loadChatMessages, loadThreads]);

  useEffect(() => {
    loadThreads();
    const handleFocus = () => pollActiveThread();
    window.addEventListener('focus', handleFocus);
    pollRef.current = setInterval(pollActiveThread, 10000);
    return () => {
      window.removeEventListener('focus', handleFocus);
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [loadThreads, pollActiveThread]);

  useEffect(() => {
    if (!activeThread) {
      setChat([]);
      return;
    }
    loadChatMessages(activeThread);
  }, [activeThread, loadChatMessages]);

  const handleSend = useCallback(async () => {
    if (!newMessage.trim() || !activeThread) return;
    setSending(true);
    
    // Optimistic UI update
    const tmpId = Date.now().toString();
    const optimisticMsg: ChatMessage = {
      id: tmpId,
      sender_id: userId || '',
      body: newMessage.trim(),
      sent_at: new Date().toISOString(),
      isMine: true,
    };
    setChat((prev) => [...prev, optimisticMsg]);
    const bodyToSend = newMessage.trim();
    setNewMessage('');

    try {
      await messagesApi.send(activeThread, bodyToSend);
      const rows: ChatMessage[] = await messagesApi.getThread(activeThread);
      setChat(
        rows.map((m) => ({
          ...m,
          isMine: String(m.sender_id) === String(userId),
        }))
      );
      await loadThreads();
    } catch {
      setChat((prev) => prev.filter((m) => m.id !== tmpId));
    } finally {
      setSending(false);
    }
  }, [activeThread, newMessage, userId, loadThreads]);

  if (loading) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center bg-surface-soft text-ink-muted">
        Loading messages…
      </div>
    );
  }

  if (threads.length === 0) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center bg-surface-soft">
        <div className="text-center">
          <MessageSquare className="w-16 h-16 text-ink-muted/40 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-ink mb-2">No messages yet</h2>
          <p className="text-ink-muted">
            When a company contacts you about your application, you will see it here.
          </p>
        </div>
      </div>
    );
  }

  const activeThreadData = threads.find((t) => t.thread_id === activeThread);

  return (
    <div className="h-[calc(100vh-56px)] flex bg-white max-w-6xl mx-auto rounded-xl overflow-hidden shadow-sm border border-border-soft mt-8">
      <div className="w-1/3 border-r border-border-soft bg-surface-soft flex flex-col">
        <div className="p-4 border-b border-border-soft bg-white">
          <h2 className="text-xl font-bold text-ink">Messages</h2>
        </div>
        <div className="flex-1 overflow-y-auto">
          {threads.map((thread) => (
            <div
              key={thread.thread_id}
              className={`p-4 border-b border-border-soft cursor-pointer hover:bg-surface-soft transition-colors ${
                activeThread === thread.thread_id ? 'bg-brand-blue/10' : ''
              }`}
              onClick={() => setActiveThread(thread.thread_id)}
            >
              <div className="flex justify-between items-start mb-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-sm text-ink">{thread.participant_label}</h3>
                  {thread.unread_count > 0 && activeThread !== thread.thread_id && (
                    <span className="bg-primary text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                      {thread.unread_count}
                    </span>
                  )}
                </div>
                <span className="text-xs text-ink-muted whitespace-nowrap">
                  {formatTime(thread.last_sent_at)}
                </span>
              </div>
              <p className="text-sm line-clamp-1 text-ink-muted">{thread.last_body || 'No messages yet'}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="flex-1 flex flex-col bg-white">
        {activeThread === null ? (
          <div className="flex-1 flex items-center justify-center text-ink-muted">
            Select a thread to view your messages.
          </div>
        ) : (
          <>
            <div className="p-4 border-b border-border-soft bg-white flex items-center justify-between shadow-sm z-10">
              <h3 className="font-bold text-ink">{activeThreadData?.participant_label}</h3>
            </div>

            <div className="flex-1 p-6 overflow-y-auto bg-surface-soft flex flex-col gap-6">
              {chat.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex flex-col max-w-[70%] ${
                    msg.isMine ? 'self-end items-end' : 'self-start items-start'
                  }`}
                >
                  <div className="text-xs text-ink-muted mb-1 px-1">{formatTime(msg.sent_at)}</div>
                  <div
                    className={`px-4 py-3 rounded-2xl ${
                      msg.isMine
                        ? 'bg-primary text-white rounded-tr-none'
                        : 'bg-white text-ink border border-border-soft rounded-tl-none shadow-sm'
                    }`}
                  >
                    {msg.body}
                  </div>
                </div>
              ))}
            </div>

            <div className="p-4 border-t border-border-soft bg-white">
              <div className="flex items-center gap-3">
                <input
                  type="text"
                  className="flex-1 border border-border-soft rounded-full px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm bg-surface-soft"
                  placeholder="Type a message..."
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && !sending && handleSend()}
                />
                <Button
                  className="rounded-full w-12 h-12 p-0 flex items-center justify-center shrink-0"
                  onClick={handleSend}
                  disabled={!newMessage.trim() || sending}
                >
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
