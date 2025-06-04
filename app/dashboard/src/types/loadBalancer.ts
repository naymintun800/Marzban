// Based on app/models/node.py -> NodeResponse
export interface NodeResponse {
    id: number;
    name: string;
    address: string;
    port: number;
    api_port: number;
    usage_coefficient: number;
    xray_version?: string | null;
    status: 'connected' | 'connecting' | 'error' | 'disabled'; // Corresponds to NodeStatus enum
    message?: string | null;
}

// Based on app/models/proxy.py Enums (ensure these match exactly from your backend)
export enum ProxyHostSecurity {
    INBOUND_DEFAULT = "inbound_default", // Adjusted to match common frontend enum naming
    NONE = "none",
    TLS = "tls",
    REALITY = "reality",
}

export enum ProxyHostALPN {
    NONE = "none",
    HTTP_1_1 = "http/1.1",
    H2 = "h2",
    H2_HTTP_1_1 = "h2,http/1.1",
    H3 = "h3",
    H3_H2_HTTP_1_1 = "h3,h2,http/1.1",
}

export enum ProxyHostFingerprint {
    NONE = "none",
    CHROME = "chrome",
    FIREFOX = "firefox",
    SAFARI = "safari",
    IOS = "ios",
    ANDROID = "android",
    EDGE = "edge",
    RANDOM = "random",
    RANDOMIZED = "randomized",
}

// Based on app/models/load_balancer.py -> LoadBalancerStrategy
export enum LoadBalancerStrategy {
    ROUND_ROBIN = "round_robin",
    RANDOM = "random",
    // LEAST_CONNECTIONS = "least_connections", // Future option
    // WEIGHTED_ROUND_ROBIN = "weighted_round_robin", // Future option
}

// Based on app/models/load_balancer.py -> LoadBalancerHostResponse
export interface LoadBalancerHostResponse {
    id: number;
    name: string;
    remark_template: string;
    address: string;
    port?: number | null;
    path?: string | null;
    sni?: string | null;
    host_header?: string | null;
    security: ProxyHostSecurity;
    alpn: ProxyHostALPN;
    fingerprint: ProxyHostFingerprint;
    allowinsecure?: boolean | null;
    is_disabled?: boolean | null;
    mux_enable?: boolean;
    fragment_setting?: string | null;
    noise_setting?: string | null;
    random_user_agent?: boolean;
    use_sni_as_host?: boolean;
    inbound_tag: string;
    load_balancing_strategy: LoadBalancerStrategy;
    nodes: NodeResponse[]; // Embeds full node details
    created_at?: string; // Assuming datetime is serialized as string
    updated_at?: string; // Assuming datetime is serialized as string
}

// Based on app/models/load_balancer.py -> LoadBalancerHostCreate
export interface LoadBalancerHostCreate {
    name: string;
    remark_template?: string;
    address: string;
    port?: number | null;
    path?: string | null;
    sni?: string | null;
    host_header?: string | null;
    security?: ProxyHostSecurity;
    alpn?: ProxyHostALPN;
    fingerprint?: ProxyHostFingerprint;
    allowinsecure?: boolean | null;
    is_disabled?: boolean | null;
    mux_enable?: boolean;
    fragment_setting?: string | null;
    noise_setting?: string | null;
    random_user_agent?: boolean;
    use_sni_as_host?: boolean;
    inbound_tag: string;
    load_balancing_strategy?: LoadBalancerStrategy;
    node_ids: number[];
}

// Based on app/models/load_balancer.py -> LoadBalancerHostUpdate
export interface LoadBalancerHostUpdate {
    name?: string | null;
    remark_template?: string | null;
    address?: string | null;
    port?: number | null;
    path?: string | null;
    sni?: string | null;
    host_header?: string | null;
    security?: ProxyHostSecurity | null;
    alpn?: ProxyHostALPN | null;
    fingerprint?: ProxyHostFingerprint | null;
    allowinsecure?: boolean | null;
    is_disabled?: boolean | null;
    mux_enable?: boolean | null;
    fragment_setting?: string | null;
    noise_setting?: string | null;
    random_user_agent?: boolean | null;
    use_sni_as_host?: boolean | null;
    inbound_tag?: string | null;
    load_balancing_strategy?: LoadBalancerStrategy | null;
    node_ids?: number[] | null;
} 