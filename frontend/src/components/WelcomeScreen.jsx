export default function WelcomeScreen({ mode }) {
  return (
    <div style={styles.wrap}>
      <img src="/logo.png" alt="URAAN Safe Voice" style={styles.logo} />

      <h2 style={styles.heading}>URAAN Safe Voice</h2>

      <p style={styles.sub}>
        {mode === 'analytical'
          ? 'Analytical mode — responses are clinical, research-grounded, and technique-focused.'
          : 'A safe, confidential space for mental health support.\nBegin whenever you are ready.'}
      </p>

      <div style={styles.divider} />

      <p style={styles.emergency}>
        Emergency: <strong>115</strong> &nbsp;·&nbsp; Umang: <strong>0317-4288665</strong>
      </p>
    </div>
  );
}

const styles = {
  wrap: {
    flex:           1,
    display:        'flex',
    flexDirection:  'column',
    alignItems:     'center',
    justifyContent: 'center',
    padding:        '40px 24px',
    textAlign:      'center',
    maxWidth:       480,
    margin:         '0 auto',
    width:          '100%',
  },
  logo: {
    height:       100,
    width:        'auto',
    marginBottom: 22,
    objectFit:    'contain',
    opacity:      0.92,
  },
  heading: {
    fontSize:      22,
    fontWeight:    700,
    color:         '#3B1D66',
    margin:        '0 0 12px',
    letterSpacing: '-0.3px',
  },
  sub: {
    color:       '#64748B',
    fontSize:    14,
    lineHeight:  1.7,
    margin:      '0 0 24px',
    whiteSpace:  'pre-line',
    maxWidth:    360,
  },
  divider: {
    width:        40,
    height:       2,
    background:   '#E8D5B0',
    borderRadius: 99,
    marginBottom: 20,
  },
  emergency: {
    fontSize:  12,
    color:     '#94A3B8',
    margin:    0,
  },
};
