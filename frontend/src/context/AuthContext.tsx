import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import api from '../lib/api';
import { User, Token } from '../types';

interface AuthContextValue {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isAdmin: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    const stored = localStorage.getItem('user');
    return stored ? JSON.parse(stored) : null;
  });
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('access_token'));

  const login = useCallback(async (email: string, password: string) => {
    const params = new URLSearchParams();
    params.append('username', email);
    params.append('password', password);
    const { data } = await api.post<Token>('/api/auth/login', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('user', JSON.stringify({
      id: data.user_id, email: data.email, full_name: data.full_name,
      role: data.role, is_active: true, created_at: new Date().toISOString(),
    }));
    setToken(data.access_token);
    setUser({ id: data.user_id, email: data.email, full_name: data.full_name, role: data.role, is_active: true, created_at: new Date().toISOString() });
  }, []);

  const logout = useCallback(() => {
    const existingToken = localStorage.getItem('access_token');
    if (existingToken) {
      void api.post('/api/auth/logout', {}, {
        headers: { Authorization: `Bearer ${existingToken}` },
      }).catch(() => undefined);
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    setUser(null);
    setToken(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, login, logout, isAdmin: user?.role === 'admin' }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be inside AuthProvider');
  return ctx;
}
