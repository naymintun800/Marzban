import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { toast } from 'sonner'
import { Upload, FileText, CheckCircle, XCircle, Trash2 } from 'lucide-react'

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
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { LoaderButton } from '@/components/ui/loader-button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import GroupsSelector from '@/components/common/GroupsSelector'
import { useGetUserTemplates } from '@/service/api'

const formSchema = z.object({
  enable_smart_username_parsing: z.boolean().default(true),
  group_ids: z.array(z.number()).default([]),
  user_template_id: z.number().optional(),
  file: z.instanceof(File).optional().refine((file) => {
    if (!file) return false
    return file.name.endsWith('.json')
  }, 'File must be a JSON file'),
})

type FormData = z.infer<typeof formSchema>

interface HiddifyImportModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}

interface ImportResult {
  successful_imports: number
  failed_imports: number
  errors: string[]
  batch_id: string
}

export default function HiddifyImportModal({
  open,
  onOpenChange,
  onSuccess,
}: HiddifyImportModalProps) {
  const { t } = useTranslation()
  const [isImporting, setIsImporting] = useState(false)
  const [isDeletingPrevious, setIsDeletingPrevious] = useState(false)
  const [importResult, setImportResult] = useState<ImportResult | null>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      enable_smart_username_parsing: true,
      group_ids: [],
    },
  })

  const { data: userTemplates, isLoading: templatesLoading } = useGetUserTemplates({
    query: {
      staleTime: 5 * 60 * 1000,
    },
  })

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      setSelectedFile(file)
      form.setValue('file', file)
    }
  }

  const handleDeletePreviousImports = async () => {
    setIsDeletingPrevious(true)
    try {
      const response = await fetch('/api/hiddify/delete-imported', {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Delete failed')
      }

      const result = await response.json()
      toast.success(`Deleted ${result.deleted_count} previously imported users`)
      onSuccess() // Refresh user list
    } catch (error: any) {
      toast.error(error.message || 'Delete failed')
    } finally {
      setIsDeletingPrevious(false)
    }
  }

  const onSubmit = async (data: FormData) => {
    if (!selectedFile) {
      toast.error('Please select a JSON file')
      return
    }

    setIsImporting(true)
    try {
      const formData = new FormData()
      formData.append('file', selectedFile)
      formData.append('config', JSON.stringify({
        enable_smart_username_parsing: data.enable_smart_username_parsing,
        group_ids: data.group_ids,
        user_template_id: data.user_template_id,
      }))

      const response = await fetch('/api/hiddify/import', {
        method: 'POST',
        body: formData,
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Import failed')
      }

      const result: ImportResult = await response.json()
      setImportResult(result)
      
      if (result.successful_imports > 0) {
        toast.success(`Successfully imported ${result.successful_imports} users`)
        onSuccess()
      }
      
      if (result.failed_imports > 0) {
        toast.warning(`${result.failed_imports} users failed to import`)
      }

    } catch (error: any) {
      toast.error(error.message || 'Import failed')
    } finally {
      setIsImporting(false)
    }
  }

  const handleClose = () => {
    form.reset()
    setSelectedFile(null)
    setImportResult(null)
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[600px] max-h-[80vh]">
        <DialogHeader>
          <DialogTitle>Import Hiddify Users</DialogTitle>
          <DialogDescription>
            Import users from Hiddify JSON export file. Users will be created with the selected groups and template settings.
          </DialogDescription>
        </DialogHeader>

        {importResult ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center space-x-2 p-3 bg-green-50 rounded-lg">
                <CheckCircle className="h-5 w-5 text-green-600" />
                <div>
                  <div className="text-sm font-medium text-green-900">
                    Successful Imports
                  </div>
                  <div className="text-lg font-bold text-green-700">
                    {importResult.successful_imports}
                  </div>
                </div>
              </div>
              
              <div className="flex items-center space-x-2 p-3 bg-red-50 rounded-lg">
                <XCircle className="h-5 w-5 text-red-600" />
                <div>
                  <div className="text-sm font-medium text-red-900">
                    Failed Imports
                  </div>
                  <div className="text-lg font-bold text-red-700">
                    {importResult.failed_imports}
                  </div>
                </div>
              </div>
            </div>

            {importResult.errors.length > 0 && (
              <div>
                <h4 className="font-medium mb-2">Errors:</h4>
                <ScrollArea className="h-32 w-full border rounded p-3">
                  <div className="space-y-1">
                    {importResult.errors.map((error, index) => (
                      <div key={index} className="text-sm text-red-600">
                        • {error}
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </div>
            )}

            <Alert>
              <AlertDescription>
                Batch ID: {importResult.batch_id}
              </AlertDescription>
            </Alert>
          </div>
        ) : (
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              <div>
                <FormLabel>Select Hiddify JSON File</FormLabel>
                <div className="mt-2">
                  <div className="flex items-center justify-center w-full">
                    <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-gray-300 border-dashed rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100">
                      <div className="flex flex-col items-center justify-center pt-5 pb-6">
                        {selectedFile ? (
                          <>
                            <FileText className="w-8 h-8 mb-4 text-gray-500" />
                            <p className="mb-2 text-sm text-gray-500">
                              <span className="font-semibold">{selectedFile.name}</span>
                            </p>
                            <p className="text-xs text-gray-500">
                              {(selectedFile.size / 1024).toFixed(2)} KB
                            </p>
                          </>
                        ) : (
                          <>
                            <Upload className="w-8 h-8 mb-4 text-gray-500" />
                            <p className="mb-2 text-sm text-gray-500">
                              <span className="font-semibold">Click to upload</span>
                            </p>
                            <p className="text-xs text-gray-500">JSON files only</p>
                          </>
                        )}
                      </div>
                      <input
                        type="file"
                        className="hidden"
                        accept=".json"
                        onChange={handleFileChange}
                      />
                    </label>
                  </div>
                </div>
              </div>

              <FormField
                control={form.control}
                name="user_template_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>User Template (Optional)</FormLabel>
                    <FormDescription>
                      Select a template to apply default settings to imported users
                    </FormDescription>
                    <Select onValueChange={(value) => field.onChange(value ? parseInt(value) : undefined)} value={field.value?.toString() || ''}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select template (optional)" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="">
                          <span className="text-muted-foreground">No template</span>
                        </SelectItem>
                        {userTemplates?.user_templates?.map((template: any) => (
                          <SelectItem key={template.id} value={template.id.toString()}>
                            {template.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="group_ids"
                render={() => (
                  <FormItem>
                    <FormLabel>Groups</FormLabel>
                    <FormDescription>
                      Select groups to assign to imported users
                    </FormDescription>
                    <GroupsSelector
                      control={form.control}
                      name="group_ids"
                    />
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="enable_smart_username_parsing"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                    <FormControl>
                      <Checkbox
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                    </FormControl>
                    <div className="space-y-1 leading-none">
                      <FormLabel className="cursor-pointer">
                        Smart Username Parsing
                      </FormLabel>
                      <FormDescription>
                        Automatically extract clean usernames from Hiddify format
                      </FormDescription>
                    </div>
                  </FormItem>
                )}
              />
            </form>
          </Form>
        )}

        <DialogFooter>
          <div className="flex justify-between items-center w-full">
            <LoaderButton 
              variant="destructive" 
              size="sm" 
              onClick={handleDeletePreviousImports}
              loading={isDeletingPrevious}
              disabled={isImporting}
              className="flex items-center gap-2"
            >
              <Trash2 className="h-4 w-4" />
              Delete Previous Imports
            </LoaderButton>
            
            <div className="flex gap-2">
              <Button variant="outline" onClick={handleClose}>
                {importResult ? 'Close' : 'Cancel'}
              </Button>
              {!importResult && (
                <LoaderButton
                  type="submit"
                  loading={isImporting}
                  disabled={!selectedFile}
                  onClick={form.handleSubmit(onSubmit)}
                >
                  Import Users
                </LoaderButton>
              )}
            </div>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}