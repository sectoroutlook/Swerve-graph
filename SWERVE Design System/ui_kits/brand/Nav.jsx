// SWERVE Brand UI Kit — Navigation Component
// Export to window for use in index.html

const SwerveNav = ({ activePage, onNavigate }) => {
  const navStyles = {
    nav: {
      position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '0 48px', height: '68px',
      background: 'rgba(10,10,10,0.85)',
      backdropFilter: 'blur(20px)',
      borderBottom: '1px solid rgba(255,255,255,0.07)',
    },
    logo: { height: '30px', display: 'block' },
    links: { display: 'flex', gap: '32px', listStyle: 'none' },
    link: {
      fontFamily: 'Poppins, sans-serif', fontSize: '14px', fontWeight: 500,
      color: 'rgba(255,255,255,0.65)', cursor: 'pointer',
      transition: 'color 200ms', textDecoration: 'none',
    },
    linkActive: { color: '#ffffff' },
    cta: {
      background: 'linear-gradient(135deg, #a78bfa, #4d9ef5)',
      border: 'none', borderRadius: '8px', color: '#fff',
      fontFamily: 'Poppins, sans-serif', fontWeight: 600, fontSize: '13px',
      padding: '9px 20px', cursor: 'pointer',
      transition: 'opacity 200ms',
    },
    right: { display: 'flex', alignItems: 'center', gap: '16px' },
  };

  const pages = ['Home', 'Features', 'Pricing', 'About'];

  return (
    <nav style={navStyles.nav}>
      <img src="../../assets/logo-primary.png" style={navStyles.logo} alt="SWERVE" />
      <ul style={navStyles.links}>
        {pages.map(p => (
          <li key={p}>
            <span
              style={{ ...navStyles.link, ...(activePage === p ? navStyles.linkActive : {}) }}
              onClick={() => onNavigate && onNavigate(p)}
            >{p}</span>
          </li>
        ))}
      </ul>
      <div style={navStyles.right}>
        <span style={{ ...navStyles.link, color: 'rgba(255,255,255,0.65)' }}>Sign In</span>
        <button style={navStyles.cta}>Get Started</button>
      </div>
    </nav>
  );
};

Object.assign(window, { SwerveNav });
