import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";

export function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!email || !password) { setError("Fill in all fields."); return; }
    setLoading(true);
    try {
      const resp = await api.login(email, password);
      login(resp);
      navigate("/");
    } catch (err: any) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <form onSubmit={handleSubmit} className="w-full max-w-md space-y-6">
        <h1 className="text-accent text-xl font-semibold tracking-wider">sign in</h1>

        <div className="space-y-4">
          <div className="space-y-1">
            <label className="text-[10px] uppercase tracking-widest text-muted">Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full bg-surface-2 border border-border rounded px-3 py-2.5 text-sm text-fg placeholder:text-zinc-600 focus:outline-none focus:border-accent/50" />
          </div>
          <div className="space-y-1">
            <label className="text-[10px] uppercase tracking-widest text-muted">Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full bg-surface-2 border border-border rounded px-3 py-2.5 text-sm text-fg placeholder:text-zinc-600 focus:outline-none focus:border-accent/50" />
          </div>
        </div>

        {error && <p className="text-red-400 text-xs">{error}</p>}

        <button type="submit" disabled={loading}
          className="w-full bg-accent text-surface-0 font-semibold text-sm py-2.5 rounded hover:bg-accent/90 disabled:opacity-40 transition-all">
          {loading ? "Signing in..." : "Sign In"}
        </button>

        <div className="flex justify-between text-xs">
          <Link to="/register" className="text-muted hover:text-accent transition-colors">Create account</Link>
          <Link to="/setup" className="text-muted hover:text-accent transition-colors">Change server</Link>
        </div>
      </form>
    </div>
  );
}
