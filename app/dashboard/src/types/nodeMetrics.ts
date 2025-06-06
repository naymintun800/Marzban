export interface NodePerformanceOverview {
  total_groups: number;
  total_nodes: number;
  connected_nodes: number;
  nodes_in_groups: number;
  healthy_nodes: number;
  total_active_connections: number;
  avg_response_time: number | null;
  avg_success_rate: number | null;
}

export interface NodeMetrics {
  node_id: number;
  node_name: string;
  status: string;
  avg_response_time: number | null;
  success_rate: number | null;
  active_connections: number;
  total_connections: number;
  last_check: string | null;
  recent_checks?: number;
  performance_trend?: 'improving' | 'degrading' | 'stable' | 'insufficient_data';
}

export interface GroupPerformanceData {
  group_id: number;
  group_name: string;
  strategy: string;
  nodes: NodeMetrics[];
}

export interface NodePerformanceResponse {
  groups: GroupPerformanceData[];
  timestamp: string;
  period_hours: number;
}

export interface GroupMetricsResponse {
  group_id: number;
  group_name: string;
  strategy: string;
  total_nodes: number;
  connected_nodes: number;
  total_active_connections: number;
  nodes: NodeMetrics[];
  timestamp: string;
}
