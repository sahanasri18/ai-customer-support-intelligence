import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import api from '../lib/api';
import { PaginatedTickets } from '../types';
import { PlusCircle, Search, Loader, Ticket } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const statusColors: Record<string, string> = {
  open: 'bg-blue-100 text-blue-700',
  in_progress: 'bg-yellow-100 text-yellow-700',
  resolved: 'bg-green-100 text-green-700',
  closed: 'bg-gray-100 text-gray-600',
};
const priorityColors: Record<string, string> = {
  low: 'text-gray-500', medium: 'text-blue-600',
  high: 'text-orange-600', urgent: 'text-red-600 font-semibold',
};

export default function TicketsPage() {
  const { isAdmin } = useAuth();
  const [data, setData] = useState<PaginatedTickets | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [priority, setPriority] = useState('');
  const [page, setPage] = useState(1);
  const [error, setError] = useState('');

  const fetchTickets = useCallback(() => {
    setLoading(true);
    setError('');
    const params = new URLSearchParams({ page: String(page), page_size: '20' });
    if (search) params.set('search', search);
    if (status) params.set('status', status);
    if (priority) params.set('priority', priority);
    api.get<PaginatedTickets>(`/api/tickets/?${params}`)
      .then(r => setData(r.data))
      .catch(() => setError('Could not load tickets. Check the API connection and try again.'))
      .finally(() => setLoading(false));
  }, [page, search, status, priority]);

  useEffect(() => { fetchTickets(); }, [fetchTickets]);

  const handleDelete = async (id: number) => {
    if (!window.confirm('Delete this ticket?')) return;
    try {
      await api.delete(`/api/tickets/${id}`);
      fetchTickets();
    } catch {
      setError('Ticket could not be deleted. Admin access may be required.');
    }
  };

  return (
    <div className="p-4 md:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Tickets</h1>
        <Link to="/tickets/new" className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium">
          <PlusCircle size={16} /> New Ticket
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-48">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            className="w-full border border-gray-300 rounded-lg pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="Search tickets…" value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
          />
        </div>
        <select value={status} onChange={e => { setStatus(e.target.value); setPage(1); }}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
          <option value="">All Statuses</option>
          {['open', 'in_progress', 'resolved', 'closed'].map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
        </select>
        <select value={priority} onChange={e => { setPriority(e.target.value); setPage(1); }}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
          <option value="">All Priorities</option>
          {['low', 'medium', 'high', 'urgent'].map(p => <option key={p} value={p}>{p}</option>)}
        </select>
      </div>

      {/* Table */}
      {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-x-auto">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader size={28} className="animate-spin text-indigo-400" />
          </div>
        ) : !data || data.items.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-gray-400">
            <Ticket size={40} className="mb-3 opacity-30" />
            <p>No tickets found.</p>
            <Link to="/tickets/new" className="mt-4 text-indigo-600 hover:underline text-sm">Create your first ticket</Link>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                {['Ticket #', 'Subject', 'Status', 'Priority', 'Category', 'Urgent', 'Created', ''].map(h => (
                  <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {data.items.map(t => (
                <tr key={t.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{t.ticket_number}</td>
                  <td className="px-4 py-3">
                    <Link to={`/tickets/${t.id}`} className="font-medium text-gray-800 hover:text-indigo-600 line-clamp-1">{t.subject}</Link>
                    {t.customer_name && <div className="text-xs text-gray-400">{t.customer_name}</div>}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[t.status] || 'bg-gray-100 text-gray-600'}`}>
                      {t.status.replace('_', ' ')}
                    </span>
                  </td>
                  <td className={`px-4 py-3 text-xs capitalize ${priorityColors[t.priority || ''] || ''}`}>{t.priority || '—'}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{t.category || (t.predictions?.predicted_category ? `${t.predictions.predicted_category} (ML)` : '—')}</td>
                  <td className="px-4 py-3">{t.is_urgent && <span className="text-xs text-red-600 font-semibold">⚡ Urgent</span>}</td>
                  <td className="px-4 py-3 text-xs text-gray-400">{new Date(t.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3 flex gap-2">
                    <Link to={`/tickets/${t.id}`} className="text-indigo-600 hover:underline text-xs">View</Link>
                    {isAdmin && (
                      <button onClick={() => handleDelete(t.id)} className="text-red-500 hover:underline text-xs">Delete</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {data && data.total_pages > 1 && (
        <div className="flex justify-center gap-2">
          {Array.from({ length: data.total_pages }, (_, i) => i + 1).map(p => (
            <button key={p} onClick={() => setPage(p)}
              className={`px-3 py-1 rounded text-sm ${p === page ? 'bg-indigo-600 text-white' : 'border border-gray-300 text-gray-600 hover:bg-gray-50'}`}>
              {p}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
