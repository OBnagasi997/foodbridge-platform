import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, tokenStore, type User } from "../lib/api";
import type { RegisterValues } from "../lib/schemas";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (values: RegisterValues) => Promise<User>;
  logout: () => void;
  updateProfile: (changes: { phone?: string }) => Promise<User>;
}

const AuthContext = createContext<AuthState | null>(null);

interface TokenResponse {
  access_token: string;
  refresh_token: string;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(() => tokenStore.get() !== null);

  useEffect(() => {
    if (!tokenStore.get()) return;
    api<User>("/auth/me")
      .then(setUser)
      .catch(() => tokenStore.clear())
      .finally(() => setLoading(false));
  }, []);

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  useEffect(() => {
    window.addEventListener("foodbridge:logout", logout);
    return () => window.removeEventListener("foodbridge:logout", logout);
  }, [logout]);

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await api<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    tokenStore.set(tokens);
    const me = await api<User>("/auth/me");
    setUser(me);
    return me;
  }, []);

  const register = useCallback(
    async (values: RegisterValues) => {
      await api<User>("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          ...values,
          organization_name: values.organization_name || null,
        }),
      });
      return login(values.email, values.password);
    },
    [login],
  );

  const updateProfile = useCallback(async (changes: { phone?: string }) => {
    const me = await api<User>("/auth/me", { method: "PATCH", body: JSON.stringify(changes) });
    setUser(me);
    return me;
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, register, logout, updateProfile }),
    [user, loading, login, register, logout, updateProfile],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth doit être utilisé dans <AuthProvider>");
  return ctx;
}
