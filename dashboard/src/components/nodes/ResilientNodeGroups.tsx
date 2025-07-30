import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Plus, Edit, Trash2, Network } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'

import ResilientNodeGroupModal from '@/components/dialogs/ResilientNodeGroupModal'
import { 
  useGetResilientNodeGroupsRoute, 
  useDeleteResilientNodeGroupRoute,
  type ResilientNodeGroupResponse 
} from '@/service/api'

const strategyLabels = {
  CLIENT_DEFAULT: 'Client Default',
  URL_TEST: 'URL Test',
  BALANCE: 'Balance',
  ROUND_ROBIN: 'Round Robin',
}

export default function ResilientNodeGroups() {
  const { t } = useTranslation()
  const [isCreateModalOpen, setCreateModalOpen] = useState(false)
  const [editingGroup, setEditingGroup] = useState<ResilientNodeGroupResponse | null>(null)
  const [deletingGroup, setDeletingGroup] = useState<ResilientNodeGroupResponse | null>(null)

  const { data: groupsData, refetch } = useGetResilientNodeGroupsRoute()
  const deleteMutation = useDeleteResilientNodeGroupRoute()

  useEffect(() => {
    const handleOpenDialog = () => {
      setCreateModalOpen(true)
    }

    window.addEventListener('openResilientGroupDialog', handleOpenDialog)
    return () => {
      window.removeEventListener('openResilientGroupDialog', handleOpenDialog)
    }
  }, [])

  const handleSuccess = () => {
    setCreateModalOpen(false)
    setEditingGroup(null)
    refetch()
  }

  const handleDelete = async () => {
    if (!deletingGroup) return
    
    try {
      await deleteMutation.mutateAsync({
        resilientNodeGroupId: deletingGroup.id,
      })
      toast.success(t('resilient_node_group.deleted_successfully'))
      setDeletingGroup(null)
      refetch()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || t('resilient_node_group.delete_error'))
    }
  }

  const groups = groupsData?.groups || []

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {groups.length === 0 ? (
          <Card className="col-span-full">
            <CardHeader className="text-center">
              <Network className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <CardTitle>No Resilient Node Groups</CardTitle>
              <CardDescription>
                Create your first resilient node group to get started with load balancing and redundancy
              </CardDescription>
            </CardHeader>
            <CardContent className="text-center">
              <Button onClick={() => setCreateModalOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Create Group
              </Button>
            </CardContent>
          </Card>
        ) : (
          groups.map((group) => (
            <Card key={group.id} className="relative">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">{group.name}</CardTitle>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setEditingGroup(group)}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setDeletingGroup(group)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                <CardDescription>
                  Strategy: {strategyLabels[group.client_strategy_hint as keyof typeof strategyLabels]}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div>
                    <p className="text-sm font-medium mb-2">Nodes ({group.node_ids?.length || 0})</p>
                    <div className="flex flex-wrap gap-2">
                      {group.node_ids?.length ? (
                        group.node_ids.map((nodeId) => (
                          <Badge key={nodeId} variant="secondary">
                            Node {nodeId}
                          </Badge>
                        ))
                      ) : (
                        <p className="text-sm text-muted-foreground">No nodes assigned</p>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      <ResilientNodeGroupModal
        open={isCreateModalOpen}
        onOpenChange={setCreateModalOpen}
        onSuccess={handleSuccess}
      />

      <ResilientNodeGroupModal
        open={!!editingGroup}
        onOpenChange={(open) => !open && setEditingGroup(null)}
        group={editingGroup}
        onSuccess={handleSuccess}
      />

      <AlertDialog open={!!deletingGroup} onOpenChange={(open) => !open && setDeletingGroup(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Resilient Node Group</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{deletingGroup?.name}"? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}