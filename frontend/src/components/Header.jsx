import { Menu, RefreshCw, Wifi, WifiOff } from 'lucide-react';

export default function Header({
  sidebarOpen, onToggleSidebar,
  backendOnline, messageCount, onClear,
  mode, onModeChange,
}) {
  return (
    <header style={styles.header}>
      <div style={styles.left}>
        <button style={styles.menuBtn} onClick={onToggleSidebar} title="Toggle sidebar">
          <Menu size={18} color="#fff" />
        </button>
        <img src="/logo.png" alt="URAAN" style={styles.logo} />
        <div>
          <h1 style={styles.title}>URAAN Safe Voice</h1>
          <p style={styles.subtitle}>Clinically-informed mental health support</p>
        </div>
      </div>

      <div style={styles.right}>
        <ModeToggle mode={mode} onChange={onModeChange} />

        <div style={{
          ...styles.statusBadge,
          background: backendOnline ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
          color:      backendOnline ? '#86efac'              : '#fca5a5',
        }}>
          {backendOnline ? <Wifi size={11} /> : <WifiOff size={11} />}
          <span>{backendOnline ? 'Connected' : 'Offline'}</span>
        </div>

        {messageCount > 0 && (
          <button onClick={onClear} style={styles.clearBtn} title="Clear conversation">
            <RefreshCw size={13} />
            <span>New Session</span>
          </button>
        )}
      </div>
    </header>
  );
}

function ModeToggle({ mode, onChange }) {
  const analytical = mode === 'analytical';
  return (
    <div style={styles.toggleWrap}>
      <span style={{ ...styles.modeLabel, color: !analytical ? '#C18D3C' : 'rgba(255,255,255,0.35)' }}>
        Empathetic
      </span>
      <div
        role="switch"
        aria-checked={analytical}
        style={{ ...styles.track, background: analytical ? '#C18D3C' : 'rgba(255,255,255,0.18)' }}
        onClick={() => onChange(analytical ? 'empathetic' : 'analytical')}
      >
        <div style={{ ...styles.thumb, transform: analytical ? 'translateX(16px)' : 'translateX(2px)' }} />
      </div>
      <span style={{ ...styles.modeLabel, color: analytical ? '#C18D3C' : 'rgba(255,255,255,0.35)' }}>
        Analytical
      </span>
    </div>
  );
}

const styles = {
  header: {
    background:     'linear-gradient(135deg, #3B1D66 0%, #2D1650 100%)',
    padding:        '10px 20px',
    display:        'flex',
    alignItems:     'center',
    justifyContent: 'space-between',
    boxShadow:      '0 2px 12px rgba(59,29,102,0.50)',
    flexShrink:     0,
    zIndex:         10,
  },
  left: {
    display:    'flex',
    alignItems: 'center',
    gap:        12,
  },
  menuBtn: {
    background:   'rgba(255,255,255,0.10)',
    border:       '1px solid rgba(255,255,255,0.12)',
    borderRadius: 8,
    padding:      '6px 8px',
    cursor:       'pointer',
    display:      'flex',
    alignItems:   'center',
    flexShrink:   0,
  },
  logo: {
    height:       36,
    width:        36,
    objectFit:    'contain',
    borderRadius: 8,
    background:   'rgba(255,255,255,0.10)',
    padding:      3,
    flexShrink:   0,
  },
  title: {
    color:         '#fff',
    fontSize:      16,
    fontWeight:    700,
    margin:        0,
    letterSpacing: '-0.3px',
  },
  subtitle: {
    color:     'rgba(255,255,255,0.50)',
    fontSize:  11,
    margin:    0,
    marginTop: 1,
  },
  right: {
    display:    'flex',
    alignItems: 'center',
    gap:        12,
  },
  toggleWrap: {
    display:    'flex',
    alignItems: 'center',
    gap:        7,
  },
  modeLabel: {
    fontSize:   12,
    fontWeight: 500,
    userSelect: 'none',
    transition: 'color 0.20s',
    whiteSpace: 'nowrap',
  },
  track: {
    width:        36,
    height:       20,
    borderRadius: 99,
    cursor:       'pointer',
    position:     'relative',
    transition:   'background 0.22s',
    flexShrink:   0,
  },
  thumb: {
    position:     'absolute',
    top:          2,
    width:        16,
    height:       16,
    borderRadius: 99,
    background:   '#fff',
    boxShadow:    '0 1px 4px rgba(0,0,0,0.25)',
    transition:   'transform 0.22s',
  },
  statusBadge: {
    display:      'flex',
    alignItems:   'center',
    gap:          4,
    padding:      '4px 9px',
    borderRadius: 99,
    fontSize:     11,
    fontWeight:   500,
  },
  clearBtn: {
    display:      'flex',
    alignItems:   'center',
    gap:          5,
    background:   'rgba(255,255,255,0.10)',
    border:       '1px solid rgba(193,141,60,0.40)',
    color:        '#fff',
    borderRadius: 8,
    padding:      '5px 11px',
    fontSize:     12,
    fontWeight:   500,
    cursor:       'pointer',
    whiteSpace:   'nowrap',
  },
};
