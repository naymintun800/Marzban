import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { useTranslation } from 'react-i18next'
import { UseFormReturn } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'
import { cn } from '@/lib/utils'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { queryClient } from '@/utils/query-client'
import useDirDetection from '@/hooks/use-dir-detection'
import { useState, useEffect } from 'react'
import { Loader2, X } from 'lucide-react'
import { LoaderButton } from '../ui/loader-button'
import useDynamicErrorHandler from "@/hooks/use-dynamic-errors.ts"
import { Badge } from '@/components/ui/badge'

// Types for resilient node groups - these should be auto-generated eventually
export enum ClientStrategyHint {
    URL_TEST = "url-test",
    FALLBACK = "fallback", 
    LOAD_BALANCE = "load-balance",
    CLIENT_DEFAULT = "client-default",
    NONE = ""
}

export interface ResilientNodeGroupResponse {
    id: number
    name: string
    client_strategy_hint: ClientStrategyHint
    nodes: NodeResponse[]
    created_at: string
    updated_at: string
}

export interface ResilientNodeGroupCreate {
    name: string
    client_strategy_hint: ClientStrategyHint
    node_ids: number[]
}

export interface ResilientNodeGroupModify {
    name?: string
    client_strategy_hint?: ClientStrategyHint
    node_ids?: number[]
}

export interface NodeResponse {
    id: number
    name: string
    address: string
    port: number
    status: string
}

export const resilientNodeGroupFormSchema = z.object({
    name: z.string().min(1, 'Name is required'),
    client_strategy_hint: z.nativeEnum(ClientStrategyHint),
    node_ids: z.array(z.number()).min(1, 'At least one node is required'),
})

export type ResilientNodeGroupFormValues = z.infer<typeof resilientNodeGroupFormSchema>

interface ResilientNodeGroupModalProps {
    isDialogOpen: boolean
    onOpenChange: (open: boolean) => void
    form: UseFormReturn<ResilientNodeGroupFormValues>
    editingGroup: boolean
    editingGroupId?: number
    nodes: NodeResponse[]
}

