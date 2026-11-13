import React, { useEffect, useState } from 'react';
import api from '../lib/api';
import { User } from '../types';
import { Loader, Users } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function UsersPage() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = () => {
    api.get<User[]>('/api/users/')
      .then(r => setUsers(r.data))
      .catch(() => setError('Could not load users. Check your administrator access and API connection.'))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const toggleActive = async (u: User) => {
    setError('');
    try { await api.patch(`/api/users/${u.id}`, { is_active: !u.is_active }); load(); }
    catch { setError('Could not update account status.'); }
  };

  const changeRole = async (u: User, role: 'admin' | 'agent') => {
    setError('');
    try { await api.patch(`/api/users/${u.id}`, { role }); load(); }
    catch { setError('Could not update user role.'); }
  };

  if (loading) return <div className="flex items-center justify-center h-full"><Loader size={36} className="animate-spin text-indigo-400" /></div>;

  return (
    <div className="p-4 md:p-8 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">User Management</h1>
      <p className="text-sm text-gray-500">Admin-only: manage agents and their permissions.</p>
      {error && <p role="alert" className="text-sm text-red-600">{error}</p>}

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-x-auto">
        {users.length === 0 ? (
          <div className="flex flex-col items-center py-20 text-gray-400">
            <Users size={40} className="mb-3 opacity-30" />
            <p>No users found.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                {['Name', 'Email', 'Role', 'Status', 'Joined', 'Actions'].map(h => (
                  <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {users.map(u => (
                <tr key={u.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-800">{u.full_name}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{u.email}</td>
                  <td className="px-4 py-3">
                    <select value={u.role} disabled={u.id === currentUser?.id} onChange={e => changeRole(u, e.target.value as 'admin' | 'agent')}
                      className="border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500">
                      <option value="agent">Agent</option>
                      <option value="admin">Admin</option>
                    </select>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${u.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-600'}`}>
                      {u.is_active ? 'Active' : 'Disabled'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-400">{new Date(u.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => toggleActive(u)} disabled={u.id === currentUser?.id}
                      className={`text-xs hover:underline disabled:opacity-40 ${u.is_active ? 'text-red-500' : 'text-green-600'}`}>
                      {u.is_active ? 'Disable' : 'Enable'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
