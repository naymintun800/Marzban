import { useQuery, useMutation, useQueryClient, UseQueryResult, UseMutationResult } from '@tanstack/react-query';
import * as loadBalancerServices from '../services/loadBalancerHosts'; // Assuming services are here
import {
    LoadBalancerHostCreate,
    LoadBalancerHostUpdate,
    LoadBalancerHostResponse,
    NodeResponse // Assuming NodeResponse is also needed for other hooks eventually
} from '../types/loadBalancer';
import { useToast, ToastId } from '@chakra-ui/react'; // Or your preferred notification library
import { AxiosError } from 'axios'; // For typing API errors

// Define a more specific error type if you have a common API error structure
interface ApiError {
    detail?: string;
    // Add other common error fields if any
}

// Key for React Query cache
export const loadBalancerHostsQueryKeys = {
    all: ['loadBalancerHosts'] as const,
    lists: () => [...loadBalancerHostsQueryKeys.all, 'list'] as const,
    list: (filters: string) => [...loadBalancerHostsQueryKeys.lists(), { filters }] as const,
    details: () => [...loadBalancerHostsQueryKeys.all, 'detail'] as const,
    detail: (id: number) => [...loadBalancerHostsQueryKeys.details(), id] as const,
};

export const useLoadBalancerHosts = (): UseQueryResult<LoadBalancerHostResponse[], AxiosError<ApiError>> => {
    return useQuery(
        loadBalancerHostsQueryKeys.lists(),
        loadBalancerServices.getLoadBalancerHosts
    );
};

export const useLoadBalancerHost = (id: number | undefined): UseQueryResult<LoadBalancerHostResponse, AxiosError<ApiError>> => {
    return useQuery(
        loadBalancerHostsQueryKeys.detail(id!),
        () => loadBalancerServices.getLoadBalancerHostById(id!),
        {
            enabled: !!id, // Only run query if id is defined
        }
    );
};

export const useCreateLoadBalancerHost = (): UseMutationResult<
    LoadBalancerHostResponse,
    AxiosError<ApiError>,
    LoadBalancerHostCreate,
    unknown // Context type, if needed for optimistic updates
> => {
    const queryClient = useQueryClient();
    const toast = useToast();

    return useMutation(
        loadBalancerServices.createLoadBalancerHost,
        {
            onSuccess: (data: LoadBalancerHostResponse) => {
                queryClient.invalidateQueries(loadBalancerHostsQueryKeys.lists());
                toast({
                    title: 'Load Balancer Created',
                    description: `Successfully created ${data.name}.`,
                    status: 'success',
                    duration: 5000,
                    isClosable: true,
                });
            },
            onError: (error: AxiosError<ApiError>) => {
                toast({
                    title: 'Error Creating Load Balancer',
                    description: error.response?.data?.detail || error.message || 'An unexpected error occurred.',
                    status: 'error',
                    duration: 7000,
                    isClosable: true,
                });
            },
        }
    );
};

export const useUpdateLoadBalancerHost = (): UseMutationResult<
    LoadBalancerHostResponse,
    AxiosError<ApiError>,
    { id: number; data: LoadBalancerHostUpdate },
    unknown
> => {
    const queryClient = useQueryClient();
    const toast = useToast();

    return useMutation(
        ({ id, data }: { id: number; data: LoadBalancerHostUpdate }) => loadBalancerServices.updateLoadBalancerHost(id, data),
        {
            onSuccess: (data: LoadBalancerHostResponse, variables: { id: number; data: LoadBalancerHostUpdate }) => {
                queryClient.invalidateQueries(loadBalancerHostsQueryKeys.lists());
                queryClient.invalidateQueries(loadBalancerHostsQueryKeys.detail(variables.id));
                // Optionally, update the specific query cache directly
                // queryClient.setQueryData(loadBalancerHostsQueryKeys.detail(variables.id), data);
                toast({
                    title: 'Load Balancer Updated',
                    description: `Successfully updated ${data.name}.`,
                    status: 'success',
                    duration: 5000,
                    isClosable: true,
                });
            },
            onError: (error: AxiosError<ApiError>, variables: { id: number; data: LoadBalancerHostUpdate }) => {
                toast({
                    title: 'Error Updating Load Balancer',
                    description: error.response?.data?.detail || error.message || 'An unexpected error occurred.',
                    status: 'error',
                    duration: 7000,
                    isClosable: true,
                });
            },
        }
    );
};

export const useDeleteLoadBalancerHost = (): UseMutationResult<
    void,
    AxiosError<ApiError>,
    number, // ID of the load balancer to delete
    unknown
> => {
    const queryClient = useQueryClient();
    const toast = useToast();

    return useMutation(
        loadBalancerServices.deleteLoadBalancerHost,
        {
            onSuccess: (_data: void, id: number) => {
                queryClient.invalidateQueries(loadBalancerHostsQueryKeys.lists());
                queryClient.removeQueries(loadBalancerHostsQueryKeys.detail(id)); // Clean up detail query
                toast({
                    title: 'Load Balancer Deleted',
                    description: 'Successfully deleted the load balancer.',
                    status: 'success',
                    duration: 5000,
                    isClosable: true,
                });
            },
            onError: (error: AxiosError<ApiError>) => {
                toast({
                    title: 'Error Deleting Load Balancer',
                    description: error.response?.data?.detail || error.message || 'An unexpected error occurred.',
                    status: 'error',
                    duration: 7000,
                    isClosable: true,
                });
            },
        }
    );
};

// Example for fetching nodes, if not already present in your project:
// import * as nodeServices from '../services/nodes'; // Assuming a nodes.ts service file
// export const nodesQueryKeys = {
//    all: ['nodes'] as const,
//    lists: () => [...nodesQueryKeys.all, 'list'] as const,
// };

// export const useNodes = (): UseQueryResult<NodeResponse[], AxiosError<ApiError>> => {
//    return useQuery(nodesQueryKeys.lists(), nodeServices.getNodes);
// }; 