import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard, Ticket, PlusCircle, BarChart2,
  Users, FileText, Settings, LogOut, Zap
} from 'lucide-react';

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/tickets', label: 'Tickets', icon: Ticket },
  { to: '/tickets/new', label: 'New Ticket', icon: PlusCircle },
  { to: '/analytics', label: 'Analytics', icon: BarChart2 },
  { to: '/reports', label: 'Reports', icon: FileText },
];
const adminItems = [
  { to: '/users', label: 'Users', icon: Users },
];
const bottomItems = [
  { to: '/settings', label: 'Settings', icon: Settings },
];

const linkBase = 'flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors';
const active   = 'bg-indigo-700 text-white';
const inactive = 'text-indigo-100 hover:bg-indigo-700/50';

export default function Sidebar() {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => { logout(); navigate('/login'); };

  return (
    <aside className="w-16 md:w-64 shrink-0 bg-indigo-900 flex flex-col h-screen">
      {/* Logo */}
      <div className="flex items-center justify-center md:justify-start gap-2 px-2 md:px-6 py-5 border-b border-indigo-800">
        <Zap className="text-indigo-300" size={24} />
        <span className="hidden md:block text-white font-bold text-sm leading-tight">
          Support<br />Intelligence
        </span>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to} to={to}
            title={label} aria-label={label}
            className={({ isActive }) => `${linkBase} justify-center md:justify-start px-2 md:px-4 ${isActive ? active : inactive}`}
          >
            <Icon size={18} /><span className="hidden md:inline">{label}</span>
          </NavLink>
        ))}

        {isAdmin && (
          <>
            <div className="hidden md:block px-4 pt-4 pb-1 text-xs font-semibold text-indigo-400 uppercase tracking-wider">
              Admin
            </div>
            {adminItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to} to={to}
                title={label} aria-label={label}
                className={({ isActive }) => `${linkBase} justify-center md:justify-start px-2 md:px-4 ${isActive ? active : inactive}`}
              >
                <Icon size={18} /><span className="hidden md:inline">{label}</span>
              </NavLink>
            ))}
          </>
        )}

        <div className="hidden md:block px-4 pt-4 pb-1 text-xs font-semibold text-indigo-400 uppercase tracking-wider">
          Account
        </div>
        {bottomItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to} to={to}
            title={label} aria-label={label}
            className={({ isActive }) => `${linkBase} justify-center md:justify-start px-2 md:px-4 ${isActive ? active : inactive}`}
          >
            <Icon size={18} /><span className="hidden md:inline">{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* User info */}
      <div className="px-1 md:px-4 py-4 border-t border-indigo-800">
        <div className="hidden md:block text-white text-sm font-medium truncate">{user?.full_name}</div>
        <div className="hidden md:block text-indigo-300 text-xs truncate">{user?.email}</div>
        <div className="hidden md:block text-indigo-400 text-xs capitalize mt-0.5">{user?.role}</div>
        <button
          onClick={handleLogout}
          title="Sign out" aria-label="Sign out"
          className="mt-1 md:mt-3 mx-auto md:mx-0 flex items-center justify-center md:justify-start gap-2 text-indigo-300 hover:text-white text-xs transition-colors"
        >
          <LogOut size={14} /><span className="hidden md:inline">Sign out</span>
        </button>
      </div>
    </aside>
  );
}
