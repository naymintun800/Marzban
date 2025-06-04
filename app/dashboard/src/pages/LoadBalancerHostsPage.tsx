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
} from '@chakra-ui/react';
import { AddIcon, EditIcon, DeleteIcon } from '@chakra-ui/icons';
import { useLoadBalancerHosts, useDeleteLoadBalancerHost } from '../../hooks/useLoadBalancerHosts'; // Adjust path if hooks are elsewhere
import { LoadBalancerHostResponse } from '../../types/loadBalancer'; // Adjust path if types are elsewhere
import { Link as RouterLink } from 'react-router-dom'; // Assuming you use React Router for navigation

const LoadBalancerHostsPage: React.FC = () => {
    const { data: lbHosts, isLoading, error, refetch } = useLoadBalancerHosts();
    const deleteMutation = useDeleteLoadBalancerHost();

    const handleDelete = (id: number) => {
        if (window.confirm('Are you sure you want to delete this load balancer host?')) {
            deleteMutation.mutate(id);
        }
    };

    if (isLoading) {
        return (
            <Box display="flex" justifyContent="center" alignItems="center" height="200px">
                <Spinner size="xl" />
            </Box>
        );
    }

    if (error) {
        return (
            <Alert status="error">
                <AlertIcon />
                <AlertTitle>Error fetching load balancer hosts!</AlertTitle>
                <AlertDescription>{error.message}</AlertDescription>
                <Button onClick={() => refetch()} ml={4}>
                    Retry
                </Button>
            </Alert>
        );
    }

    return (
        <Box p={5}>
            <HStack justifyContent="space-between" mb={6}>
                <Heading as="h1" size="lg">
                    Load Balancer Hosts
                </Heading>
                <Button
                    as={RouterLink}
                    to="/load-balancer-hosts/new" // Define this route later for creating new LB
                    leftIcon={<AddIcon />}
                    colorScheme="teal" // Or your theme's primary color
                >
                    Add Load Balancer Host
                </Button>
            </HStack>

            {lbHosts && lbHosts.length > 0 ? (
                <TableContainer>
                    <Table variant="simple">
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
                                    <Td><Tag>{lbHost.inbound_tag}</Tag></Td>
                                    <Td>{lbHost.load_balancing_strategy.replace('_', ' ').toUpperCase()}</Td>
                                    <Td>{lbHost.nodes.length}</Td>
                                    <Td>
                                        <Tag colorScheme={lbHost.is_disabled ? 'red' : 'green'}>
                                            {lbHost.is_disabled ? 'Disabled' : 'Enabled'}
                                        </Tag>
                                    </Td>
                                    <Td>
                                        <HStack spacing={2}>
                                            <IconButton
                                                as={RouterLink}
                                                to={`/load-balancer-hosts/edit/${lbHost.id}`} // Define this route for editing
                                                aria-label="Edit Load Balancer Host"
                                                icon={<EditIcon />}
                                                size="sm"
                                                colorScheme="yellow"
                                            />
                                            <IconButton
                                                aria-label="Delete Load Balancer Host"
                                                icon={<DeleteIcon />}
                                                size="sm"
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
                <Text>No load balancer hosts found. Click "Add Load Balancer Host" to create one.</Text>
            )}
        </Box>
    );
};

export default LoadBalancerHostsPage; 