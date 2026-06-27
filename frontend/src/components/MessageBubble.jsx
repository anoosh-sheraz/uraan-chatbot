import { ShieldCheck, Brain, AlertTriangle, TrendingDown, BookOpen } from 'lucide-react';

export default function MessageBubble({ msg }) {
  if (msg.role === 'crisis') return <CrisisCard msg={msg} />;

  const isUser = msg.role === 'user';

  return (
    <div style={{ ...styles.row, justifyContent: isUser ? 'flex-end' : 'flex-start' }}>
      {!isUser && (
        <div style={styles.avatar}>
          <Brain size={16} color="#C18D3C" />
        </div>
      )}

      <div style={{ maxWidth: '74%' }}>
        {!isUser && msg.meta && <MetaBadges meta={msg.meta} />}
        {!isUser && msg.meta?.sentiment_drift && <DriftWarning />}
        {!isUser && msg.meta?.resources?.length > 0 && (
          <ResourceCard resources={msg.meta.resources} />
        )}

        <div style={isUser ? styles.userBubble : styles.botBubble}>
          <p style={{ ...styles.text, color: isUser ? '#fff' : '#1E293B' }}>
            {msg.content || <span style={styles.cursor}>▋</span>}
          </p>
        </div>
        <span style={styles.time}>{msg.time}</span>
      </div>

      {isUser && <div style={styles.userAvatar} />}
    </div>
  );
}

// ── Meta badges ───────────────────────────────────────────────────────────────

function MetaBadges({ meta }) {
  const badges = [];

  if (meta.pii_scrubbed)
    badges.push({
      icon: <ShieldCheck size={11} />,
      text: 'PII removed',
      bg:   '#FDF6E9',
      color:'#92400E',
    });

  if (meta.rag_docs_retrieved > 0)
    badges.push({
      icon: <BookOpen size={11} />,
      text: `${meta.rag_docs_retrieved} context docs`,
      bg:   '#F0EBF8',
      color:'#3B1D66',
    });

  if (meta.primary_affect && meta.primary_affect !== 'NEUTRAL') {
    const affectLabel  = meta.primary_affect.replace(/_/g, ' ').toLowerCase();
    const tierColors   = {
      1: ['#F0FDF4', '#166534'],
      2: ['#FDF6E9', '#92400E'],
      3: ['#FEF2F2', '#991B1B'],
    };
    const [bg, color] = tierColors[meta.risk_tier] || tierColors[1];
    badges.push({ icon: null, text: `Tier ${meta.risk_tier} · ${affectLabel}`, bg, color });
  }

  if (meta.distortions?.length > 0)
    badges.push({
      icon: <AlertTriangle size={11} />,
      text: `${meta.distortions.length} pattern(s) noted`,
      bg:   '#F0EBF8',
      color:'#3B1D66',
    });

  if (!badges.length) return null;

  return (
    <div style={styles.badges}>
      {badges.map((b, i) => (
        <span key={i} style={{ ...styles.badge, background: b.bg, color: b.color }}>
          {b.icon}{b.text}
        </span>
      ))}
    </div>
  );
}

// ── Sentiment drift warning ───────────────────────────────────────────────────

function DriftWarning() {
  return (
    <div style={styles.driftBanner}>
      <TrendingDown size={13} color="#92400E" />
      <span>URAAN has noticed your distress is building. You are not alone in this.</span>
    </div>
  );
}

// ── Tier 2 passive resource card ─────────────────────────────────────────────

