import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../lib/api';
import { Loader } from 'lucide-react';

export default function SettingsPage() {
  const { user } = useAuth();
  const [form, setForm] = useState({ current_password: '', new_password: '', confirm: '' });
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(false);

  const handlePwChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg(''); setErr('');
    if (form.new_password !== form.confirm) { setErr('Passwords do not match.'); return; }
    setLoading(true);
    try {
      await api.post('/api/users/me/change-password', {
        current_password: form.current_password,
        new_password: form.new_password,
      });
      setMsg('Password changed successfully.');
      setForm({ current_password: '', new_password: '', confirm: '' });
    } catch (e: any) {
      setErr(e.response?.data?.detail || 'Failed to change password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 md:p-8 max-w-xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Settings</h1>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 space-y-3">
        <h2 className="font-semibold text-gray-800">Profile</h2>
        <div className="text-sm text-gray-700"><span className="text-gray-400">Name: </span>{user?.full_name}</div>
        <div className="text-sm text-gray-700"><span className="text-gray-400">Email: </span>{user?.email}</div>
        <div className="text-sm text-gray-700"><span className="text-gray-400">Role: </span><span className="capitalize">{user?.role}</span></div>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
        <h2 className="font-semibold text-gray-800 mb-4">Change Password</h2>
        {msg && <div className="bg-green-50 border border-green-200 text-green-700 rounded px-3 py-2 text-sm mb-3">{msg}</div>}
        {err && <div className="bg-red-50 border border-red-200 text-red-700 rounded px-3 py-2 text-sm mb-3">{err}</div>}
        <form onSubmit={handlePwChange} className="space-y-3">
          {[
            { label: 'Current Password', key: 'current_password' },
            { label: 'New Password', key: 'new_password' },
            { label: 'Confirm New Password', key: 'confirm' },
          ].map(({ label, key }) => (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
              <input type="password" required minLength={key === 'new_password' || key === 'confirm' ? 12 : undefined}
                maxLength={key === 'new_password' || key === 'confirm' ? 128 : undefined}
                value={form[key as keyof typeof form]}
                onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
          ))}
          <button type="submit" disabled={loading}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-60">
            {loading && <Loader size={14} className="animate-spin" />} Change Password
          </button>
        </form>
      </div>
    </div>
  );
}
