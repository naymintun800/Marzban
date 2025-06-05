export interface MarzbanNode {
  id: string; // Or number, depending on backend
  name: string;
  address: string; // Assuming nodes have an address for display or selection logic
  port: number;    // Assuming nodes have a port
}

export type ClientStrategyHint = 'url-test' | 'fallback' | 'load-balance' | 'client-default' | '';

export interface ResilientNodeGroup {
  id: string; // Or number, depending on backend
  name: string;
  node_ids: string[]; // Array of MarzbanNode ids
  client_strategy_hint: ClientStrategyHint;
}

export type NewResilientNodeGroup = Omit<ResilientNodeGroup, 'id'> & { id?: string }; 