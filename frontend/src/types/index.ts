export interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'admin' | 'agent';
  is_active: boolean;
  created_at: string;
}

export interface Token {
  access_token: string;
  token_type: string;
  user_id: number;
  email: string;
  full_name: string;
  role: 'admin' | 'agent';
}

export type TicketStatus = 'open' | 'in_progress' | 'resolved' | 'closed';
export type Priority = 'low' | 'medium' | 'high' | 'urgent';
export type Sentiment = 'positive' | 'neutral' | 'negative';

export interface Prediction {
  predicted_category: string | null;
  category_confidence: number | null;
  predicted_priority: string | null;
  priority_confidence: number | null;
  predicted_sentiment: Sentiment | null;
  sentiment_confidence: number | null;
  is_urgent_rule_based: boolean;
  model_version: string | null;
  predicted_at: string;
}

export interface PredictionTaskStatus {
  available: boolean;
  confidence_available: boolean;
  reason: string | null;
}

export interface PredictionModelStatus {
  model_version: string | null;
  trained_at_utc: string | null;
  source_dataset: string | null;
  models: {
    category: PredictionTaskStatus;
    priority: PredictionTaskStatus;
    sentiment: PredictionTaskStatus;
  };
  urgent_detection: {
    available: boolean;
    method: string;
    confidence_available: boolean;
  };
}

export interface StatusHistory {
  id: number;
  old_status: TicketStatus | null;
  new_status: TicketStatus;
  comment: string | null;
  changed_at: string;
  changed_by: number;
}

export interface Ticket {
  id: number;
  ticket_number: string;
  subject: string;
  description: string;
  status: TicketStatus;
  priority: Priority | null;
  category: string | null;
  customer_name: string | null;
  customer_email: string | null;
  created_by: number;
  assigned_to: number | null;
  is_urgent: boolean;
  created_at: string;
  updated_at: string | null;
  resolved_at: string | null;
  predictions: Prediction | null;
  status_history: StatusHistory[];
}

export interface PaginatedTickets {
  items: Ticket[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DashboardStats {
  total_tickets: number;
  open_tickets: number;
  in_progress_tickets: number;
  resolved_tickets: number;
  closed_tickets: number;
  high_priority_tickets: number;
  urgent_tickets: number;
  category_distribution: Record<string, number>;
  predicted_category_distribution: Record<string, number>;
  priority_distribution: Record<string, number>;
  sentiment_distribution: Record<string, number>;
  status_distribution: Record<string, number>;
  recent_tickets: Ticket[];
  tickets_last_7_days: Array<{ date: string; count: number }>;
}
