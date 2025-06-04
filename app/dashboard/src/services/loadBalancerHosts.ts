import apiClient from "../lib/apiClient"; // Adjust this import to your actual API client/Axios instance
import {
    LoadBalancerHostCreate,
    LoadBalancerHostUpdate,
    LoadBalancerHostResponse,
} from "../types/loadBalancer";

const BASE_URL = "/api/load-balancer-hosts";

export const getLoadBalancerHosts = async (): Promise<LoadBalancerHostResponse[]> => {
    const response = await apiClient.get<LoadBalancerHostResponse[]>(BASE_URL);
    return response.data;
};

export const getLoadBalancerHostById = async (id: number): Promise<LoadBalancerHostResponse> => {
    const response = await apiClient.get<LoadBalancerHostResponse>(`${BASE_URL}/${id}`);
    return response.data;
};

export const createLoadBalancerHost = async (data: LoadBalancerHostCreate): Promise<LoadBalancerHostResponse> => {
    const response = await apiClient.post<LoadBalancerHostResponse>(BASE_URL, data);
    return response.data;
};

export const updateLoadBalancerHost = async (id: number, data: LoadBalancerHostUpdate): Promise<LoadBalancerHostResponse> => {
    const response = await apiClient.put<LoadBalancerHostResponse>(`${BASE_URL}/${id}`, data);
    return response.data;
};

export const deleteLoadBalancerHost = async (id: number): Promise<void> => {
    await apiClient.delete(`${BASE_URL}/${id}`);
};

// You will also likely need a service to fetch nodes for the form
// This might already exist in a services/nodes.ts or similar
// If not, you would add:
// import { NodeResponse } from "../types/loadBalancer"; // or from a more general types/node.ts
// export const getNodes = async (): Promise<NodeResponse[]> => {
//     const response = await apiClient.get<NodeResponse[]>("/api/nodes");
//     return response.data;
// };

// And potentially a service to fetch inbound tags if not easily available otherwise
// export const getCoreConfig = async (): Promise<any> => { // Replace 'any' with a proper type for Xray config
//     const response = await apiClient.get<any>("/api/core/config");
//     return response.data;
// }; 