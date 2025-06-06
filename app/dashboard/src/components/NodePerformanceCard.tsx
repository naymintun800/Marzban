import { HStack, Text, Tooltip, Badge, VStack } from "@chakra-ui/react";
import { ServerIcon } from "@heroicons/react/24/outline";
import { chakra } from "@chakra-ui/react";
import { FC } from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "react-query";
import { fetch } from "service/http";
import { NodePerformanceOverview } from "types/nodeMetrics";
import { numberWithCommas } from "utils/formatByte";

const NodeIcon = chakra(ServerIcon, {
  baseStyle: {
    w: 5,
    h: 5,
    position: "relative",
    zIndex: "2",
  },
});

export interface NodePerformanceCardProps {
  icon: React.ReactElement;
  title: string;
  content: React.ReactNode;
}

const StatisticCard: FC<NodePerformanceCardProps> = ({ icon, title, content }) => (
  <VStack
    bg="white"
    _dark={{ bg: "gray.750" }}
    borderRadius="12px"
    p="6"
    flex="1"
    minW="200px"
    alignItems="flex-start"
    position="relative"
    overflow="hidden"
    spacing={3}
  >
    <HStack spacing={3}>
      {icon}
      <Text fontSize="sm" fontWeight="medium" color="gray.600" _dark={{ color: "gray.400" }}>
        {title}
      </Text>
    </HStack>
    {content}
  </VStack>
);

export const NodePerformanceCard: FC = () => {
  const { t } = useTranslation();
  
  const { data: performanceData } = useQuery<NodePerformanceOverview>({
    queryKey: "node-performance-overview",
    queryFn: () => fetch("/api/resilient-node-groups/metrics/overview"),
    refetchInterval: 30000, // Refresh every 30 seconds
    retry: 1,
  });

  const getHealthStatus = (healthyNodes: number, totalNodes: number) => {
    if (totalNodes === 0) return { color: "gray", text: "No Nodes" };
    const healthPercentage = (healthyNodes / totalNodes) * 100;
    if (healthPercentage >= 80) return { color: "green", text: "Healthy" };
    if (healthPercentage >= 60) return { color: "yellow", text: "Warning" };
    return { color: "red", text: "Critical" };
  };

  const formatResponseTime = (time: number | null) => {
    if (time === null) return "N/A";
    if (time < 100) return `${Math.round(time)}ms`;
    if (time < 1000) return `${Math.round(time)}ms`;
    return `${(time / 1000).toFixed(1)}s`;
  };

  if (!performanceData) {
    return (
      <StatisticCard
        title="Node Performance"
        content={<Text color="gray.500">Loading...</Text>}
        icon={<NodeIcon />}
      />
    );
  }

  const healthStatus = getHealthStatus(performanceData.healthy_nodes, performanceData.connected_nodes);

  return (
    <StatisticCard
      title="Node Performance"
      icon={<NodeIcon />}
      content={
        <VStack alignItems="flex-start" spacing={2} w="full">
          <HStack alignItems="flex-end" spacing={2}>
            <Text fontSize="2xl" fontWeight="bold">
              {numberWithCommas(performanceData.connected_nodes)}
            </Text>
            <Text fontSize="sm" color="gray.500" pb="2px">
              / {numberWithCommas(performanceData.total_nodes)} nodes
            </Text>
          </HStack>
          
          <HStack spacing={3} w="full" justify="space-between">
            <Tooltip label={`${performanceData.healthy_nodes} healthy out of ${performanceData.connected_nodes} connected`}>
              <Badge colorScheme={healthStatus.color} variant="subtle" fontSize="xs">
                {healthStatus.text}
              </Badge>
            </Tooltip>
            
            {performanceData.avg_response_time && (
              <Tooltip label="Average response time">
                <Text fontSize="xs" color="gray.600" _dark={{ color: "gray.400" }}>
                  {formatResponseTime(performanceData.avg_response_time)}
                </Text>
              </Tooltip>
            )}
          </HStack>

          {performanceData.total_active_connections > 0 && (
            <HStack spacing={1}>
              <Text fontSize="xs" color="gray.600" _dark={{ color: "gray.400" }}>
                {numberWithCommas(performanceData.total_active_connections)} active connections
              </Text>
            </HStack>
          )}

          {performanceData.total_groups > 0 && (
            <Text fontSize="xs" color="gray.500">
              {performanceData.total_groups} resilient groups
            </Text>
          )}
        </VStack>
      }
    />
  );
};
