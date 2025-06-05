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
} from '@chakra-ui/react';
import { useDashboard } from '../../contexts/DashboardContext';
import { useResilientNodeGroupsQuery, useDeleteResilientNodeGroupMutation } from '../../hooks/useResilientNodeGroups';
import { ResilientNodeGroup } from '../../types/resilientNodeGroup';
import ResilientNodeGroupForm from '../forms/ResilientNodeGroupForm';

const ResilientNodeGroupsModal: React.FC = () => {
  const {
    isResilientNodeGroupsModalOpen,
    editingResilientNodeGroup,
    onCloseResilientNodeGroupsModal,
    onEditResilientNodeGroup,
    onAddNewResilientNodeGroup,
  } = useDashboard();

  const { data: resilientNodeGroups, isLoading: isLoadingGroups, error: fetchError } = useResilientNodeGroupsQuery();
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
                        <Th>Number of Nodes</Th>
                        <Th>Client Strategy Hint</Th>
                        <Th>Actions</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {resilientNodeGroups?.map((group) => (
                        <Tr key={group.id}>
                          <Td>{group.name}</Td>
                          <Td>{group.node_ids?.length || 0}</Td>
                          <Td>{group.client_strategy_hint}</Td>
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
                      ))}
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