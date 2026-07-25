// SWERVE — Home Page (matches swerve.wtf)
function HomeScreen({ onNav }) {
  const stats = [
    { value: '50+', label: 'Data streams' },
    { value: '40+', label: 'Regions covered' },
    { value: '100+', label: 'Institutional clients' },
    { value: '3x',  label: 'Faster insights' },
  ];

  const features = [
    {
      label: 'AI Ingestion',
      title: 'Document Scanning',
      desc: '50+ live data sources ingested in real-time.',
      visual: <DocScanVisual />,
    },
    {
      label: 'Parallel Compute',
      title: 'Processing Nodes',
      desc: '<50ms distributed compute latency.',
      visual: <NodeVisual />,
    },
    {
      label: 'Macro & Sectoral',
      title: 'Emerging Macro Themes',
      desc: '94% signal accuracy. 2–6 weeks ahead of consensus.',
      visual: <ThemeVisual />,
    },
  ];

  return (
    <div style={{ background: BG, minHeight: '100vh', color: FG1, fontFamily: 'Poppins', position: 'relative' }}>
      {/* bg radial glow */}
      <div style={{ position: 'fixed', inset: 0, background: 'radial-gradient(ellipse 80% 60% at 60% 30%, rgba(90,50,180,0.18) 0%, transparent 70%)', pointerEvents: 'none' }} />

      {/* Hero */}
      <section style={{ maxWidth: 1140, margin: '0 auto', padding: '120px 32px 80px', position: 'relative', display: 'flex', alignItems: 'center', gap: 0 }}>
        <div style={{ flex: 1, maxWidth: 560 }}>
          <h1 style={{ fontSize: 62, fontWeight: 800, lineHeight: 1.05, letterSpacing: '-0.04em', color: '#fff', marginBottom: 24 }}>
            Swerve is how the<br /><span style={{ color: '#fff' }}>best firms</span>
          </h1>
          <p style={{ fontSize: 15, color: FG2, lineHeight: 1.7, maxWidth: 360, marginBottom: 36 }}>
            50+ live data streams, processed in real time. Converted into high-conviction institutional research.
          </p>
          <div style={{ display: 'flex', gap: 12 }}>
            <Btn size="lg" onClick={() => onNav('Research')}>Explore Reports →</Btn>
            <Btn size="lg" variant="outline">See how it works</Btn>
          </div>
          {/* Stats */}
          <div style={{ display: 'flex', gap: 36, marginTop: 52 }}>
            {stats.map((s, i) => (
              <div key={i}>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#fff', letterSpacing: '-0.02em' }}>{s.value}</div>
                <div style={{ fontSize: 11, color: FG3, marginTop: 2 }}>{s.label}</div>
              </div>
            ))}
          </div>
        </div>
        {/* W watermark */}
        <div style={{ position: 'absolute', right: -20, top: '50%', transform: 'translateY(-55%)', opacity: 0.18 }}>
          <img src="../../assets/logo-mark-dark.png" width="480" alt="" style={{ filter: 'brightness(0) invert(0.3) sepia(1) saturate(2) hue-rotate(220deg)' }} />
        </div>
      </section>

      {/* Features */}
      <section style={{ maxWidth: 1140, margin: '0 auto', padding: '60px 32px' }}>
        <Overline>Proprietary Technology</Overline>
        <h2 style={{ fontSize: 40, fontWeight: 700, letterSpacing: '-0.03em', marginBottom: 8 }}>Everything you need</h2>
        <p style={{ fontSize: 15, color: FG2, marginBottom: 40 }}>to understand global markets before anyone else.</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 16 }}>
          {features.map((f, i) => (
            <Card key={i} style={{ padding: 20 }}>
              <div style={{ fontSize: 10, fontWeight: 600, color: '#9666e3', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 8 }}>{f.label}</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: FG1, marginBottom: 12 }}>{f.title}</div>
              <div style={{ marginBottom: 14, minHeight: 80 }}>{f.visual}</div>
              <div style={{ fontSize: 12, color: FG2 }}>{f.desc}</div>
            </Card>
          ))}
        </div>
      </section>

      {/* Two modes */}
      <section style={{ maxWidth: 1140, margin: '0 auto', padding: '60px 32px' }}>
        <Overline>Research Intelligence</Overline>
        <h2 style={{ fontSize: 40, fontWeight: 700, letterSpacing: '-0.03em', marginBottom: 4 }}>Research intelligence.</h2>
        <p style={{ fontSize: 15, color: FG2, marginBottom: 36 }}>Two modes. One platform.</p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          {/* AI Thesis */}
          <Card style={{ padding: 24 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: '#9666e3', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 14 }}>Smart Forecasting</div>
            <div style={{ fontSize: 17, fontWeight: 700, color: FG1, marginBottom: 16 }}>AI-Generated Thesis</div>
            <div style={{ background: '#0a0818', border: `1px solid ${BORDER}`, borderRadius: 10, padding: 16 }}>
              <div style={{ display: 'flex', gap: 8, marginBottom: 12, alignItems: 'center' }}>
                <SectorBadge sector="Finance/Banking" />
                <span style={{ fontSize: 10, fontWeight: 600, color: FG3, background: 'rgba(255,255,255,0.06)', padding: '2px 8px', borderRadius: 4 }}>LIVE</span>
              </div>
              <div style={{ fontSize: 13, color: FG2, lineHeight: 1.65, marginBottom: 16 }}>
                Thesis: NBFC loans and BFSI balance sheets remain compelling for long-exposure in this class. Credit penetration remains steady, driven by micro-lending expansion…
              </div>
              {[
                { label: 'Conviction', value: 'High (91/100)', color: '#9666e3' },
                { label: 'Signal', value: 'Bullish 79/100', color: '#1892f3' },
                { label: 'Horizon', value: '12–18 months', color: '#1892f3' },
              ].map((r, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderTop: `1px solid ${BORDER}` }}>
                  <span style={{ fontSize: 12, color: FG3 }}>{r.label}</span>
                  <span style={{ fontSize: 12, fontWeight: 600, color: r.color }}>{r.value}</span>
                </div>
              ))}
            </div>
          </Card>
          {/* Chat */}
          <Card style={{ padding: 24, display: 'flex', flexDirection: 'column' }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: '#1892f3', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 14 }}>Chat with Swerve</div>
            <div style={{ fontSize: 17, fontWeight: 700, color: FG1, marginBottom: 16 }}>Your AI Research Analyst</div>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ fontSize: 13, color: FG2, padding: '10px 14px', background: '#0a0818', border: `1px solid ${BORDER}`, borderRadius: 10 }}>
                Hey! How can I help you analyze market earnings?
              </div>
              <div style={{ alignSelf: 'flex-end', fontSize: 13, color: '#fff', padding: '10px 14px', background: GRAD, borderRadius: 10, maxWidth: '80%' }}>
                Summarize the key revenue trends this week
              </div>
              <div style={{ fontSize: 13, color: FG2, padding: '10px 14px', background: '#0a0818', border: `1px solid ${BORDER}`, borderRadius: 10 }}>
                Revenue grew 12% YoY driven by cloud segment. Consulting margins compressed 60bps as R&D spend. Management raised FY guidance to 15.5%.
              </div>
            </div>
            <button onClick={() => onNav && onNav('Research')} style={{ marginTop: 16, background: GRAD, border: 'none', borderRadius: 8, padding: '12px', color: '#fff', fontFamily: 'Poppins', fontSize: 13, fontWeight: 600, cursor: 'pointer', width: '100%' }}>
              Ask Swerve →
            </button>
          </Card>
        </div>
      </section>

      {/* CTA */}
      <section style={{ maxWidth: 680, margin: '20px auto 80px', padding: '0 32px' }}>
        <Card style={{ padding: '48px 40px', textAlign: 'center', background: '#0d0b1e' }}>
          <Overline>Get started</Overline>
          <h2 style={{ fontSize: 34, fontWeight: 700, letterSpacing: '-0.03em', marginBottom: 12 }}>Ready to see the research?</h2>
          <p style={{ fontSize: 14, color: FG2, marginBottom: 28 }}>Browse our latest sector reports, macro analyses, and sentiment studies.</p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
            <Btn onClick={() => onNav('Research')}>Browse Reports</Btn>
            <Btn variant="ghost" onClick={() => onNav('Contact')}>Contact Us</Btn>
          </div>
        </Card>
      </section>
    </div>
  );
}

