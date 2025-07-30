import { useState } from 'react'
import { toast } from 'sonner'
import { Plus } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function ResilientNodeGroups() {
  const [isCreateModalOpen, setCreateModalOpen] = useState(false)

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

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>No Groups Found</CardTitle>
            <CardDescription>
              Create your first resilient node group to get started
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Resilient node groups allow you to configure load balancing and redundancy across multiple nodes.
            </p>
          </CardContent>
        </Card>
      </div>

      {isCreateModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h2 className="text-lg font-semibold mb-4">Create Resilient Node Group</h2>
            <p className="text-sm text-muted-foreground mb-4">
              This feature is currently being implemented. Please check back later.
            </p>
            <div className="flex justify-end">
              <Button variant="outline" onClick={() => setCreateModalOpen(false)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}