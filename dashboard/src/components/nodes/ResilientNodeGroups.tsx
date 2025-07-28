import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { queryClient } from '@/utils/query-client'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Trash2, Edit, Plus, Users } from 'lucide-react'
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table'
import ResilientNodeGroupModal, {
    resilientNodeGroupFormSchema,
    ResilientNodeGroupFormValues,
    ResilientNodeGroupResponse,
    ClientStrategyHint,
    NodeResponse
} from '@/components/dialogs/ResilientNodeGroupModal'
import { cn } from '@/lib/utils'
import useDirDetection from '@/hooks/use-dir-detection'

const initialDefaultValues: Partial<ResilientNodeGroupFormValues> = {
    name: '',
    client_strategy_hint: ClientStrategyHint.CLIENT_DEFAULT,
    node_ids: [],
}

// Temporary API functions - these should be auto-generated
const getAllResilientNodeGroups = async (): Promise<ResilientNodeGroupResponse[]> => {
    const response = await fetch('/api/resilient-node-groups')
    if (!response.ok) throw new Error('Failed to fetch resilient node groups')
    return response.json()
}

const deleteResilientNodeGroup = async (id: number): Promise<void> => {
    const response = await fetch(`/api/resilient-node-groups/${id}`, {
        method: 'DELETE'
    })
    if (!response.ok) throw new Error('Failed to delete resilient node group')
}

const getAllNodes = async (): Promise<NodeResponse[]> => {
    const response = await fetch('/api/nodes')
    if (!response.ok) throw new Error('Failed to fetch nodes')
    const data = await response.json()
    return data.nodes || []
}

