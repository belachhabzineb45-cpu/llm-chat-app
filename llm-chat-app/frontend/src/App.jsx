import { useState, useRef, useEffect } from "react";
import { Send, LogOut, Sparkles, Lock, Mail, User, Eye, EyeOff, Trash2 } from "lucide-react";

const API = "http://localhost:8000/api";

const P = {
  mist: "#EDF2F0",
  ink: "#14302A",
  pine: "#0E5C4A",
  pineDeep: "#0A4438",
  amber: "#E8A33D",
  card: "#FFFFFF",
  muted: "#6C7F7A",
  border: "#DDE6E3",
};

export default function App() {
  const [session, setSession] = useState(() => {
    const saved = localStorage.getItem("session");
    return saved ? JSON.parse(saved) : null;
  });

  const login = (s) => {
    localStorage.setItem("session", JSON.stringify(s));
    setSession(s);
  };
  const logout = () => {
    localStorage.removeItem("session");
    setSession(null);
  };

  return session ? (
    <ChatScreen session={session} onLogout={logout} />
  ) : (
    <AuthScreen onLogin={login} />
  );
}

// ───────────── Écran de connexion ─────────────

function AuthScreen({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPwd, setShowPwd] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setError("");
    if (!email.trim() || !password) return setError("Renseignez l'e-mail et le mot de passe.");
    if (mode === "register" && !name.trim()) return setError("Renseignez votre nom.");
    setBusy(true);
    try {
      const res = await fetch(`${API}/${mode === "login" ? "login" : "register"}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(
          mode === "login"
            ? { email: email.trim(), password }
            : { name: name.trim(), email: email.trim(), password }
        ),
      });
      const data = await res.json();
if (!res.ok) {
  let message = "Erreur inconnue.";
  if (Array.isArray(data.detail)) {
    message = data.detail.map((e) => e.msg.replace("Value error, ", "")).join(" ");
  } else if (typeof data.detail === "string") {
    message = data.detail;
  }
  throw new Error(message);
}
onLogin({ token: data.token, name: data.name });
    } catch (err) {
      setError(
        err.message === "Failed to fetch"
          ? "Backend injoignable. Lancez-le : uvicorn main:app --reload --port 8000"
          : err.message
      );
    } finally {
      setBusy(false);
    }
  };

  const onKey = (e) => e.key === "Enter" && submit();

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", padding: 24, background: P.mist }}>
      <div style={{ width: "100%", maxWidth: 420 }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", marginBottom: 32 }}>
          <div
            style={{
              width: 64, height: 64, borderRadius: "50%", marginBottom: 16,
              background: `radial-gradient(circle at 35% 30%, ${P.amber}, ${P.pine} 65%, ${P.pineDeep})`,
              boxShadow: `0 8px 40px -8px ${P.pine}80`,
              animation: "pulse 2.5s ease-in-out infinite",
            }}
          />
          <style>{`@keyframes pulse { 0%,100% { transform: scale(1); } 50% { transform: scale(1.06); } }`}</style>
          <h1 style={{ fontSize: 30, fontWeight: 600, color: P.ink, fontFamily: "Georgia, serif" }}>Assistant IA</h1>
          <p style={{ fontSize: 14, marginTop: 4, color: P.muted }}>Votre espace de conversation, privé et personnel.</p>
        </div>

        <div style={{ background: P.card, borderRadius: 16, padding: 32, border: `1px solid ${P.border}`, boxShadow: "0 10px 30px -12px rgba(20,48,42,0.18)" }}>
          <div style={{ display: "flex", background: P.mist, borderRadius: 10, padding: 4, marginBottom: 24 }}>
            {[["login", "Se connecter"], ["register", "Créer un compte"]].map(([id, label]) => (
              <button
                key={id}
                onClick={() => { setMode(id); setError(""); }}
                style={{
                  flex: 1, padding: "8px 0", fontSize: 14, fontWeight: 500, borderRadius: 8,
                  background: mode === id ? P.card : "transparent",
                  color: mode === id ? P.ink : P.muted,
                  boxShadow: mode === id ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
                  transition: "all 0.15s",
                }}
              >
                {label}
              </button>
            ))}
          </div>

          {mode === "register" && (
            <Field icon={<User size={16} />} label="Nom">
              <input value={name} onChange={(e) => setName(e.target.value)} onKeyDown={onKey}
                placeholder="Votre prénom" style={inputStyle} />
            </Field>
          )}

          <Field icon={<Mail size={16} />} label="E-mail">
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} onKeyDown={onKey}
              placeholder="vous@exemple.com" style={inputStyle} />
          </Field>

          <Field icon={<Lock size={16} />} label="Mot de passe">
            <input type={showPwd ? "text" : "password"} value={password}
              onChange={(e) => setPassword(e.target.value)} onKeyDown={onKey}
              placeholder="••••••••" style={inputStyle} />
            <button onClick={() => setShowPwd(!showPwd)} style={{ background: "none", color: P.muted, display: "flex" }}>
              {showPwd ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </Field>

          {error && (
            <p style={{ fontSize: 13, marginBottom: 16, padding: "8px 12px", borderRadius: 10, background: "#FBEAE5", color: "#9A3B22" }}>
              {error}
            </p>
          )}

          <button
            onClick={submit}
            disabled={busy}
            style={{
              width: "100%", padding: "12px 0", borderRadius: 12, fontSize: 14, fontWeight: 600,
              color: "#fff", background: P.pine, opacity: busy ? 0.6 : 1,
            }}
          >
            {busy ? "…" : mode === "login" ? "Se connecter" : "Créer mon compte"}
          </button>
        </div>
      </div>
    </div>
  );
}

const inputStyle = { flex: 1, background: "transparent", outline: "none", fontSize: 14, color: P.ink };

function Field({ icon, label, children }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <label style={{ fontSize: 12, fontWeight: 500, display: "block", marginBottom: 6, color: P.muted }}>{label}</label>
      <div style={{ display: "flex", alignItems: "center", gap: 8, borderRadius: 12, padding: "10px 12px", background: P.mist, border: `1px solid ${P.border}` }}>
        <span style={{ color: P.muted, display: "flex" }}>{icon}</span>
        {children}
      </div>
    </div>
  );
}

// ───────────── Écran de chat ─────────────

function ChatScreen({ session, onLogout }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;
    const history = [...messages, { role: "user", content: text }];
    setMessages(history);
    setInput("");
    setLoading(true);
    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.token}`,
        },
        body: JSON.stringify({ messages: history }),
      });
      if (res.status === 401) {
        onLogout();
        return;
      }
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Erreur serveur.");
      setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: "assistant", content: `⚠️ ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: P.mist }}>
      <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 24px", background: P.card, borderBottom: `1px solid ${P.border}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 32, height: 32, borderRadius: "50%", background: `radial-gradient(circle at 35% 30%, ${P.amber}, ${P.pine} 65%, ${P.pineDeep})` }} />
          <div>
            <p style={{ fontSize: 14, fontWeight: 600, color: P.ink }}>Assistant IA</p>
            <p style={{ fontSize: 12, color: P.muted }}>Connecté : {session.name}</p>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <button onClick={() => setMessages([])} title="Effacer la conversation"
            style={{ padding: 8, borderRadius: 8, background: "none", color: P.muted, display: "flex" }}>
            <Trash2 size={18} />
          </button>
          <button onClick={onLogout}
            style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 14, padding: "8px 12px", borderRadius: 8, background: "none", color: P.muted }}>
            <LogOut size={16} /> Se déconnecter
          </button>
        </div>
      </header>

      <main style={{ flex: 1, overflowY: "auto", padding: "24px 16px" }}>
        <div style={{ maxWidth: 680, margin: "0 auto", display: "flex", flexDirection: "column", gap: 16 }}>
          {messages.length === 0 && (
            <div style={{ textAlign: "center", marginTop: 64 }}>
              <Sparkles size={28} style={{ color: P.pine, marginBottom: 12 }} />
              <p style={{ fontSize: 18, fontWeight: 500, color: P.ink, fontFamily: "Georgia, serif" }}>
                Bonjour {session.name} !
              </p>
              <p style={{ fontSize: 14, marginTop: 4, color: P.muted }}>
                Posez une question pour démarrer la conversation.
              </p>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} style={{ display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start" }}>
              <div
                style={{
                  maxWidth: 480, padding: "12px 16px", fontSize: 14, lineHeight: 1.6, whiteSpace: "pre-wrap",
                  borderRadius: 16,
                  ...(m.role === "user"
                    ? { background: P.pine, color: "#fff", borderBottomRightRadius: 6 }
                    : { background: P.card, color: P.ink, border: `1px solid ${P.border}`, borderBottomLeftRadius: 6 }),
                }}
              >
                {m.content}
              </div>
            </div>
          ))}

          {loading && (
            <div style={{ display: "flex" }}>
              <div style={{ padding: "12px 16px", borderRadius: 16, fontSize: 14, background: P.card, color: P.muted, border: `1px solid ${P.border}` }}>
                L'assistant réfléchit…
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </main>

      <footer style={{ padding: "0 16px 20px" }}>
        <div style={{ maxWidth: 680, margin: "0 auto", display: "flex", alignItems: "flex-end", gap: 8, borderRadius: 16, padding: 8, background: P.card, border: `1px solid ${P.border}`, boxShadow: "0 6px 20px -10px rgba(20,48,42,0.25)" }}>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            rows={1}
            placeholder="Écrivez votre message…  (Entrée pour envoyer)"
            style={{ flex: 1, background: "transparent", outline: "none", border: "none", resize: "none", fontSize: 14, padding: "8px 12px", color: P.ink, maxHeight: 120 }}
          />
          <button
            onClick={send}
            disabled={loading || !input.trim()}
            style={{ padding: 12, borderRadius: 12, color: "#fff", background: P.pine, opacity: loading || !input.trim() ? 0.4 : 1, display: "flex" }}
          >
            <Send size={16} />
          </button>
        </div>
      </footer>
    </div>
  );
}
