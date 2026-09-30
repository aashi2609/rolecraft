"use client";

import React, { useCallback, useEffect, useState, useRef } from 'react';
import { useUser } from '@/context/UserContext';
import { Button } from '@/components/ui/Button';
import { Send, MessageSquare, Search } from 'lucide-react';
import { messagesApi } from '@/lib/api';

type Thread = {
  thread_id: string;
  participant_label: string;
  last_body: string;
  last_sent_at: string;
  other_user_id: string;
  unread_count: number;
  avatar_url?: string | null;
  job_title?: string | null;
  subtitle?: string | null;
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

function formatMessageTime(iso?: string) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

function formatDateDivider(iso: string) {
  const d = new Date(iso);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  if (d.toDateString() === today.toDateString()) return 'Today';
  if (d.toDateString() === yesterday.toDateString()) return 'Yesterday';
  return d.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' });
}

function getInitials(name?: string | null) {
  if (!name) return '?';
  return name.split(' ').map(w => w[0]).filter(Boolean).slice(0, 2).join('').toUpperCase();
}

function Avatar({ url, name, size = 40 }: { url?: string | null; name?: string | null; size?: number }) {
  if (url) {
    return (
      <img
        src={url}
        alt={name || 'Avatar'}
        className="rounded-full object-cover shrink-0"
        style={{ width: size, height: size }}
      />
    );
  }
  return (
    <div
      className="rounded-full bg-blue-100 text-blue-600 font-bold flex items-center justify-center shrink-0 select-none"
      style={{ width: size, height: size, fontSize: size * 0.38 }}
    >
      {getInitials(name)}
    </div>
  );
}

export default function CompanyMessagesPage() {
  const { userId, refreshMessages } = useUser();
  const [threads, setThreads] = useState<Thread[]>([]);
  const [activeThread, setActiveThread] = useState<string | null>(null);
  const [chat, setChat] = useState<ChatMessage[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [mobileShowChat, setMobileShowChat] = useState(false);

  const pollRef = useRef<NodeJS.Timeout | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);
  }, []);

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
      scrollToBottom();
    } catch {
      setChat([]);
    }
  }, [userId, refreshMessages, scrollToBottom]);

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
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
    scrollToBottom();

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
      scrollToBottom();
    } catch {
      setChat((prev) => prev.filter((m) => m.id !== tmpId));
    } finally {
      setSending(false);
    }
  }, [activeThread, newMessage, userId, loadThreads, scrollToBottom]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!sending) handleSend();
    }
  };

  const handleTextareaInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setNewMessage(e.target.value);
    const ta = e.target;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
  };

  const selectThread = (threadId: string) => {
    setActiveThread(threadId);
    setMobileShowChat(true);
  };

  const filteredThreads = searchQuery
    ? threads.filter(t => t.participant_label?.toLowerCase().includes(searchQuery.toLowerCase()))
    : threads;

  if (loading) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center bg-surface-soft text-ink-muted">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <span>Loading messages…</span>
        </div>
      </div>
    );
  }

  if (threads.length === 0) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center bg-surface-soft">
        <div className="text-center">
          <MessageSquare className="w-16 h-16 text-ink-muted/30 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-ink mb-2">No messages yet</h2>
          <p className="text-ink-muted max-w-sm mx-auto">
            Invite candidates to chat or respond to applications to start messaging.
          </p>
        </div>
      </div>
    );
  }

  const activeThreadData = threads.find((t) => t.thread_id === activeThread);

  // Check if sender changes between messages for grouping
  const shouldShowDateDivider = (idx: number) => {
    if (idx === 0) return true;
    const prevDate = new Date(chat[idx - 1].sent_at).toDateString();
    const currDate = new Date(chat[idx].sent_at).toDateString();
    return prevDate !== currDate;
  };

  const isLastInGroup = (idx: number) => {
    if (idx === chat.length - 1) return true;
    return chat[idx].sender_id !== chat[idx + 1].sender_id;
  };

  const senderChanges = (idx: number) => {
    if (idx === 0) return true;
    return chat[idx - 1].sender_id !== chat[idx].sender_id;
  };

  return (
    <div className="h-[calc(100vh-56px)] flex bg-white max-w-6xl mx-auto rounded-xl overflow-hidden shadow-lg border border-border-soft mt-4 md:mt-8">
      {/* Thread List */}
      <div className={`w-full md:w-[340px] lg:w-[380px] border-r border-border-soft bg-white flex flex-col shrink-0 ${mobileShowChat ? 'hidden md:flex' : 'flex'}`}>
        <div className="p-4 border-b border-border-soft">
          <h2 className="text-lg font-bold text-ink mb-3">Candidate Messages</h2>
          {threads.length > 5 && (
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-muted/60" />
              <input
                type="text"
                placeholder="Search conversations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-border-soft bg-surface-soft focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400"
              />
            </div>
          )}
        </div>
        <div className="flex-1 overflow-y-auto">
          {filteredThreads.map((thread) => {
            const isActive = activeThread === thread.thread_id;
            const isUnread = thread.unread_count > 0 && !isActive;
            return (
              <div
                key={thread.thread_id}
                className={`flex items-start gap-3 px-4 py-3 cursor-pointer transition-all border-b border-border-soft/50 ${
                  isActive
                    ? 'bg-blue-50 border-l-2 border-l-blue-500'
                    : isUnread
                    ? 'bg-blue-50/40 hover:bg-blue-50/60'
                    : 'hover:bg-surface-soft'
                }`}
                onClick={() => selectThread(thread.thread_id)}
              >
                <Avatar url={thread.avatar_url} name={thread.participant_label} size={44} />
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-baseline">
                    <h3 className={`text-sm truncate ${isUnread ? 'font-bold text-ink' : 'font-semibold text-ink'}`}>
                      {thread.participant_label}
                    </h3>
                    <span className="text-[11px] text-ink-muted whitespace-nowrap ml-2 shrink-0">
                      {formatTime(thread.last_sent_at)}
                    </span>
                  </div>
                  {thread.job_title && (
                    <p className="text-[11px] text-blue-600/80 truncate">Re: {thread.job_title}</p>
                  )}
                  <div className="flex justify-between items-center mt-0.5">
                    <p className={`text-[13px] truncate ${isUnread ? 'text-ink font-medium' : 'text-ink-muted'}`}>
                      {thread.last_body || 'No messages yet'}
                    </p>
                    {isUnread && (
                      <span className="bg-blue-500 text-white text-[10px] font-bold w-5 h-5 rounded-full flex items-center justify-center ml-2 shrink-0">
                        {thread.unread_count}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Conversation Panel */}
      <div className={`flex-1 flex flex-col bg-white min-w-0 ${!mobileShowChat && activeThread === null ? 'hidden md:flex' : mobileShowChat ? 'flex' : 'hidden md:flex'}`}>
        {activeThread === null ? (
          <div className="flex-1 flex flex-col items-center justify-center text-ink-muted gap-3 p-8">
            <MessageSquare className="w-12 h-12 text-ink-muted/25" />
            <p className="text-center">Select a candidate thread to start messaging</p>
          </div>
        ) : (
          <>
            {/* Header */}
            <div className="px-4 py-3 border-b border-border-soft bg-white flex items-center gap-3 shadow-sm z-10">
              <button
                className="md:hidden p-1 -ml-1 text-ink-muted hover:text-ink"
                onClick={() => { setMobileShowChat(false); }}
              >
                ← 
              </button>
              <Avatar url={activeThreadData?.avatar_url} name={activeThreadData?.participant_label} size={36} />
              <div className="min-w-0">
                <h3 className="font-bold text-ink text-sm truncate">{activeThreadData?.participant_label}</h3>
                {activeThreadData?.job_title && (
                  <p className="text-xs text-ink-muted truncate">Re: {activeThreadData.job_title}</p>
                )}
                {!activeThreadData?.job_title && activeThreadData?.subtitle && (
                  <p className="text-xs text-ink-muted truncate">{activeThreadData.subtitle}</p>
                )}
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 px-4 py-4 overflow-y-auto bg-gradient-to-b from-slate-50 to-white flex flex-col">
              {chat.map((msg, idx) => (
                <React.Fragment key={msg.id}>
                  {shouldShowDateDivider(idx) && (
                    <div className="flex items-center justify-center my-4">
                      <span className="text-[11px] text-ink-muted bg-white px-3 py-1 rounded-full border border-border-soft shadow-sm">
                        {formatDateDivider(msg.sent_at)}
                      </span>
                    </div>
                  )}
                  <div
                    className={`flex items-end gap-2 ${msg.isMine ? 'justify-end' : 'justify-start'} ${
                      senderChanges(idx) && idx > 0 ? 'mt-4' : 'mt-1'
                    }`}
                  >
                    {/* Avatar for received messages only, last in group */}
                    {!msg.isMine && (
                      <div className="w-7 shrink-0">
                        {isLastInGroup(idx) && (
                          <Avatar url={activeThreadData?.avatar_url} name={activeThreadData?.participant_label} size={28} />
                        )}
                      </div>
                    )}
                    <div className={`flex flex-col ${msg.isMine ? 'items-end' : 'items-start'} max-w-[65%]`}>
                      <div
                        className={`px-3.5 py-2.5 text-sm leading-relaxed ${
                          msg.isMine
                            ? 'bg-blue-500 text-white rounded-2xl rounded-br-sm'
                            : 'bg-white text-ink border border-border-soft rounded-2xl rounded-bl-sm shadow-sm'
                        }`}
                      >
                        {msg.body}
                      </div>
                      {isLastInGroup(idx) && (
                        <span className={`text-[10px] text-ink-muted/70 mt-1 px-1 ${msg.isMine ? 'text-right' : ''}`}>
                          {formatMessageTime(msg.sent_at)}
                        </span>
                      )}
                    </div>
                  </div>
                </React.Fragment>
              ))}
              <div ref={chatEndRef} />
            </div>

            {/* Input */}
            <div className="px-4 py-3 border-t border-border-soft bg-white shadow-[0_-1px_3px_rgba(0,0,0,0.04)]">
              <div className="flex items-end gap-2">
                <textarea
                  ref={textareaRef}
                  className="flex-1 border border-border-soft rounded-2xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 text-sm bg-surface-soft resize-none overflow-hidden"
                  placeholder="Type a message..."
                  rows={1}
                  value={newMessage}
                  onChange={handleTextareaInput}
                  onKeyDown={handleKeyDown}
                  style={{ minHeight: 42, maxHeight: 120 }}
                />
                <Button
                  className={`rounded-full w-10 h-10 p-0 flex items-center justify-center shrink-0 transition-all ${
                    newMessage.trim()
                      ? 'bg-blue-500 hover:bg-blue-600 text-white shadow-md'
                      : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  }`}
                  onClick={handleSend}
                  disabled={!newMessage.trim() || sending}
                >
                  <Send className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