export default function ResilientNodeGroups() {
    const { t } = useTranslation()
    const dir = useDirDetection()
    const [isDialogOpen, setIsDialogOpen] = useState(false)
    const [editingGroup, setEditingGroup] = useState<ResilientNodeGroupResponse | null>(null)
    const [groups, setGroups] = useState<ResilientNodeGroupResponse[]>([])
    const [nodes, setNodes] = useState<NodeResponse[]>([])
    const [isLoading, setIsLoading] = useState(true)

    const form = useForm<ResilientNodeGroupFormValues>({
        resolver: zodResolver(resilientNodeGroupFormSchema),
        defaultValues: initialDefaultValues,
    })

    useEffect(() => {
        const fetchData = async () => {
            try {
                setIsLoading(true)
                const [groupsData, nodesData] = await Promise.all([
                    getAllResilientNodeGroups(),
                    getAllNodes()
                ])
                setGroups(groupsData)
                setNodes(nodesData)
            } catch (error) {
                console.error('Error fetching data:', error)
                toast.error(t('resilientNodeGroups.fetchFailed'))
            } finally {
                setIsLoading(false)
            }
        }

        fetchData()
    }, [])

    const handleCreate = () => {
        setEditingGroup(null)
        form.reset(initialDefaultValues)
        setIsDialogOpen(true)
    }

    const handleEdit = (group: ResilientNodeGroupResponse) => {
        setEditingGroup(group)
        form.reset({
            name: group.name,
            client_strategy_hint: group.client_strategy_hint,
            node_ids: group.nodes.map(node => node.id),
        })
        setIsDialogOpen(true)
    }

    const handleDelete = async (group: ResilientNodeGroupResponse) => {
        if (!confirm(t('resilientNodeGroups.deleteConfirm', { name: group.name }))) {
            return
        }

        try {
            await deleteResilientNodeGroup(group.id)
            setGroups(prev => prev.filter(g => g.id !== group.id))
            toast.success(
                t('resilientNodeGroups.deleteSuccess', {
                    name: group.name,
                    defaultValue: 'Resilient Node Group «{name}» has been deleted successfully',
                })
            )
            queryClient.invalidateQueries({ queryKey: ['/api/resilient-node-groups'] })
        } catch (error) {
            console.error('Error deleting resilient node group:', error)
            toast.error(
                t('resilientNodeGroups.deleteFailed', {
                    name: group.name,
                    defaultValue: 'Failed to delete Resilient Node Group «{name}»',
                })
            )
        }
    }

    const getStrategyLabel = (strategy: ClientStrategyHint) => {
        switch (strategy) {
            case ClientStrategyHint.URL_TEST:
                return t('resilientNodeGroups.urlTest', { defaultValue: 'URL Test' })
            case ClientStrategyHint.FALLBACK:
                return t('resilientNodeGroups.fallback', { defaultValue: 'Fallback' })
            case ClientStrategyHint.LOAD_BALANCE:
                return t('resilientNodeGroups.loadBalance', { defaultValue: 'Load Balance' })
            case ClientStrategyHint.CLIENT_DEFAULT:
                return t('resilientNodeGroups.clientDefault', { defaultValue: 'Client Default' })
            case ClientStrategyHint.NONE:
                return t('resilientNodeGroups.none', { defaultValue: 'None' })
            default:
                return strategy
        }
    }

    const handleDialogClose = () => {
        setIsDialogOpen(false)
        setEditingGroup(null)
        // Refresh data after modal closes
        setTimeout(async () => {
            try {
                const groupsData = await getAllResilientNodeGroups()
                setGroups(groupsData)
            } catch (error) {
                console.error('Error refreshing groups:', error)
            }
        }, 100)
    }

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-muted-foreground">
                    {t('resilientNodeGroups.loading', { defaultValue: 'Loading resilient node groups...' })}
                </div>
            </div>
        )
    }

    return (
        <>
            <div className="space-y-6">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-semibold">
                            {t('resilientNodeGroups.title', { defaultValue: 'Resilient Node Groups' })}
                        </h1>
                        <p className="text-muted-foreground">
                            {t('resilientNodeGroups.description', { 
                                defaultValue: 'Manage resilient node groups for load balancing and failover' 
                            })}
                        </p>
                    </div>
                    <Button onClick={handleCreate} className="flex items-center gap-2">
                        <Plus className="h-4 w-4" />
                        {t('resilientNodeGroups.create', { defaultValue: 'Create Group' })}
                    </Button>
                </div>

                {groups.length === 0 ? (
                    <Card>
                        <CardContent className="flex items-center justify-center py-8">
                            <div className="text-center">
                                <Users className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                                <h3 className="text-lg font-medium mb-2">
                                    {t('resilientNodeGroups.noGroups', { defaultValue: 'No resilient node groups' })}
                                </h3>
                                <p className="text-muted-foreground mb-4">
                                    {t('resilientNodeGroups.noGroupsDescription', { 
                                        defaultValue: 'Create your first resilient node group to get started' 
                                    })}
                                </p>
                                <Button onClick={handleCreate}>
                                    <Plus className="h-4 w-4 mr-2" />
                                    {t('resilientNodeGroups.create', { defaultValue: 'Create Group' })}
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                ) : (
                    <Card>
                        <CardHeader>
                            <CardTitle>
                                {t('resilientNodeGroups.groupList', { defaultValue: 'Resilient Node Groups' })}
                            </CardTitle>
                            <CardDescription>
                                {t('resilientNodeGroups.groupListDescription', { 
                                    defaultValue: 'Manage your resilient node groups and their configurations' 
                                })}
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead className={cn('w-[200px]', dir === 'rtl' && 'text-right')}>
                                            {t('resilientNodeGroups.name', { defaultValue: 'Name' })}
                                        </TableHead>
                                        <TableHead className={cn(dir === 'rtl' && 'text-right')}>
                                            {t('resilientNodeGroups.strategy', { defaultValue: 'Strategy' })}
                                        </TableHead>
                                        <TableHead className={cn(dir === 'rtl' && 'text-right')}>
                                            {t('resilientNodeGroups.nodes', { defaultValue: 'Nodes' })}
                                        </TableHead>
                                        <TableHead className={cn(dir === 'rtl' && 'text-right')}>
                                            {t('resilientNodeGroups.created', { defaultValue: 'Created' })}
                                        </TableHead>
                                        <TableHead className={cn('text-right', dir === 'rtl' && 'text-left')}>
                                            {t('actions', { defaultValue: 'Actions' })}
                                        </TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {groups.map((group) => (
                                        <TableRow key={group.id}>
                                            <TableCell className="font-medium">
                                                {group.name}
                                            </TableCell>
                                            <TableCell>
                                                <Badge variant="outline">
                                                    {getStrategyLabel(group.client_strategy_hint)}
                                                </Badge>
                                            </TableCell>
                                            <TableCell>
                                                <div className="flex flex-wrap gap-1">
                                                    {group.nodes.map((node) => (
                                                        <Badge key={node.id} variant="secondary" className="text-xs">
                                                            {node.name}
                                                        </Badge>
                                                    ))}
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                {new Date(group.created_at).toLocaleDateString()}
                                            </TableCell>
                                            <TableCell className={cn('text-right', dir === 'rtl' && 'text-left')}>
                                                <div className="flex items-center justify-end gap-2">
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        onClick={() => handleEdit(group)}
                                                    >
                                                        <Edit className="h-4 w-4" />
                                                    </Button>
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        onClick={() => handleDelete(group)}
                                                        className="text-destructive hover:text-destructive"
                                                    >
                                                        <Trash2 className="h-4 w-4" />
                                                    </Button>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </CardContent>
                    </Card>
                )}
            </div>

            <ResilientNodeGroupModal
                isDialogOpen={isDialogOpen}
                onOpenChange={handleDialogClose}
                form={form}
                editingGroup={!!editingGroup}
                editingGroupId={editingGroup?.id}
                nodes={nodes}
            />
        </>
    )
}