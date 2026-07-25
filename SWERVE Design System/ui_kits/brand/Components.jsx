// SWERVE — Shared Components (matches swerve.wtf visual design)

const GRAD        = 'linear-gradient(135deg, #9666e3, #1892f3)';
const BG          = '#080714';
const BG_CARD     = '#12101e';
const BG_CARD2    = '#0f0d1c';
const BORDER      = 'rgba(255,255,255,0.07)';
const BORDER_GLOW = 'rgba(150,102,227,0.25)';
const FG1         = '#ffffff';
const FG2         = 'rgba(255,255,255,0.62)';
const FG3         = 'rgba(255,255,255,0.35)';

// Sector badge colors matching real site
const SECTOR_COLORS = {
  'Technology':  { bg: 'linear-gradient(135deg,#1a6ef5,#00c4cc)', color: '#fff' },
  'Energy':      { bg: 'linear-gradient(135deg,#f5a623,#f5642e)', color: '#fff' },
  'Macro':       { bg: 'linear-gradient(135deg,#9666e3,#5b3fc4)', color: '#fff' },
  'Global FX':   { bg: 'linear-gradient(135deg,#1892f3,#0b5fcf)', color: '#fff' },
  'Healthcare':  { bg: 'linear-gradient(135deg,#00b894,#00cec9)', color: '#fff' },
  'Consumer':    { bg: 'linear-gradient(135deg,#e17055,#d63031)', color: '#fff' },
  'Financials':  { bg: 'linear-gradient(135deg,#6c5ce7,#1892f3)', color: '#fff' },
  'Finance/Banking': { bg: 'linear-gradient(135deg,#6c5ce7,#1892f3)', color: '#fff' },
  'Emerging':    { bg: GRAD, color: '#fff' },
};

// ── Nav ───────────────────────────────────────────────────
function Nav({ active, onNav }) {
  const links = ['Home', 'Research', 'Insights', 'Contact'];
  return (
    <nav style={{ position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100, background: 'rgba(8,7,20,0.85)', backdropFilter: 'blur(16px)', borderBottom: `1px solid ${BORDER}` }}>
      <div style={{ maxWidth: 1140, margin: '0 auto', padding: '0 32px', height: 56, display: 'flex', alignItems: 'center', gap: 40 }}>
        <img src="../../assets/logo-primary.png" height="24" alt="SWERVE" style={{ flexShrink: 0 }} />
        <div style={{ display: 'flex', gap: 2, flex: 1 }}>
          {links.map(l => (
            <button key={l} onClick={() => onNav && onNav(l)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'Poppins', fontSize: 13, fontWeight: 400, color: active === l ? FG1 : FG3, padding: '5px 12px', borderRadius: 6, transition: 'color 150ms' }}>{l}</button>
          ))}
        </div>
        <button onClick={() => onNav && onNav('Research')} style={{ background: GRAD, border: 'none', borderRadius: 7, padding: '8px 18px', color: '#fff', fontFamily: 'Poppins', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>Access Reports</button>
      </div>
    </nav>
  );
}

// ── SectorBadge ───────────────────────────────────────────
function SectorBadge({ sector }) {
  const style = SECTOR_COLORS[sector] || { bg: 'rgba(255,255,255,0.1)', color: FG2 };
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', fontFamily: 'Poppins', fontSize: 10, fontWeight: 700, padding: '3px 10px', borderRadius: 4, background: style.bg, color: style.color, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
      {sector}
    </span>
  );
}

// ── Btn ───────────────────────────────────────────────────
function Btn({ children, variant = 'primary', size = 'md', onClick, style = {} }) {
  const [h, setH] = React.useState(false);
  const sizes = { sm: { padding: '7px 16px', fontSize: 12 }, md: { padding: '10px 22px', fontSize: 13 }, lg: { padding: '14px 32px', fontSize: 15 } };
  const variants = {
    primary:  { background: GRAD, color: '#fff', border: 'none', ...(h ? { opacity: 0.88, transform: 'translateY(-1px)' } : {}) },
    outline:  { background: 'transparent', color: FG2, border: `1px solid ${BORDER_GLOW}`, ...(h ? { color: FG1, borderColor: 'rgba(150,102,227,0.5)' } : {}) },
    ghost:    { background: 'rgba(255,255,255,0.06)', color: FG2, border: `1px solid ${BORDER}`, ...(h ? { background: 'rgba(255,255,255,0.1)' } : {}) },
  };
  return (
    <button style={{ border: 'none', cursor: 'pointer', fontFamily: 'Poppins', fontWeight: 600, borderRadius: 8, transition: 'all 180ms cubic-bezier(0.4,0,0.2,1)', ...sizes[size], ...variants[variant], ...style }}
      onMouseEnter={() => setH(true)} onMouseLeave={() => setH(false)} onClick={onClick}>{children}</button>
  );
}

// ── Card ──────────────────────────────────────────────────
function Card({ children, style = {}, glow = false }) {
  return (
    <div style={{ background: BG_CARD, border: `1px solid ${glow ? BORDER_GLOW : BORDER}`, borderRadius: 14, ...style }}>
      {children}
    </div>
  );
}

// ── Overline ──────────────────────────────────────────────
function Overline({ children }) {
  return <div style={{ fontFamily: 'Poppins', fontSize: 11, fontWeight: 600, color: '#9666e3', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 12 }}>{children}</div>;
}

Object.assign(window, { Nav, SectorBadge, Btn, Card, Overline, GRAD, BG, BG_CARD, BORDER, FG1, FG2, FG3, SECTOR_COLORS });
