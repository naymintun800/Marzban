import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { useTranslation } from 'react-i18next'
import { UseFormReturn } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'
import { cn } from '@/lib/utils'
import { queryClient } from '@/utils/query-client'
import useDirDetection from '@/hooks/use-dir-detection'
import { useState } from 'react'
import { Loader2, Upload, FileJson, AlertCircle, CheckCircle, XCircle } from 'lucide-react'
import { LoaderButton } from '../ui/loader-button'
import useDynamicErrorHandler from "@/hooks/use-dynamic-errors.ts"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'

export interface HiddifyImportResponse {
    message: string
    total_processed: number
    successful_imports: number
    failed_imports: number
    details: {
        success: string[]
        errors: { [key: string]: string }
        warnings: string[]
    }
}

export const hiddifyImportFormSchema = z.object({
    file: z.instanceof(File, { message: 'Please select a file' }),
})

export type HiddifyImportFormValues = z.infer<typeof hiddifyImportFormSchema>

interface HiddifyImportModalProps {
    isDialogOpen: boolean
    onOpenChange: (open: boolean) => void
    form: UseFormReturn<HiddifyImportFormValues>
}

// Temporary API function - this should be auto-generated
const importHiddifyUsers = async (file: File): Promise<HiddifyImportResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await fetch('/api/users/import-hiddify', {
        method: 'POST',
        body: formData
    })
    
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Import failed' }))
        throw new Error(errorData.detail || 'Import failed')
    }
    
    return response.json()
}

