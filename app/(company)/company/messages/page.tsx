"use client";

import React, { useCallback, useEffect, useState } from 'react';
import { useUser } from '@/context/UserContext';
import { Button } from '@/components/ui/Button';
import { Send, MessageSquare } from 'lucide-react';
import { messagesApi } from '@/lib/api';

interface Message {
  threadId?: string;
  id: string;
  companyName?: string;
  participant_label?: string;
  lastMessage?: string;
  timestamp: string;
  otherUserId?: string;
}

interface ChatMessageRaw {
  id: string;
  sender_id: string;
  body: string;
  sent_at: string;
}

type Thread = {
  id: string;
  threadId: string;
  candidateName: string;
  lastMessage: string;
  timestamp: string;
  otherUserId?: string;
};

type ChatMessage = {
  id: string;
  senderId: string;
  body: string;
  sentAt: string;
  isMine: boolean;
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

export default function CompanyMessagesPage() {
  const { messages, userId, refreshMessages } = useUser();
  const [threads, setThreads] = useState<Thread[]>([]);
  const [activeThread, setActiveThread] = useState<string | null>(null);
  const [chat, setChat] = useState<ChatMessage[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);

  const loadThreads = useCallback(() => {
    const threadData = (messages || []).map((m: Message) => ({
      id: m.threadId || m.id,
      threadId: m.threadId || m.id,
      candidateName: m.companyName || m.participant_label || 'Candidate',
      lastMessage: m.lastMessage || '',
      timestamp: m.timestamp,
      otherUserId: m.otherUserId,
    }));
    setThreads(threadData);
    setLoading(false);
  }, [messages]);

  useEffect(() => {
    loadThreads();
  }, [loadThreads]);

  const loadChatMessages = useCallback(async (threadId: string) => {
    try {
      const rows: ChatMessageRaw[] = await messagesApi.getThread(threadId);
      setChat(
        rows.map((m) => ({
          id: m.id,
          senderId: m.sender_id,
          body: m.body,
          sentAt: m.sent_at,
          isMine: String(m.sender_id) === String(userId),
        }))
      );
    } catch {
      setChat([]);
    }
  }, [userId]);

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
    const active = threads.find((t) => t.threadId === activeThread);
    try {
      await messagesApi.send(activeThread, newMessage.trim(), active?.otherUserId);
      setNewMessage('');
      const rows: ChatMessageRaw[] = await messagesApi.getThread(activeThread);
      setChat(
        rows.map((m) => ({
          id: m.id,
          senderId: m.sender_id,
          body: m.body,
          sentAt: m.sent_at,
          isMine: String(m.sender_id) === String(userId),
        }))
      );
      await refreshMessages();
    } catch {
      alert('Failed to send message');
    } finally {
      setSending(false);
    }
  }, [activeThread, newMessage, refreshMessages, threads, userId]);

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
            Invite candidates to chat or respond to applications to start messaging.
          </p>
        </div>
      </div>
    );
  }

  const activeThreadData = threads.find((t) => t.threadId === activeThread);

  return (
    <div className="h-[calc(100vh-56px)] flex bg-white">
      <div className="w-1/3 border-r border-border-soft bg-surface-soft flex flex-col">
        <div className="p-4 border-b border-border-soft bg-white">
          <h2 className="text-xl font-bold text-ink">Candidate Messages</h2>
        </div>
        <div className="flex-1 overflow-y-auto">
          {threads.map((thread) => (
            <div
              key={thread.threadId}
              className={`p-4 border-b border-border-soft cursor-pointer hover:bg-surface-soft transition-colors ${
                activeThread === thread.threadId ? 'bg-brand-blue/10' : ''
              }`}
              onClick={() => setActiveThread(thread.threadId)}
            >
              <div className="flex justify-between items-start mb-1">
                <h3 className="font-bold text-sm text-ink">{thread.candidateName}</h3>
                <span className="text-xs text-ink-muted whitespace-nowrap">
                  {formatTime(thread.timestamp)}
                </span>
              </div>
              <p className="text-sm line-clamp-1 text-ink-muted">{thread.lastMessage}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="flex-1 flex flex-col bg-white">
        {activeThread === null ? (
          <div className="flex-1 flex items-center justify-center text-ink-muted">
            Select a candidate thread to start messaging.
          </div>
        ) : (
          <>
            <div className="p-4 border-b border-border-soft bg-white flex items-center justify-between shadow-sm z-10">
              <h3 className="font-bold text-ink">{activeThreadData?.candidateName}</h3>
            </div>

            <div className="flex-1 p-6 overflow-y-auto bg-surface-soft flex flex-col gap-6">
              {chat.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex flex-col max-w-[70%] ${
                    msg.isMine ? 'self-end items-end' : 'self-start items-start'
                  }`}
                >
                  <div className="text-xs text-ink-muted mb-1 px-1">{formatTime(msg.sentAt)}</div>
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
