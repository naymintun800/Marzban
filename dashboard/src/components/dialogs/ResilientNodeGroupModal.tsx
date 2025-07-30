import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { toast } from 'sonner'

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { LoaderButton } from '@/components/ui/loader-button'

import {
  useGetNodes,
  useCreateResilientNodeGroupRoute,
  useUpdateResilientNodeGroupRoute,
  type ResilientNodeGroupResponse,
  type NodeResponse
} from '@/service/api'

const clientStrategyOptions = [
  { value: 'CLIENT_DEFAULT', label: 'Client Default' },
  { value: 'URL_TEST', label: 'URL Test' },
  { value: 'BALANCE', label: 'Balance' },
  { value: 'ROUND_ROBIN', label: 'Round Robin' },
]

const formSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100, 'Name must be less than 100 characters'),
  client_strategy_hint: z.enum(['CLIENT_DEFAULT', 'URL_TEST', 'BALANCE', 'ROUND_ROBIN']),
  node_ids: z.array(z.number()).min(1, 'At least one node must be selected'),
})

type FormData = z.infer<typeof formSchema>

interface ResilientNodeGroupModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  group?: ResilientNodeGroupResponse | null
  onSuccess: () => void
}

export default function ResilientNodeGroupModal({
  open,
  onOpenChange,
  group,
  onSuccess,
}: ResilientNodeGroupModalProps) {
  const { t } = useTranslation()
  const [availableNodes, setAvailableNodes] = useState<NodeResponse[]>([])

  const { data: nodesData } = useGetNodes()
  const createMutation = useCreateResilientNodeGroupRoute()
  const updateMutation = useUpdateResilientNodeGroupRoute()

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: '',
      client_strategy_hint: 'CLIENT_DEFAULT',
      node_ids: [],
    },
  })

  useEffect(() => {
    if (nodesData) {
      setAvailableNodes(nodesData.nodes || [])
    }
  }, [nodesData])

  useEffect(() => {
    if (group) {
      form.reset({
        name: group.name,
        client_strategy_hint: group.client_strategy_hint as any,
        node_ids: group.node_ids,
      })
    } else {
      form.reset({
        name: '',
        client_strategy_hint: 'CLIENT_DEFAULT',
        node_ids: [],
      })
    }
  }, [group, form])

  const onSubmit = async (data: FormData) => {
    try {
      if (group) {
        await updateMutation.mutateAsync({
          resilientNodeGroupId: group.id,
          resilientNodeGroupModify: data,
        })
        toast.success(t('resilient_node_group.updated_successfully'))
      } else {
        await createMutation.mutateAsync({
          resilientNodeGroupCreate: data,
        })
        toast.success(t('resilient_node_group.created_successfully'))
      }
      onSuccess()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || t('resilient_node_group.save_error'))
    }
  }

  const isLoading = createMutation.isPending || updateMutation.isPending

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>
            {group 
              ? t('resilient_node_group.edit_title') 
              : t('resilient_node_group.create_title')
            }
          </DialogTitle>
          <DialogDescription>
            {group 
              ? t('resilient_node_group.edit_description')
              : t('resilient_node_group.create_description')
            }
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('resilient_node_group.name')}</FormLabel>
                  <FormControl>
                    <Input 
                      placeholder={t('resilient_node_group.name_placeholder')} 
                      {...field} 
                    />
                  </FormControl>
                  <FormDescription>
                    {t('resilient_node_group.name_description')}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="client_strategy_hint"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('resilient_node_group.strategy')}</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder={t('resilient_node_group.strategy_placeholder')} />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {clientStrategyOptions.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    {t('resilient_node_group.strategy_description')}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="node_ids"
              render={() => (
                <FormItem>
                  <FormLabel>{t('resilient_node_group.nodes')}</FormLabel>
                  <FormDescription>
                    {t('resilient_node_group.nodes_description')}
                  </FormDescription>
                  <div className="grid gap-3 max-h-60 overflow-y-auto border rounded-md p-4">
                    {availableNodes.length === 0 ? (
                      <p className="text-sm text-muted-foreground text-center py-4">
                        {t('resilient_node_group.no_available_nodes')}
                      </p>
                    ) : (
                      availableNodes.map((node) => (
                        <FormField
                          key={node.id}
                          control={form.control}
                          name="node_ids"
                          render={({ field }) => (
                            <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                              <FormControl>
                                <Checkbox
                                  checked={field.value?.includes(node.id)}
                                  onCheckedChange={(checked) => {
                                    const updatedValue = checked
                                      ? [...field.value, node.id]
                                      : field.value?.filter((id) => id !== node.id)
                                    field.onChange(updatedValue)
                                  }}
                                />
                              </FormControl>
                              <div className="space-y-1 leading-none">
                                <FormLabel className="font-normal cursor-pointer">
                                  {node.name}
                                </FormLabel>
                                <p className="text-xs text-muted-foreground">
                                  {node.address}:{node.port}
                                </p>
                              </div>
                            </FormItem>
                          )}
                        />
                      ))
                    )}
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button 
                type="button" 
                variant="outline" 
                onClick={() => onOpenChange(false)}
                disabled={isLoading}
              >
                {t('common.cancel')}
              </Button>
              <LoaderButton 
                type="submit" 
                loading={isLoading}
                disabled={availableNodes.length === 0}
              >
                {group ? t('common.update') : t('common.create')}
              </LoaderButton>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}