// SWERVE — Sign Up / Onboarding Screen
function SignUpScreen({ onSwitch }) {
  const [email, setEmail] = React.useState('');
  const [pass, setPass]   = React.useState('');
  const [step, setStep]   = React.useState(0); // 0=form, 1=success

  const inputStyle = { background: BG_ELEVATED, border: `1px solid ${BORDER}`, borderRadius: 9, color: FG1, fontFamily: 'Poppins', fontSize: 14, padding: '12px 16px', outline: 'none', width: '100%', boxSizing: 'border-box', transition: 'border-color 200ms, box-shadow 200ms' };

  const focusStyle = { borderColor: '#9666e3', boxShadow: '0 0 0 3px rgba(150,102,227,0.15)' };
  const blurStyle  = { borderColor: BORDER, boxShadow: 'none' };

  if (step === 1) return (
    <div style={{ minHeight: '100vh', background: BG, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'Poppins' }}>
      <div style={{ textAlign: 'center', maxWidth: 380 }}>
        <div style={{ width: 64, height: 64, borderRadius: '50%', background: GRAD, display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 24px', fontSize: 26 }}>
          <svg width="28" height="22" viewBox="0 0 28 22" fill="none"><path d="M2 11l8 8L26 2" stroke="#fff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/></svg>
        </div>
        <div style={{ fontSize: 24, fontWeight: 700, color: FG1, marginBottom: 10 }}>You're in.</div>
        <div style={{ fontSize: 14, color: FG2, marginBottom: 28, lineHeight: 1.65 }}>Your SWERVE account is ready. Start exploring institutional research for emerging markets.</div>
        <Btn size="lg" onClick={() => setStep(0)}>Go to Dashboard →</Btn>
      </div>
    </div>
  );

  return (
    <div style={{ minHeight: '100vh', background: BG, display: 'flex', fontFamily: 'Poppins' }}>
      {/* Left — gradient visual */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', padding: 48 }}>
        <div style={{ position: 'absolute', inset: 0, background: GRAD_DARK, opacity: 0.9 }} />
        <div style={{ position: 'absolute', right: -40, top: '50%', transform: 'translateY(-50%)', opacity: 0.12 }}>
          <img src="../../assets/logo-mark-dark.png" width="420" alt="" />
        </div>
        <div style={{ position: 'relative' }}>
          <img src="../../assets/logo-secondary-white.png" height="28" alt="SWERVE" />
        </div>
        <div style={{ position: 'relative' }}>
          <div style={{ fontSize: 11, fontWeight: 500, color: 'rgba(255,255,255,0.5)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 12 }}>Institutional Research</div>
          <div style={{ fontSize: 32, fontWeight: 700, color: '#fff', letterSpacing: '-0.03em', lineHeight: 1.15, marginBottom: 16 }}>Finance, redesigned<br />for how you think.</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {['Emerging markets coverage across 40+ countries', 'Real-time data integrated with deep research', 'Built for analysts, PMs, and institutions'].map((t, i) => (
              <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'center', fontSize: 13, color: 'rgba(255,255,255,0.72)' }}>
                <div style={{ width: 5, height: 5, borderRadius: '50%', background: '#e3cfff', flexShrink: 0 }} />{t}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right — form */}
      <div style={{ width: 460, background: BG_SURFACE, display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '64px 52px', borderLeft: `1px solid ${BORDER}` }}>
        <div style={{ fontSize: 26, fontWeight: 700, color: FG1, letterSpacing: '-0.02em', marginBottom: 6 }}>Create an account</div>
        <div style={{ fontSize: 13, color: FG3, marginBottom: 32 }}>Start free — no credit card required.</div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, color: FG3, letterSpacing: '0.05em', textTransform: 'uppercase', marginBottom: 7 }}>Work Email</div>
            <input style={inputStyle} type="email" placeholder="you@firm.com" value={email} onChange={e => setEmail(e.target.value)} onFocus={e => Object.assign(e.target.style, focusStyle)} onBlur={e => Object.assign(e.target.style, blurStyle)} />
          </div>
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, color: FG3, letterSpacing: '0.05em', textTransform: 'uppercase', marginBottom: 7 }}>Password</div>
            <input style={inputStyle} type="password" placeholder="At least 8 characters" value={pass} onChange={e => setPass(e.target.value)} onFocus={e => Object.assign(e.target.style, focusStyle)} onBlur={e => Object.assign(e.target.style, blurStyle)} />
          </div>
          <div style={{ marginTop: 6 }}>
            <Btn style={{ width: '100%', display: 'flex', justifyContent: 'center' }} onClick={() => setStep(1)}>Create Account →</Btn>
          </div>
        </div>

        <div style={{ marginTop: 28, fontSize: 12, color: FG3, textAlign: 'center' }}>
          Already have an account?{' '}
          <button onClick={onSwitch} style={{ background: 'none', border: 'none', color: '#9666e3', fontFamily: 'Poppins', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>Sign in</button>
        </div>

        <div style={{ marginTop: 32, paddingTop: 20, borderTop: `1px solid ${BORDER}`, fontSize: 11, color: FG3, lineHeight: 1.6 }}>
          By creating an account you agree to our <span style={{ color: '#9666e3', cursor: 'pointer' }}>Terms of Service</span> and <span style={{ color: '#9666e3', cursor: 'pointer' }}>Privacy Policy</span>.
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { SignUpScreen });
