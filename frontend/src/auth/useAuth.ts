import { createContext, useContext } from "react";
import type { Me } from "../api/client";

export type AuthStatus = "loading" | "signed-out" | "signed-in";

export interface AuthState {
  status: AuthStatus;
  user: Me | null;
  /** POST /auth/login, then GET /me. Throws ApiError (401, 429) on failure. */
  login: (username: string, password: string) => Promise<Me>;
  logout: () => void;
  /** Reload the user (after a password change). */
  refresh: () => Promise<void>;
}

export const AuthContext = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}

/** The signed-in user; only call inside RequireAuth. */
export function useUser(): Me {
  const { user } = useAuth();
  if (!user) throw new Error("useUser without a signed-in user");
  return user;
}
