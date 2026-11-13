import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../lib/api';
import { PredictionModelStatus, Ticket } from '../types';
import { Loader, AlertCircle, Zap, ChevronDown } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const statusColors: Record<string, string> = {
  open: 'bg-blue-100 text-blue-700', in_progress: 'bg-yellow-100 text-yellow-700',
  resolved: 'bg-green-100 text-green-700', closed: 'bg-gray-100 text-gray-600',
};

export default function TicketDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAdmin } = useAuth();
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [updating, setUpdating] = useState(false);
  const [newStatus, setNewStatus] = useState('');
  const [comment, setComment] = useState('');
  const [repredicting, setRepredicting] = useState(false);
  const [predictionStatus, setPredictionStatus] = useState<PredictionModelStatus | null>(null);

  const load = () => {
    setLoading(true);
    api.get<Ticket>(`/api/tickets/${id}`)
      .then(r => { setTicket(r.data); setNewStatus(r.data.status); })
      .catch(() => setError('Ticket not found.'))
      .finally(() => setLoading(false));
  };
  useEffect(load, [id]);
  useEffect(() => {
    api.get<PredictionModelStatus>('/api/predictions/status')
      .then(r => setPredictionStatus(r.data))
      .catch(() => setPredictionStatus(null));
  }, []);

  const handleUpdate = async () => {
    if (!ticket) return;
    setUpdating(true);
    try {
      const { data } = await api.patch(`/api/tickets/${ticket.id}`, {
        status: newStatus,
        ...(comment ? { comment } : {}),
      });
      setTicket(data);
      setComment('');
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Update failed');
    } finally {
      setUpdating(false);
    }
  };

  const handleRepredict = async () => {
    if (!ticket) return;
    setRepredicting(true);
    try {
      const { data } = await api.post(`/api/tickets/${ticket.id}/predict`);
      setTicket(t => t ? { ...t, predictions: data } : t);
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Prediction failed');
    } finally {
      setRepredicting(false);
    }
  };

  if (loading) return <div className="flex items-center justify-center h-full"><Loader size={36} className="animate-spin text-indigo-400" /></div>;
  if (error) return <div className="p-4 md:p-8 text-red-600">{error}</div>;
  if (!ticket) return null;

  const pred = ticket.predictions;

  return (
    <div className="p-4 md:p-8 max-w-4xl space-y-6">
      <button onClick={() => navigate(-1)} className="text-sm text-indigo-600 hover:underline">← Back to tickets</button>

      {/* Header */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="text-xs font-mono text-gray-400 mb-1">{ticket.ticket_number}</div>
            <h1 className="text-xl font-bold text-gray-900">{ticket.subject}</h1>
            <div className={`mt-2 flex items-start gap-2 text-xs ${ticket.is_urgent ? 'text-red-700' : 'text-gray-500'}`}>
              <Zap size={13} className={ticket.is_urgent ? 'mt-0.5 text-red-600' : 'mt-0.5 text-gray-400'} />
              <span>
                <strong>{ticket.is_urgent ? 'Urgency rule matched' : 'No urgency rule matched'}</strong>
                {' — '}Keyword-based signal only. It can miss serious issues or flag ordinary wording; review urgency manually.
              </span>
            </div>
          </div>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusColors[ticket.status]}`}>
            {ticket.status.replace('_', ' ')}
          </span>
        </div>
        <p className="mt-4 text-gray-700 text-sm whitespace-pre-wrap">{ticket.description}</p>
        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <div><span className="text-gray-400 text-xs">Customer</span><div className="font-medium">{ticket.customer_name || '—'}</div></div>
          <div><span className="text-gray-400 text-xs">Email</span><div className="font-medium text-xs">{ticket.customer_email || '—'}</div></div>
          <div><span className="text-gray-400 text-xs">Priority</span><div className="font-medium capitalize">{ticket.priority || '—'}</div></div>
          <div><span className="text-gray-400 text-xs">Category</span><div className="font-medium">{ticket.category || '—'}</div></div>
        </div>
      </div>

      {/* ML Predictions */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-800">ML Predictions</h2>
          <button onClick={handleRepredict} disabled={repredicting}
            className="text-xs text-indigo-600 hover:underline disabled:opacity-50">
            {repredicting ? 'Running…' : 'Re-run Prediction'}
          </button>
        </div>
        <p className="mb-4 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
          Category is a suggestion. This model was trained on synthetic requests and performed substantially worse when entire request intents were held out. Confirm the category before routing.
        </p>
        {pred ? (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <PredBadge label="Predicted category" value={pred.predicted_category} confidence={pred.category_confidence} />
            {pred.predicted_priority && <PredBadge label="Predicted priority" value={pred.predicted_priority} confidence={pred.priority_confidence} />}
            {pred.predicted_sentiment && <PredBadge label="Predicted sentiment" value={pred.predicted_sentiment} confidence={pred.sentiment_confidence} />}
            <PredBadge label="Urgency (rule)" value={pred.is_urgent_rule_based ? 'Urgent signal' : 'No rule match'} confidence={null} />
            {predictionStatus && (
              <div className="col-span-full border-t border-gray-100 pt-3 text-xs text-gray-500 space-y-1">
                <div>Model version: {predictionStatus.model_version || 'none installed'}</div>
                <div>Category model: {predictionStatus.models.category.available ? 'available' : 'unavailable'}</div>
                <div>Priority model: {predictionStatus.models.priority.available ? 'available' : `unavailable — ${predictionStatus.models.priority.reason || 'no trained model'}`}</div>
                <div>Sentiment model: {predictionStatus.models.sentiment.available ? 'available' : `unavailable — ${predictionStatus.models.sentiment.reason || 'no trained model'}`}</div>
                <div>Urgency detection: keyword rules, not a learned probability.</div>
              </div>
            )}
            {pred.model_version && (
              <div className="col-span-full text-xs text-gray-400 mt-1">
                Model version: {pred.model_version} &nbsp;·&nbsp; Predicted at: {new Date(pred.predicted_at).toLocaleString()}
              </div>
            )}
          </div>
        ) : (
          <p className="text-gray-400 text-sm">No predictions yet. <button onClick={handleRepredict} className="text-indigo-600 hover:underline">Run now</button></p>
        )}
      </div>

      {/* Update status */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
        <h2 className="font-semibold text-gray-800 mb-4">Update Status</h2>
        <div className="flex gap-3 items-end flex-wrap">
          <div>
            <label className="block text-xs text-gray-500 mb-1">New Status</label>
            <select value={newStatus} onChange={e => setNewStatus(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
              {['open', 'in_progress', 'resolved', 'closed'].map(s =>
                <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
            </select>
          </div>
          <div className="flex-1 min-w-48">
            <label className="block text-xs text-gray-500 mb-1">Comment (optional)</label>
            <input value={comment} onChange={e => setComment(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Add a note about this status change" />
          </div>
          <button onClick={handleUpdate} disabled={updating}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-60 flex items-center gap-2">
            {updating && <Loader size={14} className="animate-spin" />} Save
          </button>
        </div>
      </div>

      {/* Status History */}
      {ticket.status_history.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
          <h2 className="font-semibold text-gray-800 mb-3">Status History</h2>
          <ol className="relative border-l border-gray-200 ml-3 space-y-4">
            {ticket.status_history.map(h => (
              <li key={h.id} className="pl-6">
                <span className="absolute left-0 w-3 h-3 bg-indigo-400 rounded-full -translate-x-1.5 mt-1" />
                <div className="text-sm text-gray-700">
                  <span className="font-medium">{(h.old_status || '—').replace('_', ' ')}</span>
                  {' → '}
                  <span className="font-medium">{h.new_status.replace('_', ' ')}</span>
                </div>
                {h.comment && <div className="text-xs text-gray-500 mt-0.5">"{h.comment}"</div>}
                <div className="text-xs text-gray-400 mt-0.5">{new Date(h.changed_at).toLocaleString()}</div>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

function PredBadge({ label, value, confidence }: { label: string; value: string | null; confidence: number | null }) {
  if (!value) return (
    <div className="bg-gray-50 rounded-lg p-3">
      <div className="text-xs text-gray-400">{label}</div>
      <div className="text-sm text-gray-400 italic mt-1">Not available</div>
    </div>
  );
  return (
    <div className="bg-indigo-50 rounded-lg p-3">
      <div className="text-xs text-indigo-400">{label}</div>
      <div className="text-sm font-semibold text-indigo-800 mt-1 capitalize">{value}</div>
      {confidence !== null && (
        <div className="text-xs text-indigo-400 mt-0.5">{(confidence * 100).toFixed(1)}% confidence</div>
      )}
    </div>
  );
}
