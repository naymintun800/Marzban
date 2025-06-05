import { useMutation, useQuery, useQueryClient } from 'react-query';
import { fetch } from '../service/http';
import { ResilientNodeGroup, NewResilientNodeGroup } from '../types/resilientNodeGroup';

const RESILIENT_NODE_GROUPS_QUERY_KEY = 'resilientNodeGroups';

// API Service Functions
const getResilientNodeGroups = async (): Promise<ResilientNodeGroup[]> => {
  return fetch('/api/resilient-node-groups');
};

const createResilientNodeGroup = async (groupData: NewResilientNodeGroup): Promise<ResilientNodeGroup> => {
  return fetch('/api/resilient-node-groups', { method: 'POST', body: groupData });
};

const updateResilientNodeGroup = async (groupData: ResilientNodeGroup): Promise<ResilientNodeGroup> => {
  return fetch(`/api/resilient-node-groups/${groupData.id}`, { method: 'PUT', body: groupData });
};

const deleteResilientNodeGroup = async (groupId: string): Promise<void> => {
  return fetch(`/api/resilient-node-groups/${groupId}`, { method: 'DELETE' });
};

// React Query Hooks
export const useResilientNodeGroupsQuery = () => {
  return useQuery<ResilientNodeGroup[], Error>(
    [RESILIENT_NODE_GROUPS_QUERY_KEY],
    getResilientNodeGroups
  );
};

export const useCreateResilientNodeGroupMutation = () => {
  const queryClient = useQueryClient();
  return useMutation<ResilientNodeGroup, Error, NewResilientNodeGroup>(
    createResilientNodeGroup,
    {
      onSuccess: () => {
        queryClient.invalidateQueries([RESILIENT_NODE_GROUPS_QUERY_KEY]);
      },
    }
  );
};

export const useUpdateResilientNodeGroupMutation = () => {
  const queryClient = useQueryClient();
  return useMutation<ResilientNodeGroup, Error, ResilientNodeGroup>(
    updateResilientNodeGroup,
    {
      onSuccess: (data: ResilientNodeGroup) => {
        queryClient.invalidateQueries([RESILIENT_NODE_GROUPS_QUERY_KEY]);
      },
    }
  );
};

export const useDeleteResilientNodeGroupMutation = () => {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>(deleteResilientNodeGroup, {
    onSuccess: () => {
      queryClient.invalidateQueries([RESILIENT_NODE_GROUPS_QUERY_KEY]);
    },
  });
}; 