import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import type { TokenResponse } from "./types";

interface AuthState {
  token: string | null;
  userId: string | null;
  userName: string | null;
  baseUrl: string | null;
  isReady: boolean;
  login: (resp: TokenResponse) => void;
  logout: () => void;
  setBackend: (url: string) => void;
}

const AuthContext = createContext<AuthState>(null!);

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [userName, setUserName] = useState<string | null>(null);
  const [baseUrl, setBaseUrlState] = useState<string | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    setToken(localStorage.getItem("hermes_token"));
    setUserId(localStorage.getItem("hermes_user_id"));
    setUserName(localStorage.getItem("hermes_user_name"));
    setBaseUrlState(localStorage.getItem("hermes_base_url"));
    setIsReady(true);
  }, []);

  const login = useCallback((resp: TokenResponse) => {
    localStorage.setItem("hermes_token", resp.access_token);
    localStorage.setItem("hermes_user_id", resp.user_id);
    localStorage.setItem("hermes_user_name", resp.name);
    setToken(resp.access_token);
    setUserId(resp.user_id);
    setUserName(resp.name);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("hermes_token");
    localStorage.removeItem("hermes_user_id");
    localStorage.removeItem("hermes_user_name");
    setToken(null);
    setUserId(null);
    setUserName(null);
  }, []);

  const setBackend = useCallback((url: string) => {
    localStorage.setItem("hermes_base_url", url);
    setBaseUrlState(url);
  }, []);

  return (
    <AuthContext.Provider value={{ token, userId, userName, baseUrl, isReady, login, logout, setBackend }}>
      {children}
    </AuthContext.Provider>
  );
}
