// SWERVE — Dashboard Screen (AI Research Platform)
function DashboardScreen() {
  const [generating, setGenerating] = React.useState(false);
  const [generated, setGenerated] = React.useState(false);

  function handleGenerate() {
    setGenerating(true);
    setGenerated(false);
    setTimeout(() => { setGenerating(false); setGenerated(true); }, 2200);
  }

  const recentReports = [
    { region: 'India', sector: 'Technology', title: 'India Tech Supercycle: What Comes After the Rally?', age: '2h ago', ai: true, status: 'published' },
    { region: 'Brazil', sector: 'Commodities', title: 'Brazilian Agri Exports and the FX Pivot', age: '5h ago', ai: true, status: 'published' },
    { region: 'Vietnam', sector: 'Manufacturing', title: 'Vietnam Supply Chain: A Post-China Blueprint', age: '1d ago', ai: false, status: 'published' },
    { region: 'MENA', sector: 'Fixed Income', title: 'Gulf Sovereign Bonds: Duration Risk in 2025', age: '1d ago', ai: true, status: 'draft' },
  ];

  const stats = [
    { label: 'Reports This Quarter', value: '512', change: '▲ 18% vs last qtr', pos: true },
    { label: 'Avg. Generation Time', value: '4.2 min', change: '▼ 62% faster', pos: true },
    { label: 'Active Analysts', value: '104', change: null },
    { label: 'Markets Covered', value: '43', change: '▲ 6 new', pos: true },
  ];

  return (
    <div style={{ background: BG, minHeight: '100vh', color: FG1, fontFamily: 'Poppins' }}>
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '32px 28px' }}>

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 28 }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 500, color: FG3, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 6 }}>Good morning, James</div>
            <div style={{ fontSize: 28, fontWeight: 700, color: FG1, letterSpacing: '-0.02em' }}>Research Dashboard</div>
          </div>
          <button onClick={handleGenerate} disabled={generating} style={{ background: generating ? 'rgba(150,102,227,0.2)' : 'linear-gradient(to right,#9666e3,#1892f3)', border: generating ? '1px solid rgba(150,102,227,0.4)' : 'none', borderRadius: 9, padding: '11px 22px', color: '#fff', fontFamily: 'Poppins', fontSize: 13, fontWeight: 600, cursor: generating ? 'default' : 'pointer', display: 'flex', alignItems: 'center', gap: 8, transition: 'all 200ms' }}>
            {generating ? (
              <><SpinIcon />Generating report…</>
            ) : generated ? (
              <><span style={{ fontSize: 14 }}>✓</span> Report Ready</>
            ) : (
              <><span style={{ fontSize: 16 }}>⚡</span> Generate Report</>
            )}
          </button>
        </div>

        {/* Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 14, marginBottom: 28 }}>
          {stats.map((s, i) => (
            <Card key={i} gradient={i === 0}>
              <div style={{ fontSize: 10, fontWeight: 600, color: FG3, letterSpacing: '0.07em', textTransform: 'uppercase', marginBottom: 8 }}>{s.label}</div>
              <div style={{ fontSize: 24, fontWeight: 700, color: FG1, letterSpacing: '-0.02em', marginBottom: s.change ? 5 : 0 }}>{s.value}</div>
              {s.change && <div style={{ fontSize: 11, fontWeight: 600, color: s.pos ? '#34d399' : '#f87171' }}>{s.change}</div>}
            </Card>
          ))}
        </div>

        {/* AI generation toast */}
        {generated && (
          <div style={{ background: 'rgba(150,102,227,0.1)', border: '1px solid rgba(150,102,227,0.3)', borderRadius: 10, padding: '12px 18px', marginBottom: 20, display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#9666e3', flexShrink: 0 }} />
            <div style={{ fontSize: 13, color: FG2 }}>AI generated <span style={{ color: FG1, fontWeight: 600 }}>Indonesia Macro Outlook Q2 2025</span> in 3.8 minutes</div>
            <button style={{ marginLeft: 'auto', background: 'linear-gradient(to right,#9666e3,#1892f3)', border: 'none', borderRadius: 6, padding: '5px 14px', color: '#fff', fontFamily: 'Poppins', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>Review →</button>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 20 }}>
          {/* Reports */}
          <div>
            <SLabel action="View all →">Recent Reports</SLabel>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {recentReports.map((r, i) => (
                <div key={i} style={{ background: BG_ELEVATED, border: `1px solid ${i === 0 && generated ? 'rgba(150,102,227,0.35)' : BORDER}`, borderRadius: 12, padding: '14px 18px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 14, transition: 'border-color 180ms' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', gap: 6, marginBottom: 7, flexWrap: 'wrap', alignItems: 'center' }}>
                      <Badge color="purple">{r.region}</Badge>
                      <Badge color="blue">{r.sector}</Badge>
                      {r.ai && <span style={{ fontSize: 10, fontWeight: 600, color: '#aa7bff', background: 'rgba(170,123,255,0.12)', border: '1px solid rgba(170,123,255,0.22)', padding: '2px 8px', borderRadius: 9999 }}>AI</span>}
                      {r.status === 'draft' && <span style={{ fontSize: 10, fontWeight: 600, color: FG3, background: 'rgba(255,255,255,0.06)', border: `1px solid ${BORDER}`, padding: '2px 8px', borderRadius: 9999 }}>DRAFT</span>}
                    </div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: FG1, lineHeight: 1.35 }}>{r.title}</div>
                  </div>
                  <div style={{ fontSize: 11, color: FG3, flexShrink: 0 }}>{r.age}</div>
                  <div style={{ fontSize: 16, color: FG3 }}>→</div>
                </div>
              ))}
            </div>
          </div>

          {/* Sidebar */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div>
              <SLabel>AI Performance</SLabel>
              <Card>
                {[
                  { label: 'Avg. time to publish', value: '4.2 min' },
                  { label: 'Human review rate', value: '98.4%' },
                  { label: 'Reports this week', value: '47' },
                  { label: 'Analyst hours saved', value: '312h' },
                ].map((m, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '9px 0', borderBottom: i < 3 ? `1px solid ${BORDER}` : 'none' }}>
                    <div style={{ fontSize: 12, color: FG3 }}>{m.label}</div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: FG1 }}>{m.value}</div>
                  </div>
                ))}
              </Card>
            </div>
            <div>
              <SLabel>Top Markets</SLabel>
              <Card style={{ padding: 0 }}>
                {[
                  { name: 'India', count: 142, pos: true },
                  { name: 'Brazil', count: 98, pos: true },
                  { name: 'Vietnam', count: 76, pos: false },
                  { name: 'MENA', count: 54, pos: true },
                ].map((m, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '11px 16px', borderBottom: i < 3 ? `1px solid ${BORDER}` : 'none' }}>
                    <div style={{ fontSize: 13, color: FG2 }}>{m.name}</div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <Spark positive={m.pos} />
                      <div style={{ fontSize: 12, fontWeight: 600, color: FG3, minWidth: 28, textAlign: 'right' }}>{m.count}</div>
                    </div>
                  </div>
                ))}
              </Card>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function SpinIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" style={{ animation: 'spin 0.8s linear infinite' }}>
      <circle cx="7" cy="7" r="5.5" stroke="rgba(255,255,255,0.3)" strokeWidth="1.5"/>
      <path d="M7 1.5A5.5 5.5 0 0 1 12.5 7" stroke="#fff" strokeWidth="1.5" strokeLinecap="round"/>
      <style>{`@keyframes spin { to { transform: rotate(360deg); transform-origin: center; } }`}</style>
    </svg>
  );
}

Object.assign(window, { DashboardScreen });
