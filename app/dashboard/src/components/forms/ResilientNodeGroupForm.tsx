import React, { useEffect, useState } from 'react';
import {
  VStack,
  FormControl,
  FormLabel,
  Input,
  Select,
  Button,
  Spinner,
  useToast,
  CheckboxGroup,
  Checkbox,
  SimpleGrid,
  Text,
  HStack,
  FormErrorMessage,
} from '@chakra-ui/react';
import { useDashboard } from '../../contexts/DashboardContext';
import {
  useCreateResilientNodeGroupMutation,
  useUpdateResilientNodeGroupMutation,
} from '../../hooks/useResilientNodeGroups';
import { useMarzbanNodesQuery } from '../../hooks/useMarzbanNodes';
import { NewResilientNodeGroup, ResilientNodeGroup, ClientStrategyHint } from '../../types/resilientNodeGroup';

const clientStrategyOptions: { label: string; value: ClientStrategyHint }[] = [
  { label: 'Client Default/Random', value: 'client-default' },
  { label: 'URL-Test (Clash/Sing-box)', value: 'url-test' },
  { label: 'Fallback (Clash/Sing-box)', value: 'fallback' },
  { label: 'Load Balance (Clash/Sing-box)', value: 'load-balance' },
  { label: 'Not Set', value: '' },
];

const ResilientNodeGroupForm: React.FC = () => {
  const {
    editingResilientNodeGroup,
    onCloseResilientNodeGroupsModal,
  } = useDashboard();

  const { data: marzbanNodes, isLoading: isLoadingNodes, error: nodesError } = useMarzbanNodesQuery();
  const toast = useToast();

  // Form state
  const [name, setName] = useState('');
  const [selectedNodeIds, setSelectedNodeIds] = useState<number[]>([]);
  const [clientStrategyHint, setClientStrategyHint] = useState<ClientStrategyHint>('client-default');
  const [errors, setErrors] = useState<{[key: string]: string}>({});

  useEffect(() => {
    if (editingResilientNodeGroup) {
      setName(editingResilientNodeGroup.name || '');
      setSelectedNodeIds(editingResilientNodeGroup.node_ids || []);
      setClientStrategyHint(editingResilientNodeGroup.client_strategy_hint || 'client-default');
    } else {
      setName('');
      setSelectedNodeIds([]);
      setClientStrategyHint('client-default');
    }
    setErrors({});
  }, [editingResilientNodeGroup]);
  
  const createMutation = useCreateResilientNodeGroupMutation();
  const updateMutation = useUpdateResilientNodeGroupMutation();

  // Type guard to check if we're editing an existing group
  const isEditingExistingGroup = (group: any): group is ResilientNodeGroup => {
    return group && typeof group.id === 'number' && 'nodes' in group && 'created_at' in group;
  };

  const isEditing = editingResilientNodeGroup && isEditingExistingGroup(editingResilientNodeGroup);
  const mutationLoading = createMutation.isLoading || updateMutation.isLoading;

  const validateForm = () => {
    const newErrors: {[key: string]: string} = {};

    if (!name.trim()) {
      newErrors.name = 'Please input the group name!';
    }

    if (selectedNodeIds.length === 0) {
      newErrors.node_ids = 'Please select at least one node!';
    }

    if (!clientStrategyHint) {
      newErrors.client_strategy_hint = 'Please select a strategy hint!';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = () => {
    if (!validateForm()) return;

    const onSuccess = () => {
      toast({
        title: 'Success',
        description: `Resilient Node Group ${isEditing ? 'updated' : 'created'} successfully!`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      onCloseResilientNodeGroupsModal();
    };

    const onError = (err: any) => {
      toast({
        title: 'Error',
        description: `Failed to ${isEditing ? 'update' : 'create'} group: ${err.message}`,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    };

    if (isEditing) {
      const existingGroup = editingResilientNodeGroup as ResilientNodeGroup;
      const groupData: ResilientNodeGroup = {
        ...existingGroup,
        name: name.trim(),
        node_ids: selectedNodeIds,
        client_strategy_hint: clientStrategyHint,
      };
      updateMutation.mutate(groupData, { onSuccess, onError });
    } else {
      const groupData: NewResilientNodeGroup = {
        name: name.trim(),
        node_ids: selectedNodeIds,
        client_strategy_hint: clientStrategyHint,
      };
      createMutation.mutate(groupData, { onSuccess, onError });
    }
  };

  useEffect(() => {
    if (nodesError) {
      toast({
        title: 'Error',
        description: `Error fetching nodes: ${nodesError.message}`,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  }, [nodesError, toast]);

  if (isLoadingNodes && !marzbanNodes) {
    return (
      <VStack spacing={4} py={8}>
        <Spinner size="lg" />
        <Text>Loading node data...</Text>
      </VStack>
    );
  }

  return (
    <VStack spacing={6} align="stretch">
      <FormControl isInvalid={!!errors.name}>
        <FormLabel>Group Name</FormLabel>
        <Input
          placeholder="My Resilient Group"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={mutationLoading}
        />
        <FormErrorMessage>{errors.name}</FormErrorMessage>
      </FormControl>

      <FormControl isInvalid={!!errors.node_ids}>
        <FormLabel>Select Nodes</FormLabel>
        {isLoadingNodes ? (
          <HStack>
            <Spinner size="sm" />
            <Text>Loading nodes...</Text>
          </HStack>
        ) : (
          <CheckboxGroup
            value={selectedNodeIds.map(String)}
            onChange={(values) => setSelectedNodeIds(values.map(Number))}
          >
            <SimpleGrid columns={2} spacing={2}>
              {marzbanNodes?.map((node) => (
                <Checkbox key={node.id} value={String(node.id)} isDisabled={mutationLoading}>
                  {node.name}
                </Checkbox>
              ))}
            </SimpleGrid>
          </CheckboxGroup>
        )}
        <FormErrorMessage>{errors.node_ids}</FormErrorMessage>
      </FormControl>

      <FormControl isInvalid={!!errors.client_strategy_hint}>
        <FormLabel>Client-Side Strategy Hint</FormLabel>
        <Select
          placeholder="Select a strategy"
          value={clientStrategyHint}
          onChange={(e) => setClientStrategyHint(e.target.value as ClientStrategyHint)}
          disabled={mutationLoading}
        >
          {clientStrategyOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </Select>
        <FormErrorMessage>{errors.client_strategy_hint}</FormErrorMessage>
      </FormControl>

      <HStack spacing={3} justify="flex-end" pt={4}>
        <Button
          variant="outline"
          onClick={onCloseResilientNodeGroupsModal}
          isDisabled={mutationLoading}
        >
          Cancel
        </Button>
        <Button
          colorScheme="blue"
          onClick={handleSubmit}
          isLoading={mutationLoading}
          loadingText={isEditing ? 'Saving...' : 'Creating...'}
        >
          {isEditing ? 'Save Changes' : 'Create Group'}
        </Button>
      </HStack>
    </VStack>
  );
};

export default ResilientNodeGroupForm; 