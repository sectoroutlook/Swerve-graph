// SWERVE Brand UI Kit — Feature Cards Section

const features = [
  {
    icon: '⚡',
    title: 'Real-Time Tracking',
    desc: 'Monitor every metric that matters — live, as it happens. No lag, no guessing.',
    accent: '#a78bfa',
  },
  {
    icon: '🎯',
    title: 'Goal Engine',
    desc: 'Set targets that adapt to you. SWERVE learns your pace and pushes you further.',
    accent: '#4d9ef5',
  },
  {
    icon: '🔥',
    title: 'Performance Streaks',
    desc: 'Consistency is everything. Build your streak, protect it, own it.',
    accent: '#93c5fd',
  },
  {
    icon: '📊',
    title: 'Deep Analytics',
    desc: 'See beyond the numbers. Understand your patterns and break through plateaus.',
    accent: '#c4b5fd',
  },
  {
    icon: '🤝',
    title: 'Team Mode',
    desc: 'Compete or collaborate. SWERVE connects you with your crew in real time.',
    accent: '#7c5ce8',
  },
  {
    icon: '🛡️',
    title: 'Always Private',
    desc: 'Your data stays yours. End-to-end encrypted, always in your control.',
    accent: '#6d9ef5',
  },
];

const SwerveFeatures = () => {
  const [hovered, setHovered] = React.useState(null);

  const sectionStyle = {
    padding: '96px 48px',
    background: '#0d0d0d',
    position: 'relative',
  };
  const headingStyle = {
    fontFamily: 'Poppins, sans-serif', fontSize: '42px', fontWeight: 900,
    letterSpacing: '-0.03em', color: '#fff', marginBottom: '12px', textAlign: 'center',
  };
  const subStyle = {
    fontFamily: 'Poppins, sans-serif', fontSize: '16px', fontWeight: 400,
    color: 'rgba(255,255,255,0.5)', textAlign: 'center', marginBottom: '56px',
  };
  const gridStyle = {
    display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px',
    maxWidth: '960px', margin: '0 auto',
  };
  const cardBase = {
    background: '#141414', border: '1px solid rgba(255,255,255,0.07)',
    borderRadius: '16px', padding: '28px 24px',
    transition: 'transform 220ms cubic-bezier(0.4,0,0.2,1), border-color 220ms, box-shadow 220ms',
    cursor: 'default',
  };
  const iconStyle = (accent) => ({
    fontSize: '28px', marginBottom: '14px', display: 'block',
    filter: 'none',
  });
  const dotStyle = (accent) => ({
    width: '32px', height: '32px', borderRadius: '8px',
    background: accent + '22', display: 'flex', alignItems: 'center',
    justifyContent: 'center', marginBottom: '14px', fontSize: '16px',
    border: `1px solid ${accent}33`,
  });
  const titleStyle = {
    fontFamily: 'Poppins, sans-serif', fontSize: '15px', fontWeight: 700,
    color: '#fff', marginBottom: '8px',
  };
  const descStyle = {
    fontFamily: 'Poppins, sans-serif', fontSize: '13px', fontWeight: 400,
    color: 'rgba(255,255,255,0.5)', lineHeight: 1.65,
  };

  return (
    <section style={sectionStyle}>
      <div style={headingStyle}>Everything you need to <span style={{background:'linear-gradient(135deg,#a78bfa,#4d9ef5)',WebkitBackgroundClip:'text',WebkitTextFillColor:'transparent',backgroundClip:'text'}}>perform.</span></div>
      <div style={subStyle}>Built from the ground up for serious movers.</div>
      <div style={gridStyle}>
        {features.map((f, i) => (
          <div
            key={i}
            style={{
              ...cardBase,
              ...(hovered === i ? {
                transform: 'translateY(-4px)',
                borderColor: f.accent + '44',
                boxShadow: `0 12px 40px rgba(0,0,0,0.4), 0 0 0 1px ${f.accent}22`,
              } : {}),
            }}
            onMouseEnter={() => setHovered(i)}
            onMouseLeave={() => setHovered(null)}
          >
            <div style={dotStyle(f.accent)}>{f.icon}</div>
            <div style={titleStyle}>{f.title}</div>
            <div style={descStyle}>{f.desc}</div>
          </div>
        ))}
      </div>
    </section>
  );
};

Object.assign(window, { SwerveFeatures });
