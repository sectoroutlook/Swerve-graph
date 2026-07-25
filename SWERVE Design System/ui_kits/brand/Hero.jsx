// SWERVE Brand UI Kit — Hero Section Component

const SwerveHero = ({ onCTA }) => {
  const heroStyles = {
    section: {
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      position: 'relative', overflow: 'hidden', flexDirection: 'column',
      padding: '120px 48px 80px',
    },
    gradBg: {
      position: 'absolute', inset: 0,
      background: 'radial-gradient(ellipse 80% 60% at 60% 0%, rgba(167,139,250,0.25) 0%, transparent 60%), radial-gradient(ellipse 60% 50% at 90% 80%, rgba(77,158,245,0.2) 0%, transparent 60%)',
    },
    mark: {
      position: 'absolute', right: '-40px', top: '50%', transform: 'translateY(-50%)',
      opacity: 0.05, pointerEvents: 'none',
    },
    content: { maxWidth: '760px', textAlign: 'center', position: 'relative', zIndex: 1 },
    eyebrow: {
      display: 'inline-block', fontFamily: 'Poppins, sans-serif',
      fontSize: '11px', fontWeight: 600, letterSpacing: '0.12em', textTransform: 'uppercase',
      color: '#a78bfa', marginBottom: '20px',
      background: 'rgba(167,139,250,0.12)', borderRadius: '9999px',
      padding: '5px 16px', border: '1px solid rgba(167,139,250,0.25)',
    },
    headline: {
      fontFamily: 'Poppins, sans-serif', fontSize: '76px', fontWeight: 900,
      lineHeight: 1.0, letterSpacing: '-0.04em', color: '#fff', marginBottom: '24px',
    },
    accentWord: {
      background: 'linear-gradient(135deg, #c4b5fd, #4d9ef5)',
      WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
      backgroundClip: 'text',
    },
    sub: {
      fontFamily: 'Poppins, sans-serif', fontSize: '18px', fontWeight: 400,
      color: 'rgba(255,255,255,0.6)', lineHeight: 1.65, maxWidth: '520px',
      margin: '0 auto 40px',
    },
    actions: { display: 'flex', gap: '14px', justifyContent: 'center', flexWrap: 'wrap' },
    btnPrimary: {
      background: 'linear-gradient(135deg, #a78bfa, #4d9ef5)',
      border: 'none', borderRadius: '10px', color: '#fff',
      fontFamily: 'Poppins, sans-serif', fontWeight: 700, fontSize: '15px',
      padding: '15px 36px', cursor: 'pointer',
      boxShadow: '0 8px 32px rgba(77,158,245,0.25)',
      transition: 'transform 200ms, box-shadow 200ms',
    },
    btnSecondary: {
      background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.14)',
      borderRadius: '10px', color: '#fff',
      fontFamily: 'Poppins, sans-serif', fontWeight: 600, fontSize: '15px',
      padding: '15px 36px', cursor: 'pointer',
      transition: 'background 200ms',
    },
    stats: {
      display: 'flex', gap: '48px', justifyContent: 'center', marginTop: '72px',
      position: 'relative', zIndex: 1,
    },
    statItem: { textAlign: 'center' },
    statNum: {
      fontFamily: 'Poppins, sans-serif', fontSize: '36px', fontWeight: 900,
      color: '#fff', letterSpacing: '-0.03em', lineHeight: 1,
    },
    statLabel: {
      fontFamily: 'Poppins, sans-serif', fontSize: '12px', fontWeight: 500,
      color: 'rgba(255,255,255,0.45)', marginTop: '4px', letterSpacing: '0.04em',
    },
    divider: { width: '1px', background: 'rgba(255,255,255,0.1)', alignSelf: 'stretch' },
  };

  return (
    <section style={heroStyles.section}>
      <div style={heroStyles.gradBg} />
      <div style={heroStyles.mark}>
        <img src="../../assets/watermark-gradient.png" width="600" alt="" />
      </div>
      <div style={heroStyles.content}>
        <span style={heroStyles.eyebrow}>Move Different</span>
        <h1 style={heroStyles.headline}>
          Built for those<br />who never <span style={heroStyles.accentWord}>stop.</span>
        </h1>
        <p style={heroStyles.sub}>
          SWERVE is the platform that keeps you ahead. Track, perform, and push beyond every limit you've set.
        </p>
        <div style={heroStyles.actions}>
          <button style={heroStyles.btnPrimary} onClick={onCTA}>Get Started Free</button>
          <button style={heroStyles.btnSecondary}>Watch the Film</button>
        </div>
      </div>
      <div style={heroStyles.stats}>
        <div style={heroStyles.statItem}>
          <div style={heroStyles.statNum}>250K+</div>
          <div style={heroStyles.statLabel}>Athletes</div>
        </div>
        <div style={heroStyles.divider} />
        <div style={heroStyles.statItem}>
          <div style={heroStyles.statNum}>98%</div>
          <div style={heroStyles.statLabel}>Satisfaction</div>
        </div>
        <div style={heroStyles.divider} />
        <div style={heroStyles.statItem}>
          <div style={heroStyles.statNum}>4.9★</div>
          <div style={heroStyles.statLabel}>App Rating</div>
        </div>
      </div>
    </section>
  );
};

Object.assign(window, { SwerveHero });
