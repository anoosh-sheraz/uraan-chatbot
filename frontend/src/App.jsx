import { useState, useEffect, useRef, useCallback } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import WelcomeScreen from './components/WelcomeScreen';
import MessageBubble from './components/MessageBubble';
import TypingIndicator from './components/TypingIndicator';
import InputBar from './components/InputBar';
import { sendMessage, fetchHealth, clearSession } from './api/chat';
import './App.css';

// ── LocalStorage helpers ──────────────────────────────────────────────────────

function loadSessions() {
  try { return JSON.parse(localStorage.getItem('uraan_sessions') || '[]'); }
  catch { return []; }
}

function saveSessions(list) {
  localStorage.setItem('uraan_sessions', JSON.stringify(list));
}

function loadMessages(sid) {
  try { return JSON.parse(localStorage.getItem(`uraan_msgs_${sid}`) || '[]'); }
  catch { return []; }
}

function saveMessages(sid, msgs) {
  localStorage.setItem(`uraan_msgs_${sid}`, JSON.stringify(msgs.slice(-60)));
}

function genId() {
  return 'session-' + Math.random().toString(36).slice(2, 10);
}

function nowSession(id) {
  return { id, title: 'New Chat', createdAt: Date.now(), updatedAt: Date.now() };
}

function ts() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  const initSessions = loadSessions();
  const initId       = initSessions.length ? initSessions[0].id : genId();

  const [sessions, setSessions]           = useState(initSessions);
  const [sessionId, setSessionId]         = useState(initId);
  const [messages, setMessages]           = useState(() => loadMessages(initId));
  const [typing, setTyping]               = useState(false);
  const [backendOnline, setBackendOnline] = useState(null);
  const [sidebarOpen, setSidebarOpen]     = useState(true);
  const [mode, setMode]                   = useState('empathetic');

  const bottomRef   = useRef(null);
  const titleSetRef = useRef(false);

  useEffect(() => {
    const list = loadSessions();
    if (!list.find(s => s.id === initId)) {
      const updated = [nowSession(initId), ...list];
      setSessions(updated);
      saveSessions(updated);
    }
    titleSetRef.current = loadMessages(initId).length > 0;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    fetchHealth()
      .then(d => setBackendOnline(d.status === 'healthy'))
      .catch(() => setBackendOnline(false));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, typing]);

  useEffect(() => {
    if (messages.length > 0) saveMessages(sessionId, messages);
  }, [messages, sessionId]);

  // ── Session ops ───────────────────────────────────────────────────────────

  const setTitle = useCallback((id, text) => {
    setSessions(prev => {
      const updated = prev.map(s =>
        s.id === id
          ? { ...s, title: text.slice(0, 40) + (text.length > 40 ? '…' : ''), updatedAt: Date.now() }
          : s
      );
      saveSessions(updated);
      return updated;
    });
  }, []);

  const handleNewChat = useCallback(() => {
    const id = genId();
    setSessions(prev => {
      const updated = [nowSession(id), ...prev];
      saveSessions(updated);
      return updated;
    });
    setSessionId(id);
    setMessages([]);
    titleSetRef.current = false;
  }, []);

  const handleSelectSession = useCallback((id) => {
    if (id === sessionId) return;
    setSessionId(id);
    setMessages(loadMessages(id));
    titleSetRef.current = loadMessages(id).length > 0;
  }, [sessionId]);

  const handleDeleteSession = useCallback((id) => {
    setSessions(prev => {
      const updated = prev.filter(s => s.id !== id);
      saveSessions(updated);
      if (id === sessionId) {
        if (updated.length) {
          setSessionId(updated[0].id);
          setMessages(loadMessages(updated[0].id));
          titleSetRef.current = loadMessages(updated[0].id).length > 0;
        } else {
          const newId = genId();
          const fresh = [nowSession(newId)];
          saveSessions(fresh);
          setSessionId(newId);
          setMessages([]);
          titleSetRef.current = false;
          return fresh;
        }
      }
      return updated;
    });
    localStorage.removeItem(`uraan_msgs_${id}`);
    clearSession(id).catch(() => {});
  }, [sessionId]);

  const handleClear = useCallback(async () => {
    await clearSession(sessionId).catch(() => {});
    localStorage.removeItem(`uraan_msgs_${sessionId}`);
    setMessages([]);
    setTitle(sessionId, 'New Chat');
    titleSetRef.current = false;
  }, [sessionId, setTitle]);

  // ── Chat ──────────────────────────────────────────────────────────────────

  const handleSend = useCallback(async (text) => {
    setMessages(prev => [...prev, { role: 'user', content: text, time: ts() }]);
    setTyping(true);

    if (!titleSetRef.current) {
      titleSetRef.current = true;
      setTitle(sessionId, text);
    }

    let botIndex = null;

    await sendMessage(text, sessionId, mode, {
      onMeta: (meta) => {
        setTyping(false);
        setMessages(prev => {
          const next = [...prev, { role: 'bot', content: '', meta, time: ts() }];
          botIndex = next.length - 1;
          return next;
        });
      },
      onChunk: (chunk) => {
        setMessages(prev => {
          if (botIndex === null) {
            botIndex = prev.length;
            return [...prev, { role: 'bot', content: chunk, time: ts() }];
          }
          const copy = [...prev];
          copy[botIndex] = { ...copy[botIndex], content: copy[botIndex].content + chunk };
          return copy;
        });
      },
      onDone:   () => setTyping(false),
      onCrisis: (data) => {
        setTyping(false);
        setMessages(prev => [...prev, { role: 'crisis', content: data.response, time: ts() }]);
      },
      onError: (msg) => {
        setTyping(false);
        setMessages(prev => [...prev, { role: 'bot', content: `Error: ${msg}`, time: ts() }]);
      },
    });
  }, [sessionId, mode, setTitle]);

  return (
    <div style={styles.app}>
      <Header
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen(o => !o)}
        backendOnline={backendOnline}
        messageCount={messages.length}
        onClear={handleClear}
        mode={mode}
        onModeChange={setMode}
      />

      <div style={styles.body}>
        <Sidebar
          open={sidebarOpen}
          sessions={sessions}
          activeId={sessionId}
          onNew={handleNewChat}
          onSelect={handleSelectSession}
          onDelete={handleDeleteSession}
        />

        <main style={styles.main}>
          {messages.length === 0
            ? <WelcomeScreen mode={mode} />
            : (
              <div style={styles.feed}>
                {messages.map((msg, i) => <MessageBubble key={i} msg={msg} />)}
                {typing && <TypingIndicator />}
                <div ref={bottomRef} />
              </div>
            )
          }
          <InputBar onSend={handleSend} disabled={typing} />
        </main>
      </div>
    </div>
  );
}

const styles = {
  app: {
    display:       'flex',
    flexDirection: 'column',
    height:        '100vh',
    background:    '#F8F5FF',
    overflow:      'hidden',
  },
  body: {
    flex:     1,
    display:  'flex',
    overflow: 'hidden',
  },
  main: {
    flex:          1,
    display:       'flex',
    flexDirection: 'column',
    overflow:      'hidden',
  },
  feed: {
    flex:       1,
    overflowY:  'auto',
    padding:    '24px 20px',
    maxWidth:   780,
    width:      '100%',
    margin:     '0 auto',
    boxSizing:  'border-box',
  },
};
