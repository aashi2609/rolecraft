"use client";

import React, { createContext, useContext, useState, ReactNode } from 'react';

type Role = 'candidate' | 'company' | null;

interface UserState {
  isAuthenticated: boolean;
  role: Role;
  profileComplete: boolean;
}

interface UserContextType extends UserState {
  login: (role: Role) => void;
  logout: () => void;
  setProfileComplete: (status: boolean) => void;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export function UserProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<UserState>({
    isAuthenticated: false,
    role: null,
    profileComplete: false,
  });

  const login = (role: Role) => setState({ isAuthenticated: true, role, profileComplete: false });
  const logout = () => setState({ isAuthenticated: false, role: null, profileComplete: false });
  const setProfileComplete = (status: boolean) => setState(prev => ({ ...prev, profileComplete: status }));

  return (
    <UserContext.Provider value={{ ...state, login, logout, setProfileComplete }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  const context = useContext(UserContext);
  if (context === undefined) {
    throw new Error('useUser must be used within a UserProvider');
  }
  return context;
}
