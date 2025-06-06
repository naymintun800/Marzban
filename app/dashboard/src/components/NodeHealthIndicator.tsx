import { HStack, Circle, Tooltip, Text } from "@chakra-ui/react";
import { FC } from "react";
import { useQuery } from "react-query";
import { fetch } from "service/http";
import { NodePerformanceOverview } from "types/nodeMetrics";

export const NodeHealthIndicator: FC = () => {
  const { data: performanceData } = useQuery<NodePerformanceOverview>({
    queryKey: "node-health-indicator",
    queryFn: () => fetch("/api/resilient-node-groups/metrics/overview"),
    refetchInterval: 60000, // Refresh every minute
    retry: 1,
    staleTime: 30000, // Consider data stale after 30 seconds
  });

  if (!performanceData || performanceData.total_groups === 0) {
    return null; // Don't show indicator if no resilient groups exist
  }

  const getHealthColor = () => {
    if (performanceData.connected_nodes === 0) return "red.500";
    
    const healthPercentage = (performanceData.healthy_nodes / performanceData.connected_nodes) * 100;
    if (healthPercentage >= 80) return "green.500";
    if (healthPercentage >= 60) return "yellow.500";
    return "red.500";
  };

  const getTooltipText = () => {
    if (performanceData.connected_nodes === 0) {
      return "No connected nodes";
    }
    
    const parts = [
      `${performanceData.healthy_nodes}/${performanceData.connected_nodes} nodes healthy`,
    ];
    
    if (performanceData.total_active_connections > 0) {
      parts.push(`${performanceData.total_active_connections} active connections`);
    }
    
    if (performanceData.avg_response_time) {
      parts.push(`${Math.round(performanceData.avg_response_time)}ms avg response`);
    }
    
    return parts.join(" • ");
  };

  return (
    <Tooltip label={getTooltipText()} placement="bottom">
      <HStack spacing={1} cursor="pointer">
        <Circle size="8px" bg={getHealthColor()} />
        <Text fontSize="xs" color="gray.600" _dark={{ color: "gray.400" }}>
          {performanceData.connected_nodes} nodes
        </Text>
      </HStack>
    </Tooltip>
  );
};
