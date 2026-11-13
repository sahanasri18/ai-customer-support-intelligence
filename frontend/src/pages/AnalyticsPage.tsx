import React, { useEffect, useState } from 'react';
import api, { downloadTicketCsv } from '../lib/api';
import { DashboardStats } from '../types';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, CartesianGrid, Legend
} from 'recharts';
import { Loader, Download } from 'lucide-react';

const COLORS = ['#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

export default function AnalyticsPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [exportError, setExportError] = useState('');

  useEffect(() => {
    api.get<DashboardStats>('/api/analytics/dashboard')
      .then(r => setStats(r.data))
      .catch(() => setLoadError('Failed to load analytics. Check the API connection and try again.'))
      .finally(() => setLoading(false));
  }, []);

  const handleExport = async () => {
    setExportError('');
    try { await downloadTicketCsv(); }
    catch { setExportError('CSV export failed. Check the API connection and try again.'); }
  };

  if (loading) return <div className="flex items-center justify-center h-full"><Loader size={36} className="animate-spin text-indigo-400" /></div>;
  if (loadError) return <div className="p-4 md:p-8 text-red-600" role="alert">{loadError}</div>;
  if (!stats) return null;

  const categoryData = Object.entries(stats.category_distribution).map(([name, value]) => ({ name, value })).slice(0, 10);
  const predictedCategoryData = Object.entries(stats.predicted_category_distribution || {}).map(([name, value]) => ({ name, value })).slice(0, 10);
  const priorityData = Object.entries(stats.priority_distribution).map(([name, value]) => ({ name, value }));
  const sentimentData = Object.entries(stats.sentiment_distribution).map(([name, value]) => ({ name, value }));
  const statusData = Object.entries(stats.status_distribution).map(([name, value]) => ({ name: name.replace('_', ' '), value }));
  const trendData = stats.tickets_last_7_days.map(d => ({ date: d.date.slice(5), count: d.count }));

  return (
    <div className="p-4 md:p-8 space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
          <p className="text-sm text-gray-500 mt-0.5">All charts use live data from your database</p>
        </div>
        <button onClick={handleExport}
          className="flex items-center gap-2 border border-gray-300 text-gray-700 hover:bg-gray-50 px-4 py-2 rounded-lg text-sm font-medium">
          <Download size={16} /> Export CSV
        </button>
      </div>
      {exportError && <p role="alert" className="text-sm text-red-600">{exportError}</p>}

      {/* Volume trend */}
      <Section title="Ticket Volume — Last 7 Days">
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={trendData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} allowDecimals={false} />
            <Tooltip />
            <Line type="monotone" dataKey="count" stroke="#6366f1" strokeWidth={2} dot={{ r: 4 }} name="Tickets" />
          </LineChart>
        </ResponsiveContainer>
      </Section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Status */}
        <Section title="Status Distribution">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={statusData} dataKey="value" nameKey="name" outerRadius={80}
                label={({ name, percent }) => `${name} ${(((percent ?? 0) * 100)).toFixed(0)}%`}>
                {statusData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </Section>

        {/* Priority */}
        <Section title="Priority Distribution">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={priorityData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" fill="#06b6d4" radius={[4, 4, 0, 0]} name="Tickets" />
            </BarChart>
          </ResponsiveContainer>
        </Section>

        {/* Sentiment */}
        <Section title="Sentiment (ML Predictions)">
          {sentimentData.length === 0 ? (
            <p className="text-gray-400 text-sm py-8 text-center">Sentiment unavailable: the selected dataset has no sentiment labels.</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={sentimentData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="value" fill="#10b981" radius={[4, 4, 0, 0]} name="Tickets" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Section>

        {/* Category */}
        <Section title="Assigned Ticket Categories">
          {categoryData.length === 0 ? (
            <p className="text-gray-400 text-sm py-8 text-center">No category data yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={categoryData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis dataKey="name" type="category" width={130} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="value" fill="#8b5cf6" radius={[0, 4, 4, 0]} name="Tickets" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Section>

        <Section title="Predicted Categories (ML)">
          {predictedCategoryData.length === 0 ? (
            <p className="text-gray-400 text-sm py-8 text-center">No category predictions available yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={predictedCategoryData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis dataKey="name" type="category" width={130} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="value" fill="#6366f1" radius={[0, 4, 4, 0]} name="Predictions" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Section>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
      <h2 className="font-semibold text-gray-800 mb-4">{title}</h2>
      {children}
    </div>
  );
}