export default function HiddifyImportModal({ 
    isDialogOpen, 
    onOpenChange, 
    form 
}: HiddifyImportModalProps) {
    const { t } = useTranslation()
    const dir = useDirDetection()
    const handleError = useDynamicErrorHandler()
    const [isLoading, setIsLoading] = useState(false)
    const [importResult, setImportResult] = useState<HiddifyImportResponse | null>(null)
    const [selectedFile, setSelectedFile] = useState<File | null>(null)

    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0]
        if (file) {
            // Validate file type
            if (file.type !== 'application/json' && !file.name.endsWith('.json')) {
                toast.error(t('hiddifyImport.invalidFileType', { 
                    defaultValue: 'Please select a valid JSON file' 
                }))
                return
            }
            
            setSelectedFile(file)
            form.setValue('file', file)
            form.clearErrors('file')
        }
    }

    const onSubmit = async (values: HiddifyImportFormValues) => {
        setIsLoading(true)
        setImportResult(null)
        
        try {
            const result = await importHiddifyUsers(values.file)
            setImportResult(result)
            
            // Show success toast with summary
            toast.success(
                t('hiddifyImport.importComplete', {
                    defaultValue: 'Import completed',
                }),
                {
                    description: t('hiddifyImport.importSummary', {
                        successful: result.successful_imports,
                        total: result.total_processed,
                        defaultValue: '{successful} of {total} users imported successfully'
                    })
                }
            )

            // Invalidate users queries to refresh the user list
            queryClient.invalidateQueries({ queryKey: ['/api/users'] })
            
        } catch (error: any) {
            console.error('Import error:', error)
            const fields = ['file']
            handleError({ error, fields, form, contextKey: "hiddifyImport" })
        } finally {
            setIsLoading(false)
        }
    }

    const handleClose = () => {
        onOpenChange(false)
        setImportResult(null)
        setSelectedFile(null)
        form.reset()
    }

    const renderImportResults = () => {
        if (!importResult) return null

        return (
            <div className="space-y-4">
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <CheckCircle className="h-5 w-5 text-green-500" />
                            {t('hiddifyImport.importResults', { defaultValue: 'Import Results' })}
                        </CardTitle>
                        <CardDescription>
                            {importResult.message}
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-3 gap-4">
                            <div className="text-center">
                                <div className="text-2xl font-bold text-blue-600">
                                    {importResult.total_processed}
                                </div>
                                <div className="text-sm text-muted-foreground">
                                    {t('hiddifyImport.totalProcessed', { defaultValue: 'Total Processed' })}
                                </div>
                            </div>
                            <div className="text-center">
                                <div className="text-2xl font-bold text-green-600">
                                    {importResult.successful_imports}
                                </div>
                                <div className="text-sm text-muted-foreground">
                                    {t('hiddifyImport.successful', { defaultValue: 'Successful' })}
                                </div>
                            </div>
                            <div className="text-center">
                                <div className="text-2xl font-bold text-red-600">
                                    {importResult.failed_imports}
                                </div>
                                <div className="text-sm text-muted-foreground">
                                    {t('hiddifyImport.failed', { defaultValue: 'Failed' })}
                                </div>
                            </div>
                        </div>

                        {/* Success details */}
                        {importResult.details.success.length > 0 && (
                            <div>
                                <h4 className="font-medium text-green-600 mb-2 flex items-center gap-2">
                                    <CheckCircle className="h-4 w-4" />
                                    {t('hiddifyImport.successfulImports', { defaultValue: 'Successful Imports' })}
                                </h4>
                                <ScrollArea className="h-32 w-full border rounded p-2">
                                    <div className="space-y-1">
                                        {importResult.details.success.map((username, index) => (
                                            <Badge key={index} variant="success" className="mr-1 mb-1">
                                                {username}
                                            </Badge>
                                        ))}
                                    </div>
                                </ScrollArea>
                            </div>
                        )}

                        {/* Error details */}
                        {Object.keys(importResult.details.errors).length > 0 && (
                            <div>
                                <h4 className="font-medium text-red-600 mb-2 flex items-center gap-2">
                                    <XCircle className="h-4 w-4" />
                                    {t('hiddifyImport.failedImports', { defaultValue: 'Failed Imports' })}
                                </h4>
                                <ScrollArea className="h-32 w-full border rounded p-2">
                                    <div className="space-y-2">
                                        {Object.entries(importResult.details.errors).map(([username, error], index) => (
                                            <div key={index} className="text-sm">
                                                <Badge variant="destructive" className="mr-2">
                                                    {username}
                                                </Badge>
                                                <span className="text-muted-foreground">{error}</span>
                                            </div>
                                        ))}
                                    </div>
                                </ScrollArea>
                            </div>
                        )}

                        {/* Warnings */}
                        {importResult.details.warnings.length > 0 && (
                            <div>
                                <h4 className="font-medium text-yellow-600 mb-2 flex items-center gap-2">
                                    <AlertCircle className="h-4 w-4" />
                                    {t('hiddifyImport.warnings', { defaultValue: 'Warnings' })}
                                </h4>
                                <ScrollArea className="h-24 w-full border rounded p-2">
                                    <div className="space-y-1">
                                        {importResult.details.warnings.map((warning, index) => (
                                            <div key={index} className="text-sm text-yellow-600">
                                                {warning}
                                            </div>
                                        ))}
                                    </div>
                                </ScrollArea>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        )
    }

    return (
        <Dialog open={isDialogOpen} onOpenChange={handleClose}>
            <DialogContent className="max-w-full sm:max-w-[90vw] lg:max-w-[600px] h-full lg:h-auto" onOpenAutoFocus={(e) => e.preventDefault()}>
                <DialogHeader>
                    <DialogTitle
                        className={cn('text-xl text-start font-semibold', dir === 'rtl' && 'sm:text-right')}>
                        {t('hiddifyImport.title', { defaultValue: 'Import Hiddify Users' })}
                    </DialogTitle>
                    <p className={cn('text-sm text-muted-foreground text-start', dir === 'rtl' && 'sm:text-right')}>
                        {t('hiddifyImport.description', { 
                            defaultValue: 'Import users from a Hiddify JSON backup file' 
                        })}
                    </p>
                </DialogHeader>

                <div className="space-y-6">
                    {/* Import form */}
                    {!importResult && (
                        <Form {...form}>
                            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                                <FormField
                                    control={form.control}
                                    name="file"
                                    render={({ field: { onChange, ...field } }) => (
                                        <FormItem>
                                            <FormLabel>{t('hiddifyImport.selectFile', { defaultValue: 'Select Hiddify JSON File' })}</FormLabel>
                                            <FormControl>
                                                <div className="space-y-4">
                                                    <div className="flex items-center gap-4">
                                                        <Input
                                                            type="file"
                                                            accept=".json,application/json"
                                                            onChange={handleFileChange}
                                                            className="file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-primary-foreground hover:file:bg-primary/80"
                                                        />
                                                    </div>
                                                    
                                                    {selectedFile && (
                                                        <Card>
                                                            <CardContent className="pt-4">
                                                                <div className="flex items-center gap-3">
                                                                    <FileJson className="h-8 w-8 text-blue-500" />
                                                                    <div className="flex-1">
                                                                        <div className="font-medium">{selectedFile.name}</div>
                                                                        <div className="text-sm text-muted-foreground">
                                                                            {(selectedFile.size / 1024).toFixed(1)} KB
                                                                        </div>
                                                                    </div>
                                                                </div>
                                                            </CardContent>
                                                        </Card>
                                                    )}
                                                </div>
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <Card>
                                    <CardHeader>
                                        <CardTitle className="text-sm flex items-center gap-2">
                                            <AlertCircle className="h-4 w-4" />
                                            {t('hiddifyImport.importNotes', { defaultValue: 'Import Notes' })}
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent className="text-sm text-muted-foreground space-y-2">
                                        <ul className="list-disc list-inside space-y-1">
                                            <li>{t('hiddifyImport.note1', { defaultValue: 'Only JSON files from Hiddify backups are supported' })}</li>
                                            <li>{t('hiddifyImport.note2', { defaultValue: 'Duplicate usernames will be automatically handled with suffixes' })}</li>
                                            <li>{t('hiddifyImport.note3', { defaultValue: 'Invalid user data will be skipped and reported' })}</li>
                                            <li>{t('hiddifyImport.note4', { defaultValue: 'Large files may take some time to process' })}</li>
                                        </ul>
                                    </CardContent>
                                </Card>

                                <div className="flex flex-col sm:flex-row justify-end gap-2">
                                    <Button 
                                        variant="outline" 
                                        onClick={handleClose}
                                        disabled={isLoading}
                                        className="w-full sm:w-auto"
                                    >
                                        {t('cancel', { defaultValue: 'Cancel' })}
                                    </Button>
                                    <LoaderButton
                                        type="submit"
                                        disabled={!selectedFile || isLoading}
                                        isLoading={isLoading}
                                        loadingText={t('hiddifyImport.importing', { defaultValue: 'Importing...' })}
                                        className="w-full sm:w-auto"
                                    >
                                        <Upload className="h-4 w-4 mr-2" />
                                        {t('hiddifyImport.import', { defaultValue: 'Import Users' })}
                                    </LoaderButton>
                                </div>
                            </form>
                        </Form>
                    )}

                    {/* Import results display */}
                    {importResult && (
                        <div className="space-y-4">
                            {renderImportResults()}
                            
                            <div className="flex justify-end">
                                <Button onClick={handleClose}>
                                    {t('close', { defaultValue: 'Close' })}
                                </Button>
                            </div>
                        </div>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    )
}