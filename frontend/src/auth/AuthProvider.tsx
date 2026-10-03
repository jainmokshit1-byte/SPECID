import { type ReactNode, useCallback, useEffect, useState } from "react";
import { type LoginResponse, type Me, UNAUTHORIZED_EVENT, apiGet, apiPost } from "../api/client";
import { clearSession, getToken, setSession } from "./session";
import { AuthContext, type AuthStatus } from "./useAuth";

/** Signed-in user for the whole app (App Flow 4.2). Any 401 from the API signs out. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Me | null>(null);
  const [status, setStatus] = useState<AuthStatus>(() => (getToken() ? "loading" : "signed-out"));

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      setStatus("signed-out");
      return;
    }
    try {
      setUser(await apiGet<Me>("/me"));
      setStatus("signed-in");
    } catch {
      clearSession();
      setUser(null);
      setStatus("signed-out");
    }
  }, []);

  useEffect(() => {
    if (status === "loading") void refresh();
    // only on first mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const onUnauthorized = () => {
      setUser(null);
      setStatus("signed-out");
    };
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const r = await apiPost<LoginResponse>("/auth/login", { username, password });
    setSession({ token: r.access_token, expiresAt: r.expires_at });
    const me = await apiGet<Me>("/me");
    setUser(me);
    setStatus("signed-in");
    return me;
  }, []);

  const logout = useCallback(() => {
    clearSession();
    setUser(null);
    setStatus("signed-out");
  }, []);

  return (
    <AuthContext.Provider value={{ status, user, login, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}
