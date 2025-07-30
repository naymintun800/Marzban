import React, { useState } from 'react'
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
import { Button } from '@/components/ui/button'
import { LoaderButton } from '@/components/ui/loader-button'

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
  const [isImporting, setIsImporting] = useState(false)
  const [isDeletingPrevious, setIsDeletingPrevious] = useState(false)

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      setSelectedFile(file)
    }
  }

  const handleImport = async () => {
    if (!selectedFile) {
      toast.error('Please select a JSON file')
      return
    }

    setIsImporting(true)
    try {
      // For now, just show a message that the feature is being implemented
      toast.info('Hiddify import feature is currently being implemented')
      onSuccess()
      onOpenChange(false)
    } catch (error: any) {
      toast.error('Import failed')
    } finally {
      setIsImporting(false)
    }
  }

  const handleDeletePrevious = async () => {
    setIsDeletingPrevious(true)
    try {
      toast.info('Delete previous imports feature is being implemented')
    } catch (error: any) {
      toast.error('Delete failed')
    } finally {
      setIsDeletingPrevious(false)
    }
  }

  const handleClose = () => {
    setSelectedFile(null)
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[600px] max-h-[80vh]">
        <DialogHeader>
          <DialogTitle>Import Hiddify Users</DialogTitle>
          <DialogDescription>
            Import users from Hiddify JSON export file. This feature is currently being implemented.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium mb-2">Select Hiddify JSON File</label>
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

          <div className="p-4 bg-blue-50 rounded-lg">
            <p className="text-sm text-blue-700">
              <strong>Note:</strong> The Hiddify import feature is currently being developed. 
              This will allow you to import users with group assignments and template settings.
            </p>
          </div>
        </div>

        <DialogFooter>
          <div className="flex justify-between items-center w-full">
            <LoaderButton 
              variant="destructive" 
              size="sm" 
              onClick={handleDeletePrevious}
              loading={isDeletingPrevious}
              disabled={isImporting}
              className="flex items-center gap-2"
            >
              <Trash2 className="h-4 w-4" />
              Delete Previous Imports
            </LoaderButton>
            
            <div className="flex gap-2">
              <Button variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <LoaderButton
                type="submit"
                loading={isImporting}
                disabled={!selectedFile}
                onClick={handleImport}
              >
                Import Users
              </LoaderButton>
            </div>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}