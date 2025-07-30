import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Plus } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import ResilientNodeGroupModal from '@/components/dialogs/ResilientNodeGroupModal'

import { 
  useGetResilientNodeGroups,
  useDeleteResilientNodeGroup,
  type ResilientNodeGroupResponse
} from '@/api'

export default function ResilientNodeGroups() {
  const { t } = useTranslation()
  const [isCreateModalOpen, setCreateModalOpen] = useState(false)
  const [editingGroup, setEditingGroup] = useState<ResilientNodeGroupResponse | null>(null)

  const { data: groupsData, isLoading, refetch } = useGetResilientNodeGroups()
  const deleteGroupMutation = useDeleteResilientNodeGroup()

  const handleDeleteGroup = async (groupId: number) => {
    try {
      await deleteGroupMutation.mutateAsync({ resilientNodeGroupId: groupId })
      toast.success(t('resilient_node_group.deleted_successfully'))
      refetch()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || t('resilient_node_group.delete_error'))
    }
  }

  const handleEditGroup = (group: ResilientNodeGroupResponse) => {
    setEditingGroup(group)
  }

  const handleModalClose = () => {
    setCreateModalOpen(false)
    setEditingGroup(null)
    refetch()
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-72 mt-2" />
          </div>
          <Skeleton className="h-10 w-40" />
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-32" />
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  const groups = groupsData?.groups || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Resilient Node Groups</h1>
          <p className="text-muted-foreground">Manage node groups for load balancing and redundancy</p>
        </div>
        <Button onClick={() => setCreateModalOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Create Group
        </Button>
      </div>

      {groups.length === 0 ? (
        <Card>
          <CardContent className="py-12">
            <div className="text-center space-y-4">
              <div className="text-6xl opacity-20">🔗</div>
              <div>
                <h3 className="text-lg font-semibold">{t('resilient_node_group.no_groups')}</h3>
                <p className="text-muted-foreground">{t('resilient_node_group.no_groups_description')}</p>
              </div>
              <Button onClick={() => setCreateModalOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                {t('resilient_node_group.create_first')}
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {groups.map((group) => (
            <Card key={group.id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">{group.name}</CardTitle>
                  <Badge variant="outline">{group.client_strategy_hint}</Badge>
                </div>
                <CardDescription>
                  {t('resilient_node_group.nodes_count', { count: group.total_nodes })}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground mb-2">
                      {t('resilient_node_group.nodes')}:
                    </p>
                    {group.nodes.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {group.nodes.map((node) => (
                          <Badge key={node.id} variant="secondary" className="text-xs">
                            {node.name}
                          </Badge>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">{t('resilient_node_group.no_nodes')}</p>
                    )}
                  </div>
                  
                  <div className="flex gap-2">
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => handleEditGroup(group)}
                      className="flex-1"
                    >
                      {t('common.edit')}
                    </Button>
                    <Button 
                      variant="destructive" 
                      size="sm" 
                      onClick={() => handleDeleteGroup(group.id)}
                      disabled={deleteGroupMutation.isPending}
                      className="flex-1"
                    >
                      {t('common.delete')}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <ResilientNodeGroupModal
        open={isCreateModalOpen || editingGroup !== null}
        onOpenChange={(open) => {
          if (!open) handleModalClose()
        }}
        group={editingGroup}
        onSuccess={handleModalClose}
      />
    </div>
  )
}