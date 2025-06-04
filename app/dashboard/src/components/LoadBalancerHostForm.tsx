import React, { useEffect, useMemo, useState } from 'react';
import {
  ModalBody,
  ModalFooter,
  Button,
  FormControl,
  FormLabel,
  Input,
  Select,
  Checkbox,
  VStack,
  Text,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Box,
  // useToast, // Available if direct feedback within form is needed later
} from '@chakra-ui/react';
import { useDashboard, Inbounds, InboundType } from '../contexts/DashboardContext';
import {
  LoadBalancerHostResponse,
  ProxyHostSecurity,
  ProxyHostALPN,
  ProxyHostFingerprint,
  LoadBalancerStrategy,
  NodeResponse,
  LoadBalancerHostCreate,
  LoadBalancerHostUpdate,
} from '../types/loadBalancer';
import { useNodesQuery, NodeType } from '../contexts/NodesContext';
import { useCreateLoadBalancerHost, useUpdateLoadBalancerHost } from '../hooks/useLoadBalancerHosts';

interface LoadBalancerHostFormProps {
  initialData: LoadBalancerHostResponse | 'new' | null;
  onSubmitSuccess: () => void;
  onCancel: () => void;
}

const LoadBalancerHostForm: React.FC<LoadBalancerHostFormProps> = ({
  initialData,
  onSubmitSuccess,
  onCancel,
}) => {
  const { inbounds } = useDashboard();
  const { data: nodes, isLoading: isLoadingNodes } = useNodesQuery();
  // const toast = useToast(); // For potential direct feedback

  const createMutation = useCreateLoadBalancerHost();
  const updateMutation = useUpdateLoadBalancerHost();

  const [name, setName] = useState('');
  const [remarkTemplate, setRemarkTemplate] = useState('');
  const [address, setAddress] = useState('');
  const [port, setPort] = useState<number | ''>('');
  const [path, setPath] = useState('');
  const [sni, setSni] = useState('');
  const [hostHeader, setHostHeader] = useState('');
  const [security, setSecurity] = useState<ProxyHostSecurity>(ProxyHostSecurity.INBOUND_DEFAULT);
  const [alpn, setAlpn] = useState<ProxyHostALPN>(ProxyHostALPN.NONE);
  const [fingerprint, setFingerprint] = useState<ProxyHostFingerprint>(ProxyHostFingerprint.NONE);
  const [allowInsecure, setAllowInsecure] = useState(false);
  const [isDisabled, setIsDisabled] = useState(false);
  const [muxEnable, setMuxEnable] = useState(false);
  const [fragmentSetting, setFragmentSetting] = useState('');
  const [noiseSetting, setNoiseSetting] = useState('');
  const [randomUserAgent, setRandomUserAgent] = useState(false);
  const [useSniAsHost, setUseSniAsHost] = useState(false);
  const [inboundTag, setInboundTag] = useState('');
  const [selectedNodes, setSelectedNodes] = useState<string[]>([]); // Stores node names
  const [strategy, setStrategy] = useState<LoadBalancerStrategy>(LoadBalancerStrategy.ROUND_ROBIN);

  const isEditing = initialData && initialData !== 'new';

  const uniqueInboundTags = useMemo(() => {
    const tags = new Set<string>();
    if (inbounds) {
      for (const protocolInbounds of inbounds.values()) {
        protocolInbounds.forEach((inboundItem: InboundType) => {
          tags.add(inboundItem.tag);
        });
      }
    }
    return Array.from(tags);
  }, [inbounds]);

  useEffect(() => {
    // console.log('Fetched Nodes for form:', nodes);
  }, [nodes]);

  useEffect(() => {
    if (isEditing && typeof initialData === 'object' && initialData !== null) {
      const data = initialData as LoadBalancerHostResponse;
      setName(data.name);
      setRemarkTemplate(data.remark_template || '');
      setAddress(data.address);
      setPort(data.port ?? '');
      setPath(data.path || '');
      setSni(data.sni || '');
      setHostHeader(data.host_header || '');
      setSecurity(data.security || ProxyHostSecurity.INBOUND_DEFAULT);
      setAlpn(data.alpn || ProxyHostALPN.NONE);
      setFingerprint(data.fingerprint || ProxyHostFingerprint.NONE);
      setAllowInsecure(data.allowinsecure || false);
      setIsDisabled(data.is_disabled || false);
      setMuxEnable(data.mux_enable || false);
      setFragmentSetting(data.fragment_setting || '');
      setNoiseSetting(data.noise_setting || '');
      setRandomUserAgent(data.random_user_agent || false);
      setUseSniAsHost(data.use_sni_as_host || false);
      setInboundTag(data.inbound_tag || '');
      setSelectedNodes(data.nodes ? data.nodes.map((node: NodeResponse) => node.name) : []);
      setStrategy(data.load_balancing_strategy || LoadBalancerStrategy.ROUND_ROBIN);
    } else {
      setName('');
      setRemarkTemplate('');
      setAddress('');
      setPort('');
      setPath('');
      setSni('');
      setHostHeader('');
      setSecurity(ProxyHostSecurity.INBOUND_DEFAULT);
      setAlpn(ProxyHostALPN.NONE);
      setFingerprint(ProxyHostFingerprint.NONE);
      setAllowInsecure(false);
      setIsDisabled(false);
      setMuxEnable(false);
      setFragmentSetting('');
      setNoiseSetting('');
      setRandomUserAgent(false);
      setUseSniAsHost(false);
      setInboundTag('');
      setSelectedNodes([]);
      setStrategy(LoadBalancerStrategy.ROUND_ROBIN);
    }
  }, [initialData, isEditing]);

  const mapNodeNamesToIds = (names: string[], allNodes: NodeType[] | undefined): number[] => {
    if (!allNodes) return [];
    const idMap = new Map<string, number>();
    allNodes.forEach(node => {
        if (typeof node.id === 'number') { // Ensure node.id is a valid number
            idMap.set(node.name, node.id);
        }
    });
    return names.map(name => idMap.get(name)).filter(id => typeof id === 'number') as number[];
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const node_ids = mapNodeNamesToIds(selectedNodes, nodes);

    const commonPayload = {
      name,
      remark_template: remarkTemplate || undefined, // Send undefined if empty for optional fields
      address,
      port: port === '' ? null : Number(port),
      path: path || undefined,
      sni: sni || undefined,
      host_header: hostHeader || undefined,
      security,
      alpn,
      fingerprint,
      allowinsecure: allowInsecure,
      is_disabled: isDisabled,
      mux_enable: muxEnable,
      fragment_setting: fragmentSetting || undefined,
      noise_setting: noiseSetting || undefined,
      random_user_agent: randomUserAgent,
      use_sni_as_host: useSniAsHost,
      inbound_tag: inboundTag, // This is required for create
      load_balancing_strategy: strategy,
      node_ids, // This is required for create
    };

    if (isEditing && typeof initialData === 'object' && initialData !== null) {
      const updatePayload: LoadBalancerHostUpdate = commonPayload;
      updateMutation.mutate(
        { id: (initialData as LoadBalancerHostResponse).id, data: updatePayload },
        { onSuccess: onSubmitSuccess }
      );
    } else {
      const createPayload: LoadBalancerHostCreate = {
        ...commonPayload,
        // Ensure required fields for create that might be optional in commonPayload are asserted or handled
        // name, address, inbound_tag, node_ids are already covered or required by form
      };
      createMutation.mutate(
        createPayload,
        { onSuccess: onSubmitSuccess }
      );
    }
  };

  return (
    <>
      <ModalBody pb={6} overflowY="auto" maxHeight="calc(100vh - 220px)"> {/* Adjusted maxHeight */}
        <form onSubmit={handleSubmit} id="lb-host-form">
          <VStack spacing={4} alignItems="stretch">
            <FormControl isRequired>
              <FormLabel>Name</FormLabel>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="My LB Host" />
            </FormControl>

            <FormControl isRequired>
              <FormLabel>Virtual Address</FormLabel>
              <Input value={address} onChange={(e) => setAddress(e.target.value)} placeholder="e.g., 192.168.1.100 or domain.com" />
            </FormControl>

            <FormControl isRequired>
              <FormLabel>Port</FormLabel>
              <Input type="number" value={port} onChange={(e) => setPort(e.target.value === '' ? '' : parseInt(e.target.value, 10))} placeholder="e.g., 443" />
            </FormControl>

            <FormControl isRequired>
              <FormLabel>Inbound Tag</FormLabel>
              <Select value={inboundTag} onChange={(e) => setInboundTag(e.target.value)} placeholder="Select Inbound Tag">
                {uniqueInboundTags.map(tag => (
                  <option key={tag} value={tag}>{tag}</option>
                ))}
              </Select>
            </FormControl>
            
            <FormControl isRequired>
              <FormLabel>Nodes</FormLabel>
              {isLoadingNodes && <Text>Loading nodes...</Text>}
              {nodes && nodes.length > 0 && (
                <VStack align="stretch" spacing={1} my={2} p={2} borderWidth="1px" borderRadius="md" w="full" maxH="150px" overflowY="auto">
                  <FormLabel fontSize="sm" mb={0}>Available nodes (enter names below, comma-separated):</FormLabel>
                  {nodes.map((node: NodeType) => (
                    <Text fontSize="xs" key={node.id || node.name}>{node.name} (ID: {node.id})</Text>
                  ))}
                </VStack>
              )}
              <Input 
                placeholder="Node names, comma-separated (e.g., node1,node2)" 
                value={selectedNodes.join(',')} 
                onChange={(e) => setSelectedNodes(e.target.value.split(',').map(s => s.trim()).filter(Boolean))} 
              />
            </FormControl>

            <FormControl>
              <FormLabel>Load Balancing Strategy</FormLabel>
              <Select value={strategy} onChange={(e) => setStrategy(e.target.value as LoadBalancerStrategy)}>
                {Object.values(LoadBalancerStrategy).map(lsVal => <option key={lsVal} value={lsVal}>{lsVal.replace(/_/g, " ").toUpperCase()}</option>)}
              </Select>
            </FormControl>

            <FormControl>
              <FormLabel>Remark Template</FormLabel>
              <Input value={remarkTemplate} onChange={(e) => setRemarkTemplate(e.target.value)} placeholder="Optional remark template" />
            </FormControl>
            
            <Checkbox isChecked={isDisabled} onChange={(e) => setIsDisabled(e.target.checked)}>Is Disabled</Checkbox>

            <Accordion allowToggle>
              <AccordionItem>
                <h2>
                  <AccordionButton>
                    <Box flex="1" textAlign="left" fontWeight="medium">
                      Advanced Options
                    </Box>
                    <AccordionIcon />
                  </AccordionButton>
                </h2>
                <AccordionPanel pb={4}>
                  <VStack spacing={4} alignItems="stretch">
                    <FormControl>
                      <FormLabel>Path</FormLabel>
                      <Input value={path} onChange={(e) => setPath(e.target.value)} placeholder="Optional, e.g., /my-path" />
                    </FormControl>

                    <FormControl>
                      <FormLabel>SNI (Server Name Indication)</FormLabel>
                      <Input value={sni} onChange={(e) => setSni(e.target.value)} placeholder="Optional, e.g., yourdomain.com" />
                    </FormControl>

                    <FormControl>
                      <FormLabel>Host Header</FormLabel>
                      <Input value={hostHeader} onChange={(e) => setHostHeader(e.target.value)} placeholder="Optional, e.g., yourdomain.com" />
                    </FormControl>

                    <FormControl>
                      <FormLabel>Security</FormLabel>
                      <Select value={security} onChange={(e) => setSecurity(e.target.value as ProxyHostSecurity)}>
                        {Object.values(ProxyHostSecurity).map(sVal => <option key={sVal} value={sVal}>{sVal.replace(/_/g, " ").toUpperCase()}</option>)}
                      </Select>
                    </FormControl>

                    <FormControl>
                      <FormLabel>ALPN</FormLabel>
                      <Select value={alpn} onChange={(e) => setAlpn(e.target.value as ProxyHostALPN)}>
                        {Object.values(ProxyHostALPN).map(aVal => <option key={aVal} value={aVal}>{aVal}</option>)}
                      </Select>
                    </FormControl>

                    <FormControl>
                      <FormLabel>Fingerprint</FormLabel>
                      <Select value={fingerprint} onChange={(e) => setFingerprint(e.target.value as ProxyHostFingerprint)}>
                        {Object.values(ProxyHostFingerprint).map(fVal => <option key={fVal} value={fVal}>{fVal.toUpperCase()}</option>)}
                      </Select>
                    </FormControl>

                    <Checkbox isChecked={allowInsecure} onChange={(e) => setAllowInsecure(e.target.checked)}>Allow Insecure</Checkbox>
                    <Checkbox isChecked={muxEnable} onChange={(e) => setMuxEnable(e.target.checked)}>Mux Enable</Checkbox>
                    <Checkbox isChecked={randomUserAgent} onChange={(e) => setRandomUserAgent(e.target.checked)}>Random User Agent</Checkbox>
                    <Checkbox isChecked={useSniAsHost} onChange={(e) => setUseSniAsHost(e.target.checked)}>Use SNI as Host</Checkbox>

                    <FormControl>
                      <FormLabel>Fragment Setting</FormLabel>
                      <Input value={fragmentSetting} onChange={(e) => setFragmentSetting(e.target.value)} placeholder="Optional" />
                    </FormControl>

                    <FormControl>
                      <FormLabel>Noise Setting</FormLabel>
                      <Input value={noiseSetting} onChange={(e) => setNoiseSetting(e.target.value)} placeholder="Optional" />
                    </FormControl>
                  </VStack>
                </AccordionPanel>
              </AccordionItem>
            </Accordion>
          </VStack>
        </form>
      </ModalBody>
      <ModalFooter>
        <Button 
            colorScheme="blue" 
            mr={3} 
            type="submit" 
            form="lb-host-form" 
            isLoading={createMutation.isLoading || updateMutation.isLoading}
            isDisabled={createMutation.isLoading || updateMutation.isLoading}
        >
          {isEditing ? 'Save Changes' : 'Create Host'}
        </Button>
        <Button 
            variant="ghost" 
            onClick={onCancel} 
            isDisabled={createMutation.isLoading || updateMutation.isLoading}
        >
            Cancel
        </Button>
      </ModalFooter>
    </>
  );
};

export default LoadBalancerHostForm; 