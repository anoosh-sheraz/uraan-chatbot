import { Brain } from 'lucide-react';

export default function TypingIndicator() {
  return (
    <div style={styles.row}>
      <div style={styles.avatar}>
        <Brain size={16} color="#C18D3C" />
      </div>
      <div style={styles.bubble}>
        <span style={styles.dot} />
        <span style={{ ...styles.dot, animationDelay: '0.2s' }} />
        <span style={{ ...styles.dot, animationDelay: '0.4s' }} />
      </div>
      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
          40%            { transform: translateY(-6px); opacity: 1; }
        }
      `}</style>
    </div>
  );
}

const styles = {
  row: {
    display:      'flex',
    alignItems:   'flex-end',
    gap:          8,
    marginBottom: 20,
  },
  avatar: {
    width:          32,
    height:         32,
    background:     '#F0EBF8',
    borderRadius:   99,
    display:        'flex',
    alignItems:     'center',
    justifyContent: 'center',
    flexShrink:     0,
    border:         '1px solid #E8D5B0',
  },
  bubble: {
    background:   '#fff',
    border:       '1px solid #E8D5B0',
    borderRadius: '18px 18px 18px 4px',
    padding:      '14px 18px',
    display:      'flex',
    gap:          5,
    alignItems:   'center',
    boxShadow:    '0 1px 4px rgba(59,29,102,0.06)',
  },
  dot: {
    display:         'inline-block',
    width:           8,
    height:          8,
    borderRadius:    '50%',
    background:      '#C18D3C',
    animation:       'bounce 1.2s infinite ease-in-out',
  },
};
