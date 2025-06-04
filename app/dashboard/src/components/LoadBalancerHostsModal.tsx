import React from 'react';
import {
    Box,
    Heading,
    Button,
    Table,
    Thead,
    Tbody,
    Tr,
    Th,
    Td,
    TableContainer,
    Spinner,
    Alert,
    AlertIcon,
    AlertTitle,
    AlertDescription,
    IconButton,
    HStack,
    Tag,
    Text,
    Modal,
    ModalOverlay,
    ModalContent,
    ModalHeader,
    ModalFooter,
    ModalBody,
    ModalCloseButton,
} from '@chakra-ui/react';
import { AddIcon, EditIcon, DeleteIcon } from '@chakra-ui/icons';
import { useLoadBalancerHosts, useDeleteLoadBalancerHost } from '../hooks/useLoadBalancerHosts';
import { LoadBalancerHostResponse } from '../types/loadBalancer';
import { useDashboard } from '../contexts/DashboardContext';

interface LoadBalancerHostsModalProps {
    isOpen: boolean;
    onClose: () => void;
}

const LoadBalancerHostsModal: React.FC<LoadBalancerHostsModalProps> = ({ isOpen, onClose }) => {
    const { data: lbHosts, isLoading, error, refetch } = useLoadBalancerHosts();
    const deleteMutation = useDeleteLoadBalancerHost();
    const { onOpenLoadBalancerHostForm } = useDashboard();

    const handleDelete = (id: number) => {
        if (window.confirm('Are you sure you want to delete this load balancer host?')) {
            deleteMutation.mutate(id, {
                onSuccess: () => {
                    refetch();
                }
            });
        }
    };

    const handleAdd = () => {
        onOpenLoadBalancerHostForm('new');
    };

    const handleEdit = (lbHost: LoadBalancerHostResponse) => {
        onOpenLoadBalancerHostForm(lbHost);
    };

    return (
        <Modal isOpen={isOpen} onClose={onClose} size="4xl" scrollBehavior="inside">
            <ModalOverlay />
            <ModalContent>
                <ModalHeader>Load Balancer Hosts</ModalHeader>
                <ModalCloseButton />
                <ModalBody pb={6}>
                    <HStack justifyContent="space-between" mb={6}>
                        <Heading as="h2" size="md">
                            Manage Configurations
                        </Heading>
                        <Button
                            onClick={handleAdd}
                            leftIcon={<AddIcon />}
                            colorScheme="teal"
                        >
                            Add Load Balancer Host
                        </Button>
                    </HStack>

                    {isLoading && (
                        <Box display="flex" justifyContent="center" alignItems="center" height="200px">
                            <Spinner size="xl" />
                        </Box>
                    )}
                    {error && (
                        <Alert status="error" mt={4}>
                            <AlertIcon />
                            <AlertTitle>Error fetching load balancer hosts!</AlertTitle>
                            <AlertDescription>{error.message}</AlertDescription>
                            <Button onClick={() => refetch()} ml={4} mt={2} size="sm">
                                Retry
                            </Button>
                        </Alert>
                    )}
                    {!isLoading && !error && (
                        lbHosts && lbHosts.length > 0 ? (
                            <TableContainer>
                                <Table variant="simple" size="sm">
                                    <Thead>
                                        <Tr>
                                            <Th>Name</Th>
                                            <Th>Virtual Address</Th>
                                            <Th>Inbound Tag</Th>
                                            <Th>Strategy</Th>
                                            <Th>Nodes</Th>
                                            <Th>Status</Th>
                                            <Th>Actions</Th>
                                        </Tr>
                                    </Thead>
                                    <Tbody>
                                        {lbHosts.map((lbHost: LoadBalancerHostResponse) => (
                                            <Tr key={lbHost.id}>
                                                <Td>{lbHost.name}</Td>
                                                <Td>{lbHost.address}{lbHost.port ? `:${lbHost.port}` : ''}</Td>
                                                <Td><Tag size="sm">{lbHost.inbound_tag}</Tag></Td>
                                                <Td>{lbHost.load_balancing_strategy.replace('_', ' ').toUpperCase()}</Td>
                                                <Td>{lbHost.nodes.length}</Td>
                                                <Td>
                                                    <Tag size="sm" colorScheme={lbHost.is_disabled ? 'red' : 'green'}>
                                                        {lbHost.is_disabled ? 'Disabled' : 'Enabled'}
                                                    </Tag>
                                                </Td>
                                                <Td>
                                                    <HStack spacing={1}>
                                                        <IconButton
                                                            aria-label="Edit Load Balancer Host"
                                                            icon={<EditIcon />}
                                                            size="xs"
                                                            colorScheme="yellow"
                                                            onClick={() => handleEdit(lbHost)}
                                                        />
                                                        <IconButton
                                                            aria-label="Delete Load Balancer Host"
                                                            icon={<DeleteIcon />}
                                                            size="xs"
                                                            colorScheme="red"
                                                            onClick={() => handleDelete(lbHost.id)}
                                                            isLoading={deleteMutation.isLoading && deleteMutation.variables === lbHost.id}
                                                        />
                                                    </HStack>
                                                </Td>
                                            </Tr>
                                        ))}
                                    </Tbody>
                                </Table>
                            </TableContainer>
                        ) : (
                            <Text mt={4}>No load balancer hosts found. Click "Add Load Balancer Host" to create one.</Text>
                        )
                    )}
                </ModalBody>
                <ModalFooter>
                    <Button onClick={onClose}>Close</Button>
                </ModalFooter>
            </ModalContent>
        </Modal>
    );
};

export default LoadBalancerHostsModal; 