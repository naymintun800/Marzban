import React, { useState, useEffect } from 'react'
import { toast } from 'sonner'
import { Upload, FileText, CheckCircle, XCircle, Trash2, Users, Settings } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'

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
import { LoaderButton } from '@/components/ui/loader-button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Alert, AlertDescription } from '@/components/ui/alert'

import { 
  useImportHiddifyUsers, 
  useDeleteImportedUsers,
  type HiddifyImportConfig,
  type HiddifyImportResponse 
} from '@/service/api'

const formSchema = z.object({
  enable_smart_username_parsing: z.boolean().default(true),
  group_ids: z.array(z.number()).default([]),
  user_template_id: z.number().optional(),
})

type FormData = z.infer<typeof formSchema>

interface HiddifyImportModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}

export default function HiddifyImportModal({
  open,
  onOpenChange,
  onSuccess,
}: HiddifyImportModalProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [importResult, setImportResult] = useState<HiddifyImportResponse | null>(null)
  const [isImporting, setIsImporting] = useState(false)
  const [isDeletingPrevious, setIsDeletingPrevious] = useState(false)

  const importMutation = useImportHiddifyUsers()
  const deleteMutation = useDeleteImportedUsers()

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      enable_smart_username_parsing: true,
      group_ids: [],
      user_template_id: undefined,
    },
  })

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      if (!file.name.endsWith('.json')) {
        toast.error('Please select a JSON file')
        return
      }
      setSelectedFile(file)
      setImportResult(null)
    }
  }

  const handleImport = async (data: FormData) => {
    if (!selectedFile) {
      toast.error('Please select a JSON file')
      return
    }

    setIsImporting(true)
    try {
      const result = await importMutation.mutateAsync({
        config: data,
        file: selectedFile,
      })
      
      setImportResult(result)
      
      if (result.successful_imports > 0) {
        toast.success(`Successfully imported ${result.successful_imports} users`)
        if (result.failed_imports > 0) {
          toast.warning(`${result.failed_imports} imports failed`)
        }
      } else {
        toast.error('No users were imported')
      }
      
      onSuccess()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Import failed')
    } finally {
      setIsImporting(false)
    }
  }

  const handleDeletePrevious = async () => {
    setIsDeletingPrevious(true)
    try {
      const result = await deleteMutation.mutateAsync()
      toast.success(`Deleted ${result.deleted_count} previously imported users`)
      onSuccess()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Delete failed')
    } finally {
      setIsDeletingPrevious(false)
    }
  }

  const resetForm = () => {
    setSelectedFile(null)
    setImportResult(null)
    form.reset()
  }

  useEffect(() => {
    if (open) {
      resetForm()
    }
  }, [open])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Hiddify User Import
          </DialogTitle>
          <DialogDescription>
            Import users from Hiddify JSON backup files with smart username parsing and group assignment.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleImport)} className="space-y-6">
            {/* File Upload Section */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4" />
                <span className="font-medium">JSON File Selection</span>
              </div>
              
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-gray-400 transition-colors">
                <input
                  type="file"
                  accept=".json"
                  onChange={handleFileChange}
                  className="hidden"
                  id="file-upload"
                />
                <label htmlFor="file-upload" className="cursor-pointer">
                  <Upload className="h-8 w-8 mx-auto text-gray-400 mb-2" />
                  {selectedFile ? (
                    <div>
                      <p className="text-sm font-medium text-green-600">{selectedFile.name}</p>
                      <p className="text-xs text-gray-500">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-sm font-medium">Click to select Hiddify JSON file</p>
                      <p className="text-xs text-gray-500">JSON files only</p>
                    </div>
                  )}
                </label>
              </div>
            </div>

            <Separator />

            {/* Configuration Section */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Settings className="h-4 w-4" />
                <span className="font-medium">Import Configuration</span>
              </div>

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
                      <FormLabel>Smart Username Parsing</FormLabel>
                      <FormDescription>
                        Parse "NUMBER NAME" format - use number as username and name as note
                      </FormDescription>
                    </div>
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="group_ids"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Assign to Groups (Optional)</FormLabel>
                    <FormDescription>
                      Select groups to assign imported users to. Leave empty to use default group.
                    </FormDescription>
                    <div className="space-y-2">
                      <Input
                        placeholder="Enter group IDs separated by commas (e.g., 1,2,3)"
                        onChange={(e) => {
                          const ids = e.target.value
                            .split(',')
                            .map(id => parseInt(id.trim()))
                            .filter(id => !isNaN(id))
                          field.onChange(ids)
                        }}
                      />
                      {field.value.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {field.value.map(id => (
                            <Badge key={id} variant="secondary">
                              Group {id}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="user_template_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>User Template (Optional)</FormLabel>
                    <FormDescription>
                      Apply a user template to all imported users
                    </FormDescription>
                    <FormControl>
                      <Input
                        type="number"
                        placeholder="Enter template ID"
                        value={field.value || ''}
                        onChange={(e) => field.onChange(e.target.value ? parseInt(e.target.value) : undefined)}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Import Results */}
            {importResult && (
              <div className="space-y-4">
                <Separator />
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span className="font-medium">Import Results</span>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center p-4 bg-green-50 rounded-lg">
                    <div className="text-2xl font-bold text-green-600">{importResult.successful_imports}</div>
                    <div className="text-sm text-green-600">Successful</div>
                  </div>
                  <div className="text-center p-4 bg-red-50 rounded-lg">
                    <div className="text-2xl font-bold text-red-600">{importResult.failed_imports}</div>
                    <div className="text-sm text-red-600">Failed</div>
                  </div>
                </div>

                {importResult.errors.length > 0 && (
                  <Alert>
                    <XCircle className="h-4 w-4" />
                    <AlertDescription>
                      <div className="font-medium mb-2">Import Errors:</div>
                      <ul className="text-sm space-y-1 max-h-32 overflow-y-auto">
                        {importResult.errors.slice(0, 10).map((error, index) => (
                          <li key={index}>• {error}</li>
                        ))}
                        {importResult.errors.length > 10 && (
                          <li>• ... and {importResult.errors.length - 10} more errors</li>
                        )}
                      </ul>
                    </AlertDescription>
                  </Alert>
                )}

                <Alert>
                  <CheckCircle className="h-4 w-4" />
                  <AlertDescription>
                    <strong>Batch ID:</strong> {importResult.batch_id}
                    <br />
                    <span className="text-sm text-gray-600">
                      Use this ID to identify and manage these imported users.
                    </span>
                  </AlertDescription>
                </Alert>
              </div>
            )}

            <DialogFooter className="flex justify-between">
              <Button
                type="button"
                variant="destructive"
                onClick={handleDeletePrevious}
                disabled={isImporting || isDeletingPrevious}
                className="flex items-center gap-2"
              >
                <Trash2 className="h-4 w-4" />
                {isDeletingPrevious ? 'Deleting...' : 'Delete Previous Imports'}
              </Button>

              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => onOpenChange(false)}
                  disabled={isImporting}
                >
                  Close
                </Button>
                <LoaderButton
                  type="submit"
                  loading={isImporting}
                  disabled={!selectedFile || isImporting}
                >
                  Import Users
                </LoaderButton>
              </div>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}