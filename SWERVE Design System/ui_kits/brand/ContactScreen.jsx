// SWERVE — Contact Page (matches swerve.wtf/contact)
function ContactScreen() {
  const [form, setForm] = React.useState({ name: '', email: '', company: '', message: '' });
  const [sent, setSent] = React.useState(false);

  const inputStyle = {
    background: '#0d0b1e', border: `1px solid ${BORDER}`, borderRadius: 8,
    color: FG1, fontFamily: 'Poppins', fontSize: 13, padding: '11px 14px',
    outline: 'none', width: '100%', boxSizing: 'border-box', transition: 'border-color 200ms',
  };

  return (
    <div style={{ background: BG, minHeight: '100vh', color: FG1, fontFamily: 'Poppins', position: 'relative' }}>
      <div style={{ position: 'fixed', inset: 0, background: 'radial-gradient(ellipse 60% 50% at 50% 20%, rgba(90,50,180,0.12) 0%, transparent 70%)', pointerEvents: 'none' }} />

      <div style={{ maxWidth: 1000, margin: '0 auto', padding: '52px 32px' }}>
        <Overline>Get in touch</Overline>
        <h1 style={{ fontSize: 44, fontWeight: 700, letterSpacing: '-0.03em', marginBottom: 40 }}>Talk to Swerve</h1>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.6fr', gap: 32, alignItems: 'start' }}>
          {/* Contact info */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {[
              { icon: '✉', label: 'Email', value: 'akshai@swerve.wtf' },
              { icon: '📍', label: 'Office', value: 'Pune, MH' },
              { icon: '🔒', label: 'Confidentiality', value: 'NDA available on request' },
            ].map((c, i) => (
              <div key={i} style={{ background: BG_CARD, border: `1px solid ${BORDER}`, borderRadius: 12, padding: '14px 18px', display: 'flex', alignItems: 'center', gap: 14 }}>
                <div style={{ width: 36, height: 36, borderRadius: 9, background: 'rgba(150,102,227,0.12)', border: `1px solid rgba(150,102,227,0.22)`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16, flexShrink: 0 }}>{c.icon}</div>
                <div>
                  <div style={{ fontSize: 10, fontWeight: 600, color: FG3, letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 2 }}>{c.label}</div>
                  <div style={{ fontSize: 13, color: FG2 }}>{c.value}</div>
                </div>
              </div>
            ))}
          </div>

          {/* Form */}
          <div style={{ background: BG_CARD, border: `1px solid ${BORDER}`, borderRadius: 14, padding: '28px 28px 24px' }}>
            {sent ? (
              <div style={{ textAlign: 'center', padding: '40px 0' }}>
                <div style={{ fontSize: 32, marginBottom: 14 }}>✓</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: FG1, marginBottom: 8 }}>Message sent</div>
                <div style={{ fontSize: 13, color: FG2 }}>We'll be in touch shortly.</div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 600, color: FG3, letterSpacing: '0.05em', marginBottom: 6 }}>Full name *</div>
                    <input style={inputStyle} placeholder="Jane Smith" value={form.name} onChange={e => setForm({...form, name: e.target.value})} onFocus={e => e.target.style.borderColor='#9666e3'} onBlur={e => e.target.style.borderColor=BORDER} />
                  </div>
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 600, color: FG3, letterSpacing: '0.05em', marginBottom: 6 }}>Email *</div>
                    <input style={inputStyle} placeholder="jane@firm.com" value={form.email} onChange={e => setForm({...form, email: e.target.value})} onFocus={e => e.target.style.borderColor='#9666e3'} onBlur={e => e.target.style.borderColor=BORDER} />
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 11, fontWeight: 600, color: FG3, letterSpacing: '0.05em', marginBottom: 6 }}>Company / Fund</div>
                  <input style={inputStyle} placeholder="Optional" value={form.company} onChange={e => setForm({...form, company: e.target.value})} onFocus={e => e.target.style.borderColor='#9666e3'} onBlur={e => e.target.style.borderColor=BORDER} />
                </div>
                <div>
                  <div style={{ fontSize: 11, fontWeight: 600, color: FG3, letterSpacing: '0.05em', marginBottom: 6 }}>Message *</div>
                  <textarea style={{ ...inputStyle, minHeight: 110, resize: 'vertical' }} placeholder="Tell us about your inquiry…" value={form.message} onChange={e => setForm({...form, message: e.target.value})} onFocus={e => e.target.style.borderColor='#9666e3'} onBlur={e => e.target.style.borderColor=BORDER} />
                </div>
                <button onClick={() => setSent(true)} style={{ background: GRAD, border: 'none', borderRadius: 9, padding: '14px', color: '#fff', fontFamily: 'Poppins', fontSize: 14, fontWeight: 600, cursor: 'pointer', width: '100%', boxShadow: '0 0 32px rgba(24,146,243,0.25)', transition: 'opacity 200ms' }}>
                  Send Message
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { ContactScreen });
