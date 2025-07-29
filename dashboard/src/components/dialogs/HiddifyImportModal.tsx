import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { toast } from 'sonner'
import { Upload, FileText, CheckCircle, XCircle } from 'lucide-react'

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

const protocolOptions = [
  { id: 'vmess', label: 'VMess' },
  { id: 'vless', label: 'VLESS' },
  { id: 'trojan', label: 'Trojan' },
  { id: 'shadowsocks', label: 'Shadowsocks' },
]

const formSchema = z.object({
  set_unlimited_expire: z.boolean().default(false),
  enable_smart_username_parsing: z.boolean().default(true),
  selected_protocols: z.array(z.string()).min(1, 'At least one protocol must be selected'),
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
  const [importResult, setImportResult] = useState<ImportResult | null>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      set_unlimited_expire: false,
      enable_smart_username_parsing: true,
      selected_protocols: ['vmess', 'vless', 'trojan', 'shadowsocks'],
    },
  })

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      setSelectedFile(file)
      form.setValue('file', file)
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
        set_unlimited_expire: data.set_unlimited_expire,
        enable_smart_username_parsing: data.enable_smart_username_parsing,
        selected_protocols: data.selected_protocols,
      }))

      const response = await fetch('/api/hiddify_import/import', {
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
          <DialogTitle>{t('hiddify_import.title')}</DialogTitle>
          <DialogDescription>
            {t('hiddify_import.description')}
          </DialogDescription>
        </DialogHeader>

        {importResult ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center space-x-2 p-3 bg-green-50 rounded-lg">
                <CheckCircle className="h-5 w-5 text-green-600" />
                <div>
                  <div className="text-sm font-medium text-green-900">
                    {t('hiddify_import.successful_imports')}
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
                    {t('hiddify_import.failed_imports')}
                  </div>
                  <div className="text-lg font-bold text-red-700">
                    {importResult.failed_imports}
                  </div>
                </div>
              </div>
            </div>

            {importResult.errors.length > 0 && (
              <div>
                <h4 className="font-medium mb-2">{t('hiddify_import.errors')}:</h4>
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
                {t('hiddify_import.batch_id')}: {importResult.batch_id}
              </AlertDescription>
            </Alert>
          </div>
        ) : (
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              <div>
                <FormLabel>{t('hiddify_import.select_file')}</FormLabel>
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
                              <span className="font-semibold">{t('hiddify_import.click_to_upload')}</span>
                            </p>
                            <p className="text-xs text-gray-500">{t('hiddify_import.json_only')}</p>
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
                name="selected_protocols"
                render={() => (
                  <FormItem>
                    <FormLabel>{t('hiddify_import.protocols')}</FormLabel>
                    <FormDescription>
                      {t('hiddify_import.protocols_description')}
                    </FormDescription>
                    <div className="grid grid-cols-2 gap-3">
                      {protocolOptions.map((protocol) => (
                        <FormField
                          key={protocol.id}
                          control={form.control}
                          name="selected_protocols"
                          render={({ field }) => (
                            <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                              <FormControl>
                                <Checkbox
                                  checked={field.value?.includes(protocol.id)}
                                  onCheckedChange={(checked) => {
                                    const updatedValue = checked
                                      ? [...field.value, protocol.id]
                                      : field.value?.filter((id) => id !== protocol.id)
                                    field.onChange(updatedValue)
                                  }}
                                />
                              </FormControl>
                              <FormLabel className="font-normal cursor-pointer">
                                {protocol.label}
                              </FormLabel>
                            </FormItem>
                          )}
                        />
                      ))}
                    </div>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="space-y-3">
                <FormField
                  control={form.control}
                  name="set_unlimited_expire"
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
                          {t('hiddify_import.unlimited_expire')}
                        </FormLabel>
                        <FormDescription>
                          {t('hiddify_import.unlimited_expire_description')}
                        </FormDescription>
                      </div>
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
                          {t('hiddify_import.smart_username_parsing')}
                        </FormLabel>
                        <FormDescription>
                          {t('hiddify_import.smart_username_parsing_description')}
                        </FormDescription>
                      </div>
                    </FormItem>
                  )}
                />
              </div>
            </form>
          </Form>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            {importResult ? t('common.close') : t('common.cancel')}
          </Button>
          {!importResult && (
            <LoaderButton
              type="submit"
              loading={isImporting}
              disabled={!selectedFile}
              onClick={form.handleSubmit(onSubmit)}
            >
              {t('hiddify_import.import_users')}
            </LoaderButton>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}