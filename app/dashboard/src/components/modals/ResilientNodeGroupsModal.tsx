import React from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  Button,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
  VStack,
  HStack,
  Text,
  Spinner,
  useToast,
  AlertDialog,
  AlertDialogBody,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogContent,
  AlertDialogOverlay,
  useDisclosure,
  Badge,
  Tooltip,
} from '@chakra-ui/react';
import { useDashboard } from '../../contexts/DashboardContext';
import { useResilientNodeGroupsQuery, useDeleteResilientNodeGroupMutation } from '../../hooks/useResilientNodeGroups';
import { ResilientNodeGroup } from '../../types/resilientNodeGroup';
import { NodePerformanceResponse } from '../../types/nodeMetrics';
import ResilientNodeGroupForm from '../forms/ResilientNodeGroupForm';
import { useQuery } from 'react-query';
import { fetch } from '../../service/http';

const ResilientNodeGroupsModal: React.FC = () => {
  const {
    isResilientNodeGroupsModalOpen,
    editingResilientNodeGroup,
    onCloseResilientNodeGroupsModal,
    onEditResilientNodeGroup,
    onAddNewResilientNodeGroup,
  } = useDashboard();

  const { data: resilientNodeGroups, isLoading: isLoadingGroups, error: fetchError } = useResilientNodeGroupsQuery();
  const { data: performanceData } = useQuery<NodePerformanceResponse>({
    queryKey: "node-performance-data",
    queryFn: () => fetch("/api/resilient-node-groups/metrics/performance"),
    refetchInterval: 30000, // Refresh every 30 seconds
    retry: 1,
  });
  const deleteMutation = useDeleteResilientNodeGroupMutation();
  const toast = useToast();
  const { isOpen: isDeleteOpen, onOpen: onDeleteOpen, onClose: onDeleteClose } = useDisclosure();
  const [deleteGroupId, setDeleteGroupId] = React.useState<number | null>(null);
  const cancelRef = React.useRef<HTMLButtonElement>(null);

  const handleDeleteClick = (groupId: number) => {
    setDeleteGroupId(groupId);
    onDeleteOpen();
  };

  const handleDeleteConfirm = () => {
    if (deleteGroupId) {
      deleteMutation.mutate(deleteGroupId, {
        onSuccess: () => {
          toast({
            title: 'Success',
            description: 'Resilient Node Group deleted successfully!',
            status: 'success',
            duration: 3000,
            isClosable: true,
          });
          onDeleteClose();
          setDeleteGroupId(null);
        },
        onError: (err: any) => {
          toast({
            title: 'Error',
            description: `Failed to delete group: ${err.message}`,
            status: 'error',
            duration: 5000,
            isClosable: true,
          });
          onDeleteClose();
          setDeleteGroupId(null);
        },
      });
    }
  };

  React.useEffect(() => {
    if (fetchError) {
      toast({
        title: 'Error',
        description: `Error fetching resilient node groups: ${fetchError.message}`,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  }, [fetchError, toast]);

  const showForm = !!editingResilientNodeGroup;

  // Helper function to get group performance data
  const getGroupPerformance = (groupId: number) => {
    return performanceData?.groups.find(g => g.group_id === groupId);
  };

  // Helper function to determine health status
  const getHealthStatus = (groupPerf: any) => {
    if (!groupPerf || !groupPerf.nodes.length) {
      return { color: "gray", text: "No Data", tooltip: "No performance data available" };
    }

    const connectedNodes = groupPerf.nodes.filter((n: any) => n.status === 'connected');
    const healthyNodes = connectedNodes.filter((n: any) =>
      n.success_rate === null || n.success_rate >= 80
    );

    if (connectedNodes.length === 0) {
      return { color: "red", text: "Offline", tooltip: "No connected nodes" };
    }

    const healthPercentage = (healthyNodes.length / connectedNodes.length) * 100;
    if (healthPercentage >= 80) {
      return {
        color: "green",
        text: "Healthy",
        tooltip: `${healthyNodes.length}/${connectedNodes.length} nodes healthy`
      };
    }
    if (healthPercentage >= 60) {
      return {
        color: "yellow",
        text: "Warning",
        tooltip: `${healthyNodes.length}/${connectedNodes.length} nodes healthy`
      };
    }
    return {
      color: "red",
      text: "Critical",
      tooltip: `${healthyNodes.length}/${connectedNodes.length} nodes healthy`
    };
  };

  return (
    <>
      <Modal isOpen={isResilientNodeGroupsModalOpen} onClose={onCloseResilientNodeGroupsModal} size="4xl">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>
            {showForm
              ? (editingResilientNodeGroup?.id ? 'Edit Resilient Node Group' : 'Add New Resilient Node Group')
              : 'Manage Resilient Node Groups'
            }
          </ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            {isLoadingGroups || deleteMutation.isLoading ? (
              <VStack spacing={4} py={8}>
                <Spinner size="lg" />
                <Text>Loading...</Text>
              </VStack>
            ) : showForm ? (
              <ResilientNodeGroupForm />
            ) : (
              <VStack spacing={4} align="stretch">
                <Button onClick={onAddNewResilientNodeGroup} colorScheme="blue" size="sm" alignSelf="flex-start">
                  Add New Resilient Node Group
                </Button>
                <TableContainer>
                  <Table variant="simple" size="sm">
                    <Thead>
                      <Tr>
                        <Th>Group Name</Th>
                        <Th>Nodes</Th>
                        <Th>Strategy</Th>
                        <Th>Health</Th>
                        <Th>Actions</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {resilientNodeGroups?.map((group) => {
                        const groupPerf = getGroupPerformance(group.id);
                        const healthStatus = getHealthStatus(groupPerf);
                        const connectedCount = groupPerf?.nodes.filter((n: any) => n.status === 'connected').length || 0;
                        const totalConnections = groupPerf?.nodes.reduce((sum: number, n: any) => sum + (n.active_connections || 0), 0) || 0;

                        return (
                          <Tr key={group.id}>
                            <Td>
                              <VStack align="start" spacing={1}>
                                <Text fontWeight="medium">{group.name}</Text>
                                {totalConnections > 0 && (
                                  <Text fontSize="xs" color="gray.500">
                                    {totalConnections} active connections
                                  </Text>
                                )}
                              </VStack>
                            </Td>
                            <Td>
                              <VStack align="start" spacing={1}>
                                <Text>{group.node_ids?.length || 0} total</Text>
                                {connectedCount > 0 && (
                                  <Text fontSize="xs" color="green.500">
                                    {connectedCount} connected
                                  </Text>
                                )}
                              </VStack>
                            </Td>
                            <Td>
                              <Badge variant="outline" fontSize="xs">
                                {group.client_strategy_hint}
                              </Badge>
                            </Td>
                            <Td>
                              <Tooltip label={healthStatus.tooltip}>
                                <Badge colorScheme={healthStatus.color} variant="subtle" fontSize="xs">
                                  {healthStatus.text}
                                </Badge>
                              </Tooltip>
                            </Td>
                            <Td>
                              <HStack spacing={2}>
                                <Button
                                  size="xs"
                                  variant="outline"
                                  onClick={() => onEditResilientNodeGroup(group)}
                                >
                                  Edit
                                </Button>
                                <Button
                                  size="xs"
                                  colorScheme="red"
                                  variant="outline"
                                  onClick={() => handleDeleteClick(group.id)}
                                >
                                  Delete
                                </Button>
                              </HStack>
                            </Td>
                          </Tr>
                        );
                      })}
                    </Tbody>
                  </Table>
                </TableContainer>
                {(!resilientNodeGroups || resilientNodeGroups.length === 0) && (
                  <Text textAlign="center" color="gray.500" py={8}>
                    No resilient node groups found. Create one to get started.
                  </Text>
                )}
              </VStack>
            )}
          </ModalBody>
        </ModalContent>
      </Modal>

      <AlertDialog
        isOpen={isDeleteOpen}
        leastDestructiveRef={cancelRef}
        onClose={onDeleteClose}
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              Delete Resilient Node Group
            </AlertDialogHeader>
            <AlertDialogBody>
              Are you sure you want to delete this group? This action cannot be undone.
            </AlertDialogBody>
            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={onDeleteClose}>
                Cancel
              </Button>
              <Button colorScheme="red" onClick={handleDeleteConfirm} ml={3} isLoading={deleteMutation.isLoading}>
                Delete
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </>
  );
};

export default ResilientNodeGroupsModal; 