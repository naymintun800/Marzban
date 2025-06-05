export interface MarzbanNode {
  id: number; // Backend uses integer IDs
  name: string;
  address: string;
  port: number;
  api_port: number;
  status: string;
  usage_coefficient: number;
}

export type ClientStrategyHint = 'url-test' | 'fallback' | 'load-balance' | 'client-default' | '';

export interface ResilientNodeGroup {
  id: number; // Backend uses integer IDs
  name: string;
  node_ids: number[]; // Array of MarzbanNode ids (integers)
  client_strategy_hint: ClientStrategyHint;
  nodes: MarzbanNode[]; // Full node details from backend
  created_at: string;
  updated_at: string;
}

export type NewResilientNodeGroup = Omit<ResilientNodeGroup, 'id' | 'nodes' | 'created_at' | 'updated_at'> & { id?: number };