// ── Feature card visuals ──────────────────────────────────
function DocScanVisual() {
  return (
    <div style={{ background: '#0a0818', borderRadius: 8, padding: 10, border: `1px solid ${BORDER}` }}>
      {[60,80,70,90,55].map((w,i) => <div key={i} style={{ height: 6, borderRadius: 3, background: i===3 ? 'linear-gradient(to right,#9666e3,#1892f3)' : 'rgba(255,255,255,0.08)', width: `${w}%`, marginBottom: 5 }} />)}
      <div style={{ marginTop: 6, fontSize: 10, color: '#9666e3', fontWeight: 600 }}>+ 50+ sources</div>
    </div>
  );
}
function NodeVisual() {
  const nodes = [[50,20],[25,50],[75,50],[50,80]];
  return (
    <svg viewBox="0 0 100 100" style={{ width: '100%', height: 80 }}>
      <line x1="50" y1="20" x2="25" y2="50" stroke="rgba(150,102,227,0.4)" strokeWidth="1.5"/>
      <line x1="50" y1="20" x2="75" y2="50" stroke="rgba(24,146,243,0.4)" strokeWidth="1.5"/>
      <line x1="25" y1="50" x2="50" y2="80" stroke="rgba(150,102,227,0.4)" strokeWidth="1.5"/>
      <line x1="75" y1="50" x2="50" y2="80" stroke="rgba(24,146,243,0.4)" strokeWidth="1.5"/>
      {nodes.map(([cx,cy],i) => <circle key={i} cx={cx} cy={cy} r="5" fill={i%2===0?'#9666e3':'#1892f3'} opacity="0.9"/>)}
    </svg>
  );
}
function ThemeVisual() {
  const tags = ['Data Consumers','Inflation/Yields','FinTech Firms','Rate Sensitivity','China FX Risk','Energy Transition','Clean Energy','AR/Capex'];
  const colors = ['#9666e3','#1892f3','#00b894','#e17055','#6c5ce7','#00cec9','#fdcb6e','#a29bfe'];
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
      {tags.map((t,i) => <span key={i} style={{ fontSize: 9, fontWeight: 700, padding: '2px 7px', borderRadius: 3, background: `${colors[i%colors.length]}22`, color: colors[i%colors.length], border: `1px solid ${colors[i%colors.length]}44` }}>#{t}</span>)}
    </div>
  );
}

Object.assign(window, { HomeScreen });
