import { useQuery } from 'react-query';
import { MarzbanNode } from '../types/resilientNodeGroup';
import { fetch } from '../service/http';

export const MARZBAN_NODES_QUERY_KEY = 'marzbanNodes';

// API Service Function for fetching nodes
const getMarzbanNodes = async (): Promise<MarzbanNode[]> => {
  return fetch('/api/nodes');
};

// React Query Hook
export const useMarzbanNodesQuery = () => {
  return useQuery<MarzbanNode[], Error>(
    [MARZBAN_NODES_QUERY_KEY],
    getMarzbanNodes
  );
}; 