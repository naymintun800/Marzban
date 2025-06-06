import {
  Box,
  VStack,
  HStack,
  Text,
  Progress,
  Badge,
  Tooltip,
  Card,
  CardBody,
  SimpleGrid,
  Divider,
} from "@chakra-ui/react";
import { FC } from "react";
import { useQuery } from "react-query";
import { fetch } from "service/http";
import { NodePerformanceResponse } from "types/nodeMetrics";
import { numberWithCommas } from "utils/formatByte";

export const NodePerformanceOverview: FC = () => {
  const { data: performanceData } = useQuery<NodePerformanceResponse>({
    queryKey: "node-performance-overview-detailed",
    queryFn: () => fetch("/api/resilient-node-groups/metrics/performance"),
    refetchInterval: 30000, // Refresh every 30 seconds
    retry: 1,
  });

  if (!performanceData || performanceData.groups.length === 0) {
    return null; // Don't show if no resilient groups exist
  }

  const getStrategyColor = (strategy: string) => {
    switch (strategy) {
      case 'url-test': return 'blue';
      case 'fallback': return 'orange';
      case 'load-balance': return 'green';
      case 'client-default': return 'purple';
      default: return 'gray';
    }
  };

  const getHealthPercentage = (nodes: any[]) => {
    if (nodes.length === 0) return 0;
    const connectedNodes = nodes.filter(n => n.status === 'connected');
    if (connectedNodes.length === 0) return 0;
    const healthyNodes = connectedNodes.filter(n => 
      n.success_rate === null || n.success_rate >= 80
    );
    return (healthyNodes.length / connectedNodes.length) * 100;
  };

  const formatResponseTime = (time: number | null) => {
    if (time === null) return "N/A";
    if (time < 100) return `${Math.round(time)}ms`;
    if (time < 1000) return `${Math.round(time)}ms`;
    return `${(time / 1000).toFixed(1)}s`;
  };

  return (
    <Card size="sm" variant="outline">
      <CardBody>
        <VStack spacing={4} align="stretch">
          <HStack justify="space-between">
            <Text fontSize="sm" fontWeight="semibold" color="gray.700" _dark={{ color: "gray.300" }}>
              Resilient Node Groups Performance
            </Text>
            <Badge variant="outline" fontSize="xs">
              {performanceData.groups.length} groups
            </Badge>
          </HStack>

          <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={3}>
            {performanceData.groups.map((group) => {
              const connectedNodes = group.nodes.filter(n => n.status === 'connected');
              const totalConnections = group.nodes.reduce((sum, n) => sum + (n.active_connections || 0), 0);
              const healthPercentage = getHealthPercentage(group.nodes);
              const avgResponseTime = connectedNodes.length > 0 
                ? connectedNodes.reduce((sum, n) => sum + (n.avg_response_time || 0), 0) / connectedNodes.length 
                : null;

              return (
                <Box
                  key={group.group_id}
                  p={3}
                  borderRadius="md"
                  bg="gray.50"
                  _dark={{ bg: "gray.700", borderColor: "gray.600" }}
                  borderWidth="1px"
                  borderColor="gray.200"
                >
                  <VStack spacing={2} align="stretch">
                    <HStack justify="space-between">
                      <Text fontSize="xs" fontWeight="medium" noOfLines={1}>
                        {group.group_name}
                      </Text>
                      <Badge 
                        colorScheme={getStrategyColor(group.strategy)} 
                        variant="subtle" 
                        fontSize="2xs"
                      >
                        {group.strategy}
                      </Badge>
                    </HStack>

                    <HStack justify="space-between" fontSize="xs">
                      <Text color="gray.600" _dark={{ color: "gray.400" }}>
                        {connectedNodes.length}/{group.nodes.length} nodes
                      </Text>
                      {totalConnections > 0 && (
                        <Text color="green.600" _dark={{ color: "green.400" }}>
                          {numberWithCommas(totalConnections)} conn
                        </Text>
                      )}
                    </HStack>

                    {connectedNodes.length > 0 && (
                      <>
                        <Tooltip label={`${Math.round(healthPercentage)}% healthy nodes`}>
                          <Progress 
                            value={healthPercentage} 
                            size="xs" 
                            colorScheme={healthPercentage >= 80 ? "green" : healthPercentage >= 60 ? "yellow" : "red"}
                            borderRadius="sm"
                          />
                        </Tooltip>

                        {avgResponseTime && avgResponseTime > 0 && (
                          <Text fontSize="2xs" color="gray.500" textAlign="center">
                            {formatResponseTime(avgResponseTime)} avg
                          </Text>
                        )}
                      </>
                    )}
                  </VStack>
                </Box>
              );
            })}
          </SimpleGrid>

          <Divider />

          <HStack justify="center" spacing={6} fontSize="xs" color="gray.500">
            <Text>
              Total: {performanceData.groups.reduce((sum, g) => sum + g.nodes.length, 0)} nodes
            </Text>
            <Text>
              Connected: {performanceData.groups.reduce((sum, g) => 
                sum + g.nodes.filter(n => n.status === 'connected').length, 0
              )}
            </Text>
            <Text>
              Active: {performanceData.groups.reduce((sum, g) => 
                sum + g.nodes.reduce((nodeSum, n) => nodeSum + (n.active_connections || 0), 0), 0
              )} connections
            </Text>
          </HStack>
        </VStack>
      </CardBody>
    </Card>
  );
};
