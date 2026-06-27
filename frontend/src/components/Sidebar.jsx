import { MessageSquare, Plus, Trash2 } from 'lucide-react';

export default function Sidebar({ open, sessions, activeId, onNew, onSelect, onDelete }) {
  return (
    <aside style={{ ...styles.sidebar, width: open ? 260 : 0, minWidth: open ? 260 : 0 }}>
      <div style={styles.inner}>

        <div style={styles.sectionLabel}>Chat History</div>

        <button style={styles.newBtn} onClick={onNew}>
          <Plus size={14} />
          New Chat
        </button>

        <div style={styles.list}>
          {sessions.length === 0 ? (
            <p style={styles.empty}>No previous sessions</p>
          ) : (
            sessions.map(s => (
              <div
                key={s.id}
                style={{ ...styles.row, ...(s.id === activeId ? styles.rowActive : {}) }}
              >
                <button style={styles.rowBtn} onClick={() => onSelect(s.id)}>
                  <MessageSquare
                    size={12}
                    color={s.id === activeId ? '#C18D3C' : 'rgba(255,255,255,0.30)'}
                    style={{ flexShrink: 0 }}
                  />
                  <div style={styles.meta}>
                    <span style={styles.rowTitle}>{s.title}</span>
                    <span style={styles.rowDate}>{fmt(s.updatedAt)}</span>
                  </div>
                </button>
                <button
                  style={styles.delBtn}
                  onClick={e => { e.stopPropagation(); onDelete(s.id); }}
                  title="Delete"
                >
                  <Trash2 size={11} color="rgba(255,255,255,0.25)" />
                </button>
              </div>
            ))
          )}
        </div>

        <div style={styles.footer}>
          <span style={styles.footerNote}>Sessions persist while the server runs</span>
        </div>
      </div>
    </aside>
  );
}

function fmt(ts) {
  if (!ts) return '';
  const d = new Date(ts), now = new Date();
  return d.toDateString() === now.toDateString()
    ? d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : d.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

const styles = {
  sidebar: {
    background:    '#3B1D66',
    flexShrink:    0,
    overflow:      'hidden',
    transition:    'width 0.24s ease, min-width 0.24s ease',
    display:       'flex',
    flexDirection: 'column',
    borderRight:   '1px solid rgba(193,141,60,0.18)',
  },
  inner: {
    width:         260,
    height:        '100%',
    display:       'flex',
    flexDirection: 'column',
    padding:       '18px 0 12px',
  },
  sectionLabel: {
    color:         'rgba(232,213,176,0.70)',
    fontSize:      10,
    fontWeight:    600,
    letterSpacing: '0.10em',
    textTransform: 'uppercase',
    padding:       '0 16px 10px',
    borderBottom:  '1px solid rgba(255,255,255,0.07)',
    marginBottom:  12,
  },
  newBtn: {
    display:      'flex',
    alignItems:   'center',
    gap:          7,
    margin:       '0 12px 14px',
    background:   '#C18D3C',
    border:       'none',
    borderRadius: 8,
    color:        '#fff',
    fontSize:     13,
    fontWeight:   600,
    padding:      '9px 14px',
    cursor:       'pointer',
    whiteSpace:   'nowrap',
    boxShadow:    '0 2px 8px rgba(193,141,60,0.35)',
  },
  list: {
    flex:      1,
    overflowY: 'auto',
    padding:   '0 8px',
  },
  empty: {
    color:     'rgba(255,255,255,0.25)',
    fontSize:  12,
    textAlign: 'center',
    padding:   '28px 16px',
    margin:    0,
  },
  row: {
    display:      'flex',
    alignItems:   'center',
    borderRadius: 8,
    marginBottom: 2,
  },
  rowActive: {
    background: 'rgba(193,141,60,0.16)',
  },
  rowBtn: {
    flex:        1,
    display:     'flex',
    alignItems:  'center',
    gap:         8,
    background:  'transparent',
    border:      'none',
    cursor:      'pointer',
    padding:     '9px 8px',
    textAlign:   'left',
    minWidth:    0,
  },
  meta: {
    display:       'flex',
    flexDirection: 'column',
    gap:           2,
    minWidth:      0,
  },
  rowTitle: {
    color:        '#E8E0F4',
    fontSize:     13,
    fontWeight:   500,
    whiteSpace:   'nowrap',
    overflow:     'hidden',
    textOverflow: 'ellipsis',
    maxWidth:     150,
    display:      'block',
  },
  rowDate: {
    color:    'rgba(255,255,255,0.30)',
    fontSize: 10,
  },
  delBtn: {
    background:   'transparent',
    border:       'none',
    cursor:       'pointer',
    padding:      '7px 8px',
    borderRadius: 6,
    flexShrink:   0,
  },
  footer: {
    padding:   '10px 16px 0',
    borderTop: '1px solid rgba(255,255,255,0.06)',
    marginTop: 8,
  },
  footerNote: {
    color:    'rgba(255,255,255,0.20)',
    fontSize: 10,
  },
};