// Temporary API functions - these should be auto-generated
const createResilientNodeGroup = async (data: ResilientNodeGroupCreate): Promise<ResilientNodeGroupResponse> => {
    const response = await fetch('/api/resilient-node-groups', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    if (!response.ok) throw new Error('Failed to create resilient node group')
    return response.json()
}

const modifyResilientNodeGroup = async (id: number, data: ResilientNodeGroupModify): Promise<ResilientNodeGroupResponse> => {
    const response = await fetch(`/api/resilient-node-groups/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    if (!response.ok) throw new Error('Failed to modify resilient node group')
    return response.json()
}

const getResilientNodeGroup = async (id: number): Promise<ResilientNodeGroupResponse> => {
    const response = await fetch(`/api/resilient-node-groups/${id}`)
    if (!response.ok) throw new Error('Failed to get resilient node group')
    return response.json()
}

export default function ResilientNodeGroupModal({ 
    isDialogOpen, 
    onOpenChange, 
    form, 
    editingGroup, 
    editingGroupId,
    nodes 
}: ResilientNodeGroupModalProps) {
    const { t } = useTranslation()
    const dir = useDirDetection()
    const handleError = useDynamicErrorHandler()
    const [isLoading, setIsLoading] = useState(false)
    const [selectedNodes, setSelectedNodes] = useState<NodeResponse[]>([])

    // Initialize form with group data when editing
    useEffect(() => {
        if (editingGroup && editingGroupId) {
            const fetchGroupData = async () => {
                try {
                    const groupData = await getResilientNodeGroup(editingGroupId)
                    form.reset({
                        name: groupData.name,
                        client_strategy_hint: groupData.client_strategy_hint,
                        node_ids: groupData.nodes.map(node => node.id),
                    })
                    setSelectedNodes(groupData.nodes)
                } catch (error) {
                    console.error('Error fetching resilient node group data:', error)
                    toast.error(t('resilientNodeGroups.fetchFailed'))
                }
            }
            fetchGroupData()
        } else {
            // For new groups, set default values
            form.reset({
                name: '',
                client_strategy_hint: ClientStrategyHint.CLIENT_DEFAULT,
                node_ids: [],
            })
            setSelectedNodes([])
        }
    }, [editingGroup, editingGroupId, isDialogOpen])

    // Update selected nodes when node_ids change
    useEffect(() => {
        const nodeIds = form.watch('node_ids')
        if (nodeIds) {
            const selected = nodes.filter(node => nodeIds.includes(node.id))
            setSelectedNodes(selected)
        }
    }, [form.watch('node_ids'), nodes])

    const onSubmit = async (values: ResilientNodeGroupFormValues) => {
        setIsLoading(true)
        try {
            if (editingGroup && editingGroupId) {
                await modifyResilientNodeGroup(editingGroupId, values)
                toast.success(
                    t('resilientNodeGroups.editSuccess', {
                        name: values.name,
                        defaultValue: 'Resilient Node Group «{name}» has been updated successfully',
                    }),
                )
            } else {
                await createResilientNodeGroup(values)
                toast.success(
                    t('resilientNodeGroups.createSuccess', {
                        name: values.name,
                        defaultValue: 'Resilient Node Group «{name}» has been created successfully',
                    }),
                )
            }

            // Invalidate queries after successful operation
            queryClient.invalidateQueries({ queryKey: ['/api/resilient-node-groups'] })
            onOpenChange(false)
            form.reset()
        } catch (error: any) {
            const fields = ['name', 'client_strategy_hint', 'node_ids']
            handleError({ error, fields, form, contextKey: "resilientNodeGroups" })
        } finally {
            setIsLoading(false)
        }
    }

    const handleNodeToggle = (node: NodeResponse) => {
        const currentNodeIds = form.getValues('node_ids') || []
        const isSelected = currentNodeIds.includes(node.id)
        
        let newNodeIds: number[]
        if (isSelected) {
            newNodeIds = currentNodeIds.filter(id => id !== node.id)
        } else {
            newNodeIds = [...currentNodeIds, node.id]
        }
        
        form.setValue('node_ids', newNodeIds)
    }

    const removeNode = (nodeId: number) => {
        const currentNodeIds = form.getValues('node_ids') || []
        const newNodeIds = currentNodeIds.filter(id => id !== nodeId)
        form.setValue('node_ids', newNodeIds)
    }

    return (
        <Dialog open={isDialogOpen} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-full sm:max-w-[90vw] lg:max-w-[800px] h-full lg:h-auto" onOpenAutoFocus={(e) => e.preventDefault()}>
                <DialogHeader>
                    <DialogTitle
                        className={cn('text-xl text-start font-semibold', dir === 'rtl' && 'sm:text-right')}>
                        {editingGroup ? t('resilientNodeGroups.editTitle') : t('resilientNodeGroups.createTitle')}
                    </DialogTitle>
                    <p className={cn('text-sm text-muted-foreground text-start', dir === 'rtl' && 'sm:text-right')}>
                        {editingGroup ? t('resilientNodeGroups.editDescription') : t('resilientNodeGroups.createDescription')}
                    </p>
                </DialogHeader>

                <Form {...form}>
                    <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col">
                        <div className="max-h-[49dvh] overflow-y-auto pr-2 -mr-2 sm:pr-4 sm:-mr-4 sm:max-h-[65dvh] px-1 sm:px-2">
                            <div className="space-y-4">
                                <FormField
                                    control={form.control}
                                    name="name"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>{t('resilientNodeGroups.name')}</FormLabel>
                                            <FormControl>
                                                <Input 
                                                    isError={!!form.formState.errors.name}
                                                    placeholder={t('resilientNodeGroups.namePlaceholder')} 
                                                    {...field} 
                                                />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <FormField
                                    control={form.control}
                                    name="client_strategy_hint"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>{t('resilientNodeGroups.clientStrategyHint')}</FormLabel>
                                            <Select onValueChange={field.onChange} value={field.value}>
                                                <FormControl>
                                                    <SelectTrigger>
                                                        <SelectValue placeholder={t('resilientNodeGroups.selectClientStrategy')} />
                                                    </SelectTrigger>
                                                </FormControl>
                                                <SelectContent>
                                                    <SelectItem value={ClientStrategyHint.CLIENT_DEFAULT}>
                                                        {t('resilientNodeGroups.clientDefault')}
                                                    </SelectItem>
                                                    <SelectItem value={ClientStrategyHint.URL_TEST}>
                                                        {t('resilientNodeGroups.urlTest')}
                                                    </SelectItem>
                                                    <SelectItem value={ClientStrategyHint.FALLBACK}>
                                                        {t('resilientNodeGroups.fallback')}
                                                    </SelectItem>
                                                    <SelectItem value={ClientStrategyHint.LOAD_BALANCE}>
                                                        {t('resilientNodeGroups.loadBalance')}
                                                    </SelectItem>
                                                    <SelectItem value={ClientStrategyHint.NONE}>
                                                        {t('resilientNodeGroups.none')}
                                                    </SelectItem>
                                                </SelectContent>
                                            </Select>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                {/* Selected nodes display */}
                                {selectedNodes.length > 0 && (
                                    <div className="space-y-2">
                                        <FormLabel>{t('resilientNodeGroups.selectedNodes')}</FormLabel>
                                        <div className="flex flex-wrap gap-2">
                                            {selectedNodes.map((node) => (
                                                <Badge key={node.id} variant="secondary" className="flex items-center gap-1">
                                                    {node.name}
                                                    <Button
                                                        type="button"
                                                        variant="ghost"
                                                        size="sm"
                                                        className="h-4 w-4 p-0 hover:bg-destructive hover:text-destructive-foreground"
                                                        onClick={() => removeNode(node.id)}
                                                    >
                                                        <X className="h-3 w-3" />
                                                    </Button>
                                                </Badge>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Available nodes selection */}
                                <FormField
                                    control={form.control}
                                    name="node_ids"
                                    render={() => (
                                        <FormItem>
                                            <FormLabel>{t('resilientNodeGroups.availableNodes')}</FormLabel>
                                            <div className="grid grid-cols-1 gap-2 max-h-64 overflow-y-auto border rounded-md p-3">
                                                {nodes.length === 0 ? (
                                                    <p className="text-sm text-muted-foreground">{t('resilientNodeGroups.noNodesAvailable')}</p>
                                                ) : (
                                                    nodes.map((node) => {
                                                        const isSelected = form.getValues('node_ids')?.includes(node.id) || false
                                                        return (
                                                            <div
                                                                key={node.id}
                                                                className={cn(
                                                                    "flex items-center justify-between p-3 rounded-md border cursor-pointer transition-colors",
                                                                    isSelected
                                                                        ? "bg-primary/10 border-primary"
                                                                        : "hover:bg-muted/50"
                                                                )}
                                                                onClick={() => handleNodeToggle(node)}
                                                            >
                                                                <div className="flex flex-col">
                                                                    <span className="font-medium">{node.name}</span>
                                                                    <span className="text-sm text-muted-foreground">
                                                                        {node.address}:{node.port}
                                                                    </span>
                                                                </div>
                                                                <Badge 
                                                                    variant={node.status === 'connected' ? 'default' : 'destructive'}
                                                                    className="ml-2"
                                                                >
                                                                    {node.status}
                                                                </Badge>
                                                            </div>
                                                        )
                                                    })
                                                )}
                                            </div>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                            </div>
                        </div>
                        
                        <div className="flex flex-col sm:flex-row justify-end gap-2 pt-4">
                            <Button 
                                variant="outline" 
                                onClick={() => onOpenChange(false)}
                                disabled={isLoading}
                                className="w-full sm:w-auto"
                            >
                                {t('cancel')}
                            </Button>
                            <LoaderButton
                                type="submit"
                                disabled={isLoading}
                                isLoading={isLoading}
                                loadingText={editingGroup ? t('modifying') : t('creating')}
                                className="w-full sm:w-auto"
                            >
                                {editingGroup ? t('modify') : t('create')}
                            </LoaderButton>
                        </div>
                    </form>
                </Form>
            </DialogContent>
        </Dialog>
    )
}