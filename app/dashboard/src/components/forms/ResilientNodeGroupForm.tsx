import React, { useEffect } from 'react';
import { useDashboard } from '../../contexts/DashboardContext';
import {
  useCreateResilientNodeGroupMutation,
  useUpdateResilientNodeGroupMutation,
} from '../../hooks/useResilientNodeGroups';
import { useMarzbanNodesQuery } from '../../hooks/useMarzbanNodes';
import { NewResilientNodeGroup, ResilientNodeGroup, ClientStrategyHint } from '../../types/resilientNodeGroup';
import { Form, Input, Select, Button, Spin, message, Checkbox } from 'antd';

const clientStrategyOptions: { label: string; value: ClientStrategyHint }[] = [
  { label: 'Client Default/Random', value: 'client-default' },
  { label: 'URL-Test (Clash/Sing-box)', value: 'url-test' },
  { label: 'Fallback (Clash/Sing-box)', value: 'fallback' },
  { label: 'Load Balance (Clash/Sing-box)', value: 'load-balance' },
  { label: 'Not Set', value: '' },
];

const ResilientNodeGroupForm: React.FC = () => {
  const [form] = Form.useForm();
  const {
    editingResilientNodeGroup,
    onCloseResilientNodeGroupsModal,
  } = useDashboard();

  const { data: marzbanNodes, isLoading: isLoadingNodes, error: nodesError } = useMarzbanNodesQuery();

  useEffect(() => {
    if (editingResilientNodeGroup) {
      form.setFieldsValue(
        editingResilientNodeGroup.name || editingResilientNodeGroup.node_ids?.length > 0 || editingResilientNodeGroup.client_strategy_hint
        ? { ...editingResilientNodeGroup }
        : { name: '', node_ids: [], client_strategy_hint: 'client-default' }
      );
    } else {
      form.resetFields();
      form.setFieldsValue({ name: '', node_ids: [], client_strategy_hint: 'client-default' });
    }
  }, [editingResilientNodeGroup, form]);
  
  useEffect(() => {
    if (nodesError) {
      message.error(`Error fetching Marzban nodes: ${nodesError.message}`);
    }
  }, [nodesError]);

  const createMutation = useCreateResilientNodeGroupMutation();
  const updateMutation = useUpdateResilientNodeGroupMutation();

  const isEditing = !!editingResilientNodeGroup?.id;
  const mutationLoading = createMutation.isLoading || updateMutation.isLoading;

  const handleSubmit = (values: NewResilientNodeGroup) => {
    if (!values.name) {
      message.error('Group Name is required.');
      return;
    }
    if (!values.node_ids || values.node_ids.length === 0) {
      message.error('Please select at least one node.');
      return;
    }

    const groupDataToSubmit: NewResilientNodeGroup = {
      ...editingResilientNodeGroup,
      ...values,
      node_ids: values.node_ids.map(id => String(id)),
    };

    if (isEditing) {
      updateMutation.mutate(groupDataToSubmit as ResilientNodeGroup, {
        onSuccess: () => {
          message.success('Resilient Node Group updated successfully!');
          onCloseResilientNodeGroupsModal();
        },
        onError: (error: any) => {
          message.error(`Failed to update group: ${error.message}`);
        },
      });
    } else {
      createMutation.mutate(groupDataToSubmit, {
        onSuccess: () => {
          message.success('Resilient Node Group created successfully!');
          onCloseResilientNodeGroupsModal();
        },
        onError: (error: any) => {
          message.error(`Failed to create group: ${error.message}`);
        },
      });
    }
  };

  if (isLoadingNodes && !isEditing && !form.getFieldValue('name') && !marzbanNodes) {
      return <Spin spinning={true} tip="Loading node data..."></Spin>;
  }

  return (
    <Spin spinning={mutationLoading || (isLoadingNodes && !marzbanNodes && !form.getFieldValue('name'))}>
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{ name: '', node_ids: [], client_strategy_hint: 'client-default' }}
      >
        <Form.Item
          label="Group Name"
          name="name"
          rules={[{ required: true, message: 'Please input the group name!' }]}
        >
          <Input placeholder="My Resilient Group" />
        </Form.Item>

        <Form.Item
          label="Select Nodes"
          name="node_ids"
          rules={[{ required: true, message: 'Please select at least one node!', type: 'array' }]}
        >
          <Checkbox.Group
            options={marzbanNodes?.map(node => ({ label: node.name, value: node.id })) || []}
            disabled={isLoadingNodes}
          />
        </Form.Item>

        <Form.Item
          label="Client-Side Strategy Hint"
          name="client_strategy_hint"
          rules={[{ required: true, message: 'Please select a strategy hint!' }]}
        >
          <Select placeholder="Select a strategy">
            {clientStrategyOptions.map(opt => (
              <Select.Option key={opt.value} value={opt.value}>{opt.label}</Select.Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item style={{ textAlign: 'right' }}>
          <Button onClick={onCloseResilientNodeGroupsModal} style={{ marginRight: 8 }} disabled={mutationLoading}>
            Cancel
          </Button>
          <Button type="primary" htmlType="submit" loading={mutationLoading}>
            {isEditing ? 'Save Changes' : 'Create Group'}
          </Button>
        </Form.Item>
      </Form>
    </Spin>
  );
};

export default ResilientNodeGroupForm; 