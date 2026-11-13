import React from 'react';
import { Download, FileText } from 'lucide-react';
import { downloadTicketCsv } from '../lib/api';

export default function ReportsPage() {
  const [error, setError] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const downloadCSV = async () => {
    setError(''); setLoading(true);
    try { await downloadTicketCsv(); }
    catch { setError('CSV export failed. Check the API connection and try again.'); }
    finally { setLoading(false); }
  };

  return (
    <div className="p-4 md:p-8 max-w-3xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
      <p className="text-gray-500 text-sm">Export your ticket data for offline analysis. All exports use live database records.</p>
      {error && <p role="alert" className="text-sm text-red-600">{error}</p>}

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 space-y-4">
        <div className="flex flex-col sm:flex-row items-start gap-4 p-4 border border-gray-100 rounded-lg">
          <FileText size={36} className="text-indigo-400 flex-shrink-0" />
          <div className="flex-1">
            <h3 className="font-medium text-gray-800">All Tickets Export</h3>
            <p className="text-sm text-gray-500 mt-1">
              Exports all tickets with subject, status, priority, category, customer info, urgency flag,
              and currently available model predictions as CSV (category only for this trained model).
            </p>
            <p className="text-xs text-gray-400 mt-2">
              Columns: ticket_number, subject, status, priority, category, customer_name, customer_email,
              is_urgent, created_at, predicted_category, predicted_sentiment, predicted_priority
            </p>
          </div>
          <button onClick={downloadCSV} disabled={loading}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium flex-shrink-0">
            <Download size={16} /> {loading ? 'Preparing…' : 'Download CSV'}
          </button>
        </div>
      </div>
    </div>
  );
}
