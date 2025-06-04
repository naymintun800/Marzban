import React, { useEffect, useMemo, useState } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  Button,
  FormControl,
  FormLabel,
  Input,
  Select,
  Checkbox,
  VStack,
  Text,
  // Textarea, // If needed for longer text fields like remark template
  // useToast, // For feedback
} from '@chakra-ui/react';
import { useDashboard, Inbounds, InboundType } from '../contexts/DashboardContext';
import { 
  LoadBalancerHostResponse, 
  ProxyHostSecurity,  // Corrected import
  ProxyHostALPN,      // Corrected import
  ProxyHostFingerprint, // Corrected import
  LoadBalancerStrategy,
  NodeResponse
} from '../types/loadBalancer';
import { useNodesQuery, NodeType } from '../contexts/NodesContext';
import { useCreateLoadBalancerHost, useUpdateLoadBalancerHost } from '../hooks/useLoadBalancerHosts'; // Uncommented and path corrected
// import { useInbounds } from '../hooks/useInbounds'; // This was never used

const LoadBalancerHostFormModal: React.FC = () => {
  const { editingLoadBalancerHostData, onOpenLoadBalancerHostForm, inbounds } = useDashboard();
  // const toast = useToast();
  const { data: nodes, isLoading: isLoadingNodes } = useNodesQuery();
  // const { data: inbounds } = useInbounds(); // TODO: Fetch inbounds

  const createMutation = useCreateLoadBalancerHost(); // Uncommented
  const updateMutation = useUpdateLoadBalancerHost(); // Uncommented

  const [name, setName] = useState('');
  const [remarkTemplate, setRemarkTemplate] = useState('');
  const [address, setAddress] = useState('');
  const [port, setPort] = useState<number | '' >('');
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
  const [selectedNodes, setSelectedNodes] = useState<string[]>([]);
  const [strategy, setStrategy] = useState<LoadBalancerStrategy>(LoadBalancerStrategy.ROUND_ROBIN);

  const isEditing = editingLoadBalancerHostData && editingLoadBalancerHostData !== 'new';
  const isOpen = !!editingLoadBalancerHostData;

  // Memoize the list of unique inbound tags
  const uniqueInboundTags = useMemo(() => {
    const tags = new Set<string>();
    if (inbounds) {
      for (const protocolInbounds of inbounds.values()) {
        protocolInbounds.forEach((inbound: InboundType) => {
          tags.add(inbound.tag);
        });
      }
    }
    return Array.from(tags);
  }, [inbounds]);

  useEffect(() => {
    if (nodes) {
      console.log('Fetched Nodes:', nodes);
    }
    // Log unique inbound tags when they are computed
    // console.log('Unique Inbound Tags:', uniqueInboundTags);
  }, [nodes, uniqueInboundTags]);

  useEffect(() => {
    if (isEditing && typeof editingLoadBalancerHostData === 'object' && editingLoadBalancerHostData !== null) {
      const data = editingLoadBalancerHostData as LoadBalancerHostResponse;
      setName(data.name);
      setRemarkTemplate(data.remark_template || '');
      setAddress(data.address);
      setPort(data.port ?? ''); // Handle null port
      setPath(data.path || '');
      setSni(data.sni || '');
      setHostHeader(data.host_header || '');
      setSecurity(data.security || ProxyHostSecurity.INBOUND_DEFAULT);
      setAlpn(data.alpn || ProxyHostALPN.NONE);
      setFingerprint(data.fingerprint || ProxyHostFingerprint.NONE);
      setAllowInsecure(data.allowinsecure || false); // Corrected property name
      setIsDisabled(data.is_disabled || false);
      setMuxEnable(data.mux_enable || false);
      setFragmentSetting(data.fragment_setting || '');
      setNoiseSetting(data.noise_setting || '');
      setRandomUserAgent(data.random_user_agent || false);
      setUseSniAsHost(data.use_sni_as_host || false);
      setInboundTag(data.inbound_tag || '');
      // Assuming selectedNodes stores node names for the comma-separated input
      setSelectedNodes(data.nodes ? data.nodes.map((node: NodeResponse) => node.name) : []); 
      setStrategy(data.load_balancing_strategy || LoadBalancerStrategy.ROUND_ROBIN); // Corrected property name
    } else {
      // Reset form for 'new'
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
  }, [editingLoadBalancerHostData, isEditing]);

  // Helper function to map node names to IDs
  const mapNodeNamesToIds = (names: string[], allNodes: NodeType[] | undefined): number[] => {
    if (!allNodes) return [];
    const idMap = new Map(allNodes.map(node => [node.name, node.id]));
    return names.map(name => idMap.get(name)).filter(id => id !== undefined) as number[];
  };

  const handleClose = () => {
    onOpenLoadBalancerHostForm(null);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    const node_ids = mapNodeNamesToIds(selectedNodes, nodes);

    const hostDataForApi = {
      name,
      remark_template: remarkTemplate,
      address,
      port: port === '' ? undefined : Number(port),
      path,
      sni,
      host_header: hostHeader,
      security,
      alpn,
      fingerprint,
      allowinsecure: allowInsecure,
      is_disabled: isDisabled,
      mux_enable: muxEnable,
      fragment_setting: fragmentSetting,
      noise_setting: noiseSetting,
      random_user_agent: randomUserAgent,
      use_sni_as_host: useSniAsHost,
      inbound_tag: inboundTag,
      load_balancing_strategy: strategy,
      node_ids, // Use mapped node_ids
    };

    if (isEditing && typeof editingLoadBalancerHostData === 'object' && editingLoadBalancerHostData !== null) {
      updateMutation.mutate(
        { id: (editingLoadBalancerHostData as LoadBalancerHostResponse).id, data: hostDataForApi }, 
        { onSuccess: handleClose } // Mutations already show toast
      );
    } else {
      createMutation.mutate(
        hostDataForApi, 
        { onSuccess: handleClose } // Mutations already show toast
      );
    }
    // handleClose(); // Called on success by mutation
  };

  if (!isOpen) return null;

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="xl">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>{isEditing ? 'Edit Load Balancer Host' : 'Add New Load Balancer Host'}</ModalHeader>
        <ModalCloseButton />
        <form onSubmit={handleSubmit}>
          <ModalBody pb={6}>
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel>Name</FormLabel>
                <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="My LB Host" />
              </FormControl>

              <FormControl>
                <FormLabel>Remark Template</FormLabel>
                <Input value={remarkTemplate} onChange={(e) => setRemarkTemplate(e.target.value)} placeholder="Optional remark template" />
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Virtual Address</FormLabel>
                <Input value={address} onChange={(e) => setAddress(e.target.value)} placeholder="e.g., 192.168.1.100 or domain.com" />
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Port</FormLabel>
                <Input type="number" value={port} onChange={(e) => setPort(e.target.value === '' ? '' : parseInt(e.target.value, 10))} placeholder="e.g., 443" />
              </FormControl>

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
                  {Object.values(ProxyHostSecurity).map(sVal => <option key={sVal} value={sVal}>{sVal.replace("_", " ").toUpperCase()}</option>)}
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

              <FormControl>
                <FormLabel>Inbound Tag</FormLabel>
                <Select value={inboundTag} onChange={(e) => setInboundTag(e.target.value)} placeholder="Select Inbound Tag">
                  {uniqueInboundTags.map(tag => (
                    <option key={tag} value={tag}>{tag}</option>
                  ))}
                </Select>
              </FormControl>
              
              <FormControl>
                <FormLabel>Nodes</FormLabel>
                {isLoadingNodes && <p>Loading nodes...</p>}
                {/* TODO: Replace with a multi-select or checkbox group populated with fetched nodes. 
                           For now, provide a list of available node names for easier manual input. */}
                {nodes && nodes.length > 0 && (
                  <VStack align="start" spacing={1} my={2} p={2} borderWidth="1px" borderRadius="md" w="full">
                    <FormLabel fontSize="sm">Available nodes (enter names below):</FormLabel>
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
                  {Object.values(LoadBalancerStrategy).map(lsVal => <option key={lsVal} value={lsVal}>{lsVal.replace("_", " ").toUpperCase()}</option>)}
                </Select>
              </FormControl>

              <Checkbox isChecked={allowInsecure} onChange={(e) => setAllowInsecure(e.target.checked)}>Allow Insecure</Checkbox>
              <Checkbox isChecked={isDisabled} onChange={(e) => setIsDisabled(e.target.checked)}>Is Disabled</Checkbox>
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
          </ModalBody>

          <ModalFooter>
            <Button colorScheme="blue" mr={3} type="submit">
              {isEditing ? 'Save Changes' : 'Create Host'}
            </Button>
            <Button variant="ghost" onClick={handleClose}>Cancel</Button>
          </ModalFooter>
        </form>
      </ModalContent>
    </Modal>
  );
};

export default LoadBalancerHostFormModal; 