function ResourceCard({ resources }) {
  return (
    <div style={styles.resourceCard}>
      <p style={styles.resourceTitle}>Support is available right now</p>
      <div style={styles.resourceGrid}>
        {resources.map((r, i) => (
          <div key={i} style={styles.resourceItem}>
            <span style={styles.resourceLabel}>{r.label}</span>
            {r.number && (
              <a href={`tel:${r.number}`} style={styles.resourceNumber}>{r.number}</a>
            )}
            <span style={styles.resourceAvail}>{r.available}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Crisis card ───────────────────────────────────────────────────────────────

function CrisisCard({ msg }) {
  return (
    <div style={styles.crisisWrap}>
      <div style={styles.crisisHeader}>🚨 Immediate Support Activated</div>
      <p style={styles.crisisBody}>{msg.content}</p>
      <div style={styles.crisisGrid}>
        {[
          { label: 'Ambulance / Rescue', number: '115' },
          { label: 'Umang Helpline',     number: '0317-4288665' },
          { label: 'Rozan Counselling',  number: '051-2890505' },
        ].map(c => (
          <div key={c.number} style={styles.crisisContact}>
            <span style={styles.crisisLabel}>{c.label}</span>
            <a href={`tel:${c.number}`} style={styles.crisisNumber}>{c.number}</a>
          </div>
        ))}
      </div>
      <span style={styles.time}>{msg.time}</span>
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

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
    marginBottom:   18,
    border:         '1px solid #E8D5B0',
  },
  userAvatar: {
    width:        28,
    height:       28,
    background:   'linear-gradient(135deg,#3B1D66,#2D1650)',
    borderRadius: 99,
    flexShrink:   0,
    marginBottom: 18,
  },
  userBubble: {
    background:   'linear-gradient(135deg, #3B1D66, #2D1650)',
    borderRadius: '18px 18px 4px 18px',
    padding:      '12px 16px',
    boxShadow:    '0 2px 8px rgba(59,29,102,0.28)',
  },
  botBubble: {
    background:   '#FFFFFF',
    border:       '1px solid #E8D5B0',
    borderRadius: '18px 18px 18px 4px',
    padding:      '12px 16px',
    boxShadow:    '0 1px 4px rgba(59,29,102,0.06)',
  },
  text: {
    margin:      0,
    fontSize:    15,
    lineHeight:  1.65,
    whiteSpace:  'pre-wrap',
  },
  cursor: {
    animation: 'blink 1s step-end infinite',
    color:     '#C18D3C',
  },
  time: {
    fontSize:  11,
    color:     '#94A3B8',
    marginTop: 4,
    display:   'block',
  },
  badges: {
    display:      'flex',
    gap:          6,
    marginBottom: 6,
    flexWrap:     'wrap',
  },
  badge: {
    display:     'inline-flex',
    alignItems:  'center',
    gap:         4,
    padding:     '3px 8px',
    borderRadius: 99,
    fontSize:    11,
    fontWeight:  500,
  },
  driftBanner: {
    display:      'flex',
    alignItems:   'center',
    gap:          6,
    background:   '#FEF3C7',
    border:       '1px solid #FDE68A',
    borderRadius: 8,
    padding:      '7px 10px',
    marginBottom: 8,
    fontSize:     12,
    color:        '#92400E',
  },
  resourceCard: {
    background:   '#FDF6E9',
    border:       '1px solid #E8D5B0',
    borderRadius: 10,
    padding:      '10px 12px',
    marginBottom: 8,
  },
  resourceTitle: {
    fontSize:     12,
    fontWeight:   600,
    color:        '#C18D3C',
    margin:       '0 0 8px',
  },
  resourceGrid: {
    display:       'flex',
    flexDirection: 'column',
    gap:           6,
  },
  resourceItem: {
    display:    'flex',
    alignItems: 'center',
    gap:        8,
    flexWrap:   'wrap',
  },
  resourceLabel: {
    fontSize:   12,
    color:      '#334155',
    fontWeight: 500,
    minWidth:   160,
  },
  resourceNumber: {
    fontSize:       13,
    fontWeight:     700,
    color:          '#C18D3C',
    textDecoration: 'none',
  },
  resourceAvail: {
    fontSize: 11,
    color:    '#94A3B8',
  },
  crisisWrap: {
    background:   '#FEF2F2',
    border:       '1.5px solid #FECACA',
    borderRadius: 14,
    padding:      '16px 18px',
    marginBottom: 20,
    width:        '100%',
  },
  crisisHeader: {
    fontWeight:   700,
    fontSize:     15,
    color:        '#991B1B',
    marginBottom: 10,
  },
  crisisBody: {
    color:        '#7F1D1D',
    fontSize:     14,
    lineHeight:   1.65,
    marginBottom: 14,
    whiteSpace:   'pre-line',
  },
  crisisGrid: {
    display:             'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap:                 8,
    marginBottom:        10,
  },
  crisisContact: {
    background:    '#fff',
    border:        '1px solid #FECACA',
    borderRadius:  10,
    padding:       '10px 12px',
    display:       'flex',
    flexDirection: 'column',
    gap:           4,
  },
  crisisLabel:  { fontSize: 11, color: '#9CA3AF', fontWeight: 500 },
  crisisNumber: { fontSize: 14, fontWeight: 700, color: '#DC2626', textDecoration: 'none' },
};
