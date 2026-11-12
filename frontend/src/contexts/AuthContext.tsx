import React, { createContext, useContext, useState, useEffect } from 'react';
import { authApi } from '../services/api';

interface User {
  user_id: string;
  username: string;
  email?: string;
  role: string;
  full_name?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('access_token'));
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const storedToken = localStorage.getItem('access_token');
    if (storedToken) {
      authApi.me()
        .then((res) => {
          setUser(res.data);
          setToken(storedToken);
        })
        .catch(() => {
          localStorage.removeItem('access_token');
          localStorage.removeItem('user');
          setUser(null);
          setToken(null);
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = async (username: string, password: string) => {
    const res = await authApi.login(username, password);
    const data = res.data;
    if (!data?.access_token || !data?.user_id || !data?.username || !data?.role) {
      throw new Error('The server returned an incomplete login response.');
    }

    // Match the FastAPI TokenResponse fields returned by POST /api/auth/login.
    const userData: User = {
      user_id: data.user_id,
      username: data.username,
      role: data.role,
    };
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('user', JSON.stringify(userData));
    setToken(data.access_token);
    setUser(userData);
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, isAuthenticated: !!token, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
