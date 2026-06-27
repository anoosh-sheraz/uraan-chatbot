/**
 * Sends a message to URAAN Safe Voice and handles both:
 * - JSON response (crisis detection)
 * - SSE stream (normal response)
 *
 * @param {string} message
 * @param {string} sessionId
 * @param {{ onMeta, onChunk, onDone, onCrisis, onError }} callbacks
 */
export async function sendMessage(message, sessionId, mode, { onMeta, onChunk, onDone, onCrisis, onError }) {
  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: sessionId, mode: mode || 'empathetic' }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Unknown server error' }));
      onError(err.detail || 'Server error');
      return;
    }

    const contentType = res.headers.get('content-type') || '';

    // Crisis — plain JSON response
    if (contentType.includes('application/json')) {
      const data = await res.json();
      onCrisis(data);
      return;
    }

    // Normal — Server-Sent Events stream
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let isCrisisStream = false;
    let doneFired = false;

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        if (!doneFired) onDone();
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // keep incomplete line

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const event = JSON.parse(line.slice(6));
          if (event.type === 'meta') {
            if (event.crisis) {
              isCrisisStream = true;
            } else {
              onMeta(event);
            }
          }
          if (event.type === 'chunk') {
            if (isCrisisStream) {
              onCrisis({ response: event.content });
            } else {
              onChunk(event.content);
            }
          }
          if (event.type === 'error') {
            onError(event.detail || 'Pipeline error');
          }
          if (event.type === 'done') { doneFired = true; onDone(); }
        } catch {
          // skip malformed event
        }
      }
    }
  } catch (err) {
    onError(err.message || 'Could not reach the server. Make sure the backend is running.');
  }
}

export async function fetchHealth() {
  const res = await fetch('/health');
  return res.json();
}

export async function clearSession(sessionId) {
  const res = await fetch(`/session/${sessionId}`, { method: 'DELETE' });
  return res.ok;
}
