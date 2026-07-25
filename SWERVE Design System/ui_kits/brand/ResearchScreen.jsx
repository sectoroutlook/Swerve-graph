// SWERVE — Research Hub (Reports & Analysis page)
function ResearchScreen() {
  const [activeFilter, setActiveFilter] = React.useState('All');
  const [search, setSearch] = React.useState('');

  const filters = ['All', 'Technology', 'Energy', 'Macro', 'Global FX', 'Healthcare', 'Consumer', 'Financials'];

  const reports = [
    { sector: 'Technology', title: 'Q4 2024 Technology Sector Macro Outlook', type: 'Research Report', date: 'Dec 11, 2024' },
    { sector: 'Energy', title: 'Energy Transition & Portfolio Risk Analysis', type: 'Research Report', date: 'Nov 11, 2024' },
    { sector: 'Macro', title: 'Federal Reserve Policy Impact Assessment', type: 'Research Report', date: 'Oct 1, 2024' },
    { sector: 'Global FX', title: 'Emerging Markets Currency Dynamics', type: 'Research Report', date: 'Oct 10, 2024' },
    { sector: 'Healthcare', title: 'Healthcare Innovation: Fundamental Mapping', type: 'Research Report', date: 'Nov 1, 2024' },
    { sector: 'Consumer', title: 'Consumer Sentiment & Retail Sector Outlook', type: 'Research Report', date: 'Sep 28, 2024' },
    { sector: 'Financials', title: 'Gulf Sovereign Bonds: Duration Risk in 2025', type: 'Research Report', date: 'Apr 19, 2025' },
    { sector: 'Technology', title: 'India Tech Supercycle: What Comes After the Rally?', type: 'Research Report', date: 'Apr 22, 2025' },
    { sector: 'Macro', title: 'Brazil Macro — FX Pivot and Rate Trajectory', type: 'Research Report', date: 'Apr 10, 2025' },
  ];

  const filtered = reports.filter(r =>
    (activeFilter === 'All' || r.sector === activeFilter) &&
    (search === '' || r.title.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div style={{ background: BG, minHeight: '100vh', color: FG1, fontFamily: 'Poppins', position: 'relative' }}>
      <div style={{ position: 'fixed', inset: 0, background: 'radial-gradient(ellipse 60% 50% at 50% 20%, rgba(90,50,180,0.14) 0%, transparent 70%)', pointerEvents: 'none' }} />

      <div style={{ maxWidth: 1140, margin: '0 auto', padding: '48px 32px' }}>
        <Overline>Research Hub</Overline>
        <h1 style={{ fontSize: 44, fontWeight: 700, letterSpacing: '-0.03em', marginBottom: 4 }}>
          Reports &amp; <span style={{ background: GRAD, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>Analysis</span>
        </h1>
        <div style={{ display: 'flex', gap: 8, fontSize: 13, color: FG3, marginBottom: 36 }}>
          <span style={{ color: '#9666e3', cursor: 'pointer', fontWeight: 500 }}>Reports</span>
          <span>/</span>
          <span>Sectors</span>
        </div>

        {/* Search + filter bar */}
        <div style={{ background: BG_CARD, border: `1px solid ${BORDER}`, borderRadius: 10, padding: '10px 16px', marginBottom: 20, display: 'flex', alignItems: 'center', gap: 10 }}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" style={{ flexShrink: 0 }}>
            <circle cx="6" cy="6" r="4.5" stroke="rgba(255,255,255,0.3)" strokeWidth="1.4"/>
            <path d="M9.5 9.5L12 12" stroke="rgba(255,255,255,0.3)" strokeWidth="1.4" strokeLinecap="round"/>
          </svg>
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search reports…"
            style={{ background: 'none', border: 'none', outline: 'none', color: FG1, fontFamily: 'Poppins', fontSize: 13, flex: 1 }} />
        </div>

        {/* Filter pills */}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 28 }}>
          {filters.map(f => (
            <button key={f} onClick={() => setActiveFilter(f)}
              style={{ background: activeFilter === f ? GRAD : 'rgba(255,255,255,0.05)', border: `1px solid ${activeFilter === f ? 'transparent' : BORDER}`, borderRadius: 6, padding: '6px 14px', color: activeFilter === f ? '#fff' : FG3, fontFamily: 'Poppins', fontSize: 12, fontWeight: 600, cursor: 'pointer', transition: 'all 150ms' }}>
              {f}
            </button>
          ))}
        </div>

        {/* Reports grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 16 }}>
          {filtered.map((r, i) => (
            <div key={i} style={{ background: BG_CARD, border: `1px solid ${BORDER}`, borderRadius: 14, padding: '20px 20px 16px', display: 'flex', flexDirection: 'column', gap: 10, cursor: 'pointer', transition: 'border-color 180ms' }}
              onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(150,102,227,0.35)'}
              onMouseLeave={e => e.currentTarget.style.borderColor = BORDER}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', justifyContent: 'space-between' }}>
                <SectorBadge sector={r.sector} />
                <span style={{ fontSize: 10, color: FG3 }}>{r.date}</span>
              </div>
              <div style={{ fontSize: 15, fontWeight: 700, color: FG1, lineHeight: 1.35, flex: 1 }}>{r.title}</div>
              <div style={{ fontSize: 11, color: FG3 }}>{r.type}</div>
              <button style={{ background: GRAD, border: 'none', borderRadius: 7, padding: '9px', color: '#fff', fontFamily: 'Poppins', fontSize: 12, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 7 }}>
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M6 1v7M3 5l3 3 3-3M1 10h10" stroke="#fff" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/></svg>
                Download PDF
              </button>
            </div>
          ))}
        </div>

        {filtered.length === 0 && (
          <div style={{ textAlign: 'center', padding: '60px 0', color: FG3, fontSize: 14 }}>No reports match your search.</div>
        )}

        <div style={{ marginTop: 24, fontSize: 12, color: FG3 }}>Showing {filtered.length} of {reports.length} reports</div>
      </div>
    </div>
  );
}

Object.assign(window, { ResearchScreen });
