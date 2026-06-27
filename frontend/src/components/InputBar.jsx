import { useState } from 'react';
import { Send } from 'lucide-react';

export default function InputBar({ onSend, disabled }) {
  const [text, setText] = useState('');

  const handleSubmit = () => {
    const msg = text.trim();
    if (!msg || disabled) return;
    setText('');
    onSend(msg);
  };

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const charCount = text.length;
  const overLimit  = charCount > 2000;

  return (
    <div style={styles.wrap}>
      <div style={{
        ...styles.row,
        border: overLimit
          ? '1.5px solid #EF4444'
          : '1.5px solid #E8D5B0',
      }}>
        <textarea
          style={styles.textarea}
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Share how you're feeling… your message is private and secure."
          rows={2}
          disabled={disabled}
          maxLength={2100}
        />
        <div style={styles.actions}>
          <span style={{ ...styles.counter, color: overLimit ? '#EF4444' : '#94A3B8' }}>
            {charCount}/2000
          </span>
          <button
            style={{
              ...styles.sendBtn,
              opacity: (!text.trim() || disabled || overLimit) ? 0.45 : 1,
            }}
            onClick={handleSubmit}
            disabled={!text.trim() || disabled || overLimit}
          >
            <Send size={18} color="#fff" />
          </button>
        </div>
      </div>
    </div>
  );
}

const styles = {
  wrap: {
    borderTop:  '1px solid #E8D5B0',
    padding:    '12px 20px 16px',
    background: '#fff',
    flexShrink: 0,
  },
  hint: {
    fontSize:     11,
    color:        '#94A3B8',
    marginBottom: 8,
  },
  kbd: {
    background:   '#F1F5F9',
    border:       '1px solid #CBD5E1',
    borderRadius: 4,
    padding:      '1px 5px',
    fontSize:     10,
    fontFamily:   'monospace',
  },
  row: {
    display:      'flex',
    alignItems:   'flex-end',
    gap:          10,
    background:   '#F8F5FF',
    borderRadius: 14,
    padding:      '10px 12px 10px 14px',
  },
  textarea: {
    flex:        1,
    background:  'transparent',
    border:      'none',
    outline:     'none',
    resize:      'none',
    fontSize:    15,
    color:       '#1E293B',
    lineHeight:  1.5,
    fontFamily:  'inherit',
  },
  actions: {
    display:        'flex',
    flexDirection:  'column',
    alignItems:     'flex-end',
    gap:            6,
  },
  counter: {
    fontSize:            11,
    fontVariantNumeric:  'tabular-nums',
  },
  sendBtn: {
    width:          38,
    height:         38,
    borderRadius:   10,
    background:     'linear-gradient(135deg, #3B1D66, #2D1650)',
    border:         'none',
    cursor:         'pointer',
    display:        'flex',
    alignItems:     'center',
    justifyContent: 'center',
    boxShadow:      '0 2px 6px rgba(59,29,102,0.40)',
    transition:     'opacity 0.15s',
  },
  disclaimer: {
    marginTop: 8,
    fontSize:  11,
    color:     '#94A3B8',
    textAlign: 'center',
  },
};
