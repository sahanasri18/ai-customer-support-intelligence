import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../lib/api';
import { DashboardStats, Ticket } from '../types';
import {
  TicketIcon, AlertCircle, CheckCircle, Clock,
  TrendingUp, Loader, PlusCircle, Zap
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, CartesianGrid, Legend
} from 'recharts';

const COLORS = ['#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

function StatCard({ title, value, icon: Icon, color }: {
  title: string; value: number; icon: React.ElementType; color: string;
}) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 flex items-center gap-4">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${color}`}>
        <Icon size={22} className="text-white" />
      </div>
      <div>
        <div className="text-2xl font-bold text-gray-900">{value.toLocaleString()}</div>
        <div className="text-sm text-gray-500">{title}</div>
      </div>
    </div>
  );
}

function statusBadge(status: string) {
  const map: Record<string, string> = {
    open: 'bg-blue-100 text-blue-700',
    in_progress: 'bg-yellow-100 text-yellow-700',
    resolved: 'bg-green-100 text-green-700',
    closed: 'bg-gray-100 text-gray-700',
  };
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${map[status] || 'bg-gray-100 text-gray-700'}`}>
      {status.replace('_', ' ')}
    </span>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get<DashboardStats>('/api/analytics/dashboard')
      .then(r => setStats(r.data))
      .catch(() => setError('Failed to load dashboard data.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="flex items-center justify-center h-full">
      <Loader size={36} className="animate-spin text-indigo-500" />
    </div>
  );
  if (error) return <div className="p-4 md:p-8 text-red-600">{error}</div>;
  if (!stats) return null;

  const categoryData = Object.entries(stats.category_distribution).map(([name, value]) => ({ name, value }));
  const sentimentData = Object.entries(stats.sentiment_distribution).map(([name, value]) => ({ name, value }));
  const trendData = stats.tickets_last_7_days.map(d => ({ date: d.date.slice(5), count: d.count }));

  return (
    <div className="p-4 md:p-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 text-sm mt-0.5">Real-time support metrics from your database</p>
        </div>
        <Link
          to="/tickets/new"
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          <PlusCircle size={16} /> New Ticket
        </Link>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Total Tickets" value={stats.total_tickets} icon={TicketIcon} color="bg-indigo-500" />
        <StatCard title="Open" value={stats.open_tickets} icon={AlertCircle} color="bg-blue-500" />
        <StatCard title="In Progress" value={stats.in_progress_tickets} icon={Clock} color="bg-yellow-500" />
        <StatCard title="Resolved" value={stats.resolved_tickets} icon={CheckCircle} color="bg-green-500" />
        <StatCard title="Closed" value={stats.closed_tickets} icon={CheckCircle} color="bg-gray-400" />
        <StatCard title="High Priority" value={stats.high_priority_tickets} icon={TrendingUp} color="bg-orange-500" />
        <StatCard title="Urgent (rule-based)" value={stats.urgent_tickets} icon={Zap} color="bg-red-500" />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 7-day trend */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 col-span-1 lg:col-span-2">
          <h2 className="font-semibold text-gray-800 mb-4">Tickets Last 7 Days</h2>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} allowDecimals={false} />
              <Tooltip />
              <Line type="monotone" dataKey="count" stroke="#6366f1" strokeWidth={2} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Sentiment pie */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <h2 className="font-semibold text-gray-800 mb-4">Sentiment Distribution</h2>
          {sentimentData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={sentimentData} dataKey="value" nameKey="name" outerRadius={70} label={({ name, percent }) => `${name} ${(((percent ?? 0) * 100)).toFixed(0)}%`}>
                  {sentimentData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-48 text-gray-400 text-sm">
              Sentiment model unavailable: the selected dataset has no sentiment labels.
            </div>
          )}
        </div>
      </div>

      {/* Category bar + Recent tickets */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <h2 className="font-semibold text-gray-800 mb-4">Category Distribution</h2>
          {categoryData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={categoryData.slice(0, 10)} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis dataKey="name" type="category" width={120} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="value" fill="#6366f1" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-48 text-gray-400 text-sm">
              No category data yet
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <h2 className="font-semibold text-gray-800 mb-4">Recent Tickets</h2>
          {stats.recent_tickets.length === 0 ? (
            <p className="text-gray-400 text-sm">No tickets yet.</p>
          ) : (
            <div className="space-y-3">
              {stats.recent_tickets.slice(0, 7).map((t: Ticket) => (
                <Link
                  key={t.id} to={`/tickets/${t.id}`}
                  className="flex items-start justify-between p-3 rounded-lg hover:bg-gray-50 transition-colors gap-2"
                >
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-gray-800 truncate">{t.subject}</div>
                    <div className="text-xs text-gray-400 mt-0.5">{t.ticket_number}</div>
                  </div>
                  {statusBadge(t.status)}
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
