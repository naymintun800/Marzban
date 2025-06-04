import { $fetch as apiClient } from "../service/http"; // Corrected import path and aliased $fetch
import {
    LoadBalancerHostCreate,
    LoadBalancerHostUpdate,
    LoadBalancerHostResponse,
} from "../types/loadBalancer"; // Assuming loadBalancer.ts is in src/types/

const BASE_URL = "/api/load-balancer-hosts"; // This will be relative to VITE_BASE_API configured in http.ts

export const getLoadBalancerHosts = async (): Promise<LoadBalancerHostResponse[]> => {
    // ofetch throws errors for non-2xx responses, which React Query handles.
    // Type assertion might be needed if $fetch's generic isn't automatically inferred well by TS here.
    return apiClient<LoadBalancerHostResponse[]>(BASE_URL, { method: 'GET' });
};

export const getLoadBalancerHostById = async (id: number): Promise<LoadBalancerHostResponse> => {
    return apiClient<LoadBalancerHostResponse>(`${BASE_URL}/${id}`, { method: 'GET' });
};

export const createLoadBalancerHost = async (data: LoadBalancerHostCreate): Promise<LoadBalancerHostResponse> => {
    return apiClient<LoadBalancerHostResponse>(BASE_URL, {
        method: 'POST',
        body: data,
    });
};

export const updateLoadBalancerHost = async (id: number, data: LoadBalancerHostUpdate): Promise<LoadBalancerHostResponse> => {
    return apiClient<LoadBalancerHostResponse>(`${BASE_URL}/${id}`, {
        method: 'PUT',
        body: data,
    });
};

export const deleteLoadBalancerHost = async (id: number): Promise<void> => {
    // ofetch typically returns the response body or throws an error. For a DELETE that returns 204, this should be fine.
    // If it expects a JSON response and gets none, it might error. Adjust if needed based on actual API behavior.
    await apiClient<void>(`${BASE_URL}/${id}`, { method: 'DELETE' }); 
    // No explicit return needed if ofetch handles non-2xx by throwing and 204 has no body.
};

// You will also likely need a service to fetch nodes for the form
// This might already exist in a services/nodes.ts or similar
// If not, you would add:
// import { NodeResponse } from "../types/loadBalancer"; // or from a more general types/node.ts
// export const getNodes = async (): Promise<NodeResponse[]> => {
//     const response = await apiClient<NodeResponse[]>("/api/nodes", { method: 'GET' });
//     return response;
// };

// And potentially a service to fetch inbound tags if not easily available otherwise
// export const getCoreConfig = async (): Promise<any> => { // Replace 'any' with a proper type for Xray config
//     const response = await apiClient<any>("/api/core/config", { method: 'GET' });
//     return response;
// }; 