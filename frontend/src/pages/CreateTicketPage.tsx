import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../lib/api';
import { Loader } from 'lucide-react';

export default function CreateTicketPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    subject: '', description: '', customer_name: '', customer_email: '',
    priority: '', category: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const payload: Record<string, any> = { subject: form.subject, description: form.description };
      if (form.customer_name) payload.customer_name = form.customer_name;
      if (form.customer_email) payload.customer_email = form.customer_email;
      if (form.priority) payload.priority = form.priority;
      if (form.category) payload.category = form.category;
      const { data } = await api.post('/api/tickets/', payload);
      navigate(`/tickets/${data.id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create ticket.');
    } finally {
      setLoading(false);
    }
  };

  const field = (label: string, key: string, type = 'text', required = false, placeholder = '') => (
    <div key={key}>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}{required && ' *'}</label>
      <input
        type={type} required={required} placeholder={placeholder}
        value={form[key as keyof typeof form]}
        onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
        className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
      />
    </div>
  );

  return (
    <div className="p-4 md:p-8 max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Create Ticket</h1>

      {error && <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 mb-4 text-sm">{error}</div>}

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 space-y-4">
        {field('Subject', 'subject', 'text', true, 'Brief description of the issue')}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Description *</label>
          <textarea
            required rows={5}
            value={form.description}
            onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
            className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
            placeholder="Detailed description of the customer's issue…"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          {field('Customer Name', 'customer_name', 'text', false, 'John Doe')}
          {field('Customer Email', 'customer_email', 'email', false, 'john@example.com')}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
            <select value={form.priority} onChange={e => setForm(f => ({ ...f, priority: e.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
              <option value="">Choose manually (optional)</option>
              {['low', 'medium', 'high', 'urgent'].map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
            <input
              type="text" placeholder="Leave blank to view the model prediction separately"
              value={form.category}
              onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>

        <div className="flex gap-3 pt-2">
          <button type="submit" disabled={loading}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-lg text-sm font-medium disabled:opacity-60">
            {loading && <Loader size={15} className="animate-spin" />}
            {loading ? 'Creating…' : 'Create Ticket'}
          </button>
          <button type="button" onClick={() => navigate(-1)}
            className="px-5 py-2.5 rounded-lg text-sm font-medium border border-gray-300 text-gray-700 hover:bg-gray-50">
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
