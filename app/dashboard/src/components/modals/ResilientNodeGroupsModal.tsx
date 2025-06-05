import React from 'react';
import { useDashboard } from '../../contexts/DashboardContext';
import { useResilientNodeGroupsQuery, useDeleteResilientNodeGroupMutation } from '../../hooks/useResilientNodeGroups';
import { ResilientNodeGroup } from '../../types/resilientNodeGroup';
import { Modal, Button, Table, Spin, Popconfirm, message, Space } from 'antd'; // Uncommented Ant Design
import ResilientNodeGroupForm from '../forms/ResilientNodeGroupForm';

const ResilientNodeGroupsModal: React.FC = () => {
  const {
    isResilientNodeGroupsModalOpen,
    editingResilientNodeGroup,
    onCloseResilientNodeGroupsModal,
    onEditResilientNodeGroup,
    onAddNewResilientNodeGroup,
  } = useDashboard();

  const { data: resilientNodeGroups, isLoading: isLoadingGroups, error: fetchError } = useResilientNodeGroupsQuery();
  const deleteMutation = useDeleteResilientNodeGroupMutation();

  const handleDelete = (groupId: string) => {
    deleteMutation.mutate(groupId, {
      onSuccess: () => {
        message.success('Resilient Node Group deleted successfully!');
      },
      onError: (err: any) => {
        message.error(`Failed to delete group: ${err.message}`);
      },
    });
  };

  if (fetchError) {
    message.error(`Error fetching resilient node groups: ${fetchError.message}`);
  }

  const columns = [
    { title: 'Group Name', dataIndex: 'name', key: 'name' },
    {
      title: 'Number of Nodes',
      dataIndex: 'node_ids',
      key: 'node_count',
      render: (node_ids: string[]) => node_ids?.length || 0,
    },
    { title: 'Client Strategy Hint', dataIndex: 'client_strategy_hint', key: 'client_strategy_hint' },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: ResilientNodeGroup) => (
        <Space size="middle">
          <Button type="link" onClick={() => onEditResilientNodeGroup(record)}>
            Edit
          </Button>
          <Popconfirm title="Are you sure you want to delete this group?" onConfirm={() => handleDelete(record.id)} okText="Yes" cancelText="No">
            <Button type="link" danger>
              Delete
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const showForm = !!editingResilientNodeGroup;

  return (
    <Modal
      title={showForm ? (editingResilientNodeGroup?.id ? 'Edit Resilient Node Group' : 'Add New Resilient Node Group') : 'Manage Resilient Node Groups'}
      visible={isResilientNodeGroupsModalOpen}
      onCancel={onCloseResilientNodeGroupsModal}
      footer={null}
      width={800}
      destroyOnClose
    >
      <Spin spinning={isLoadingGroups || deleteMutation.isLoading}>
        {showForm ? (
          <ResilientNodeGroupForm />
        ) : (
          <>
            <Button onClick={onAddNewResilientNodeGroup} type="primary" style={{ marginBottom: 16 }}>
              Add New Resilient Node Group
            </Button>
            <Table
              rowKey="id"
              dataSource={resilientNodeGroups || []}
              columns={columns}
              loading={isLoadingGroups}
            />
          </>
        )}
      </Spin>
    </Modal>
  );
};

export default ResilientNodeGroupsModal; 