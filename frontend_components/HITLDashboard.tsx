/**
 * HITL Dashboard - Real-Time Run Monitoring
 * 
 * Add this to your brainscraper.io admin panel.
 * Connects to SSE endpoint and shows live runs + interventions.
 */

'use client';

import { useEffect, useState } from 'react';
import { toast } from 'sonner'; // or your toast library

interface Run {
  run_id: string;
  job_id: string;
  target_url: string;
  timestamp: string;
}

interface Intervention {
  intervention_id: string;
  intervention_type: string;
  reason: string;
  priority: string;
  timestamp: string;
}

interface InterventionDetail extends Intervention {
  payload?: Record<string, any>;
  status?: string;
}

export function HITLDashboard() {
  const [activeRuns, setActiveRuns] = useState<Run[]>([]);
  const [interventions, setInterventions] = useState<Intervention[]>([]);
  const [selectedIntervention, setSelectedIntervention] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  // SSE Connection
  useEffect(() => {
    const SCRAPER_API_URL = process.env.NEXT_PUBLIC_SCRAPER_API_URL || 'http://localhost:8000';
    const eventSource = new EventSource(`${SCRAPER_API_URL}/events/runs/events`);
    
    eventSource.onopen = () => {
      setIsConnected(true);
      console.log('✅ Connected to SSE');
    };
    
    eventSource.onerror = () => {
      setIsConnected(false);
      console.error('❌ SSE connection error');
    };
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'connected':
          console.log('SSE heartbeat:', data.timestamp);
          break;
          
        case 'run.started':
          setActiveRuns(prev => [...prev, data]);
          break;
          
        case 'intervention.created':
          setInterventions(prev => [...prev, data]);
          // Alert user
          toast.error(`🚨 Manual action needed: ${data.reason}`, {
            duration: 10000,
            action: {
              label: 'View',
              onClick: () => setSelectedIntervention(data.intervention_id)
            }
          });
          break;
          
        case 'intervention.resolved':
          setInterventions(prev => prev.filter(i => i.intervention_id !== data.intervention_id));
          toast.success('✅ Intervention resolved');
          break;
          
        case 'run.completed':
          setActiveRuns(prev => prev.filter(r => r.run_id !== data.run_id));
          break;
          
        case 'run.failed':
          setActiveRuns(prev => prev.filter(r => r.run_id !== data.run_id));
          break;
      }
    };
    
    return () => {
      eventSource.close();
      setIsConnected(false);
    };
  }, []);

  return (
    <div className="space-y-6 p-6">
      {/* Status Bar */}
      <div className="flex items-center justify-between border-b pb-4">
        <h1 className="text-2xl font-bold">HITL Dashboard</h1>
        <div className="flex items-center gap-4">
          <div className={`flex items-center gap-2 ${isConnected ? 'text-green-600' : 'text-red-600'}`}>
            <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-600' : 'bg-red-600'} animate-pulse`} />
            <span className="text-sm">{isConnected ? 'Connected' : 'Disconnected'}</span>
          </div>
          <div className="text-sm text-gray-500">
            {activeRuns.length} active runs
          </div>
        </div>
      </div>

      {/* Pending Interventions (Priority) */}
      {interventions.length > 0 && (
        <div className="rounded-lg border-2 border-orange-500 bg-orange-50 p-4">
          <h2 className="text-lg font-semibold text-orange-900 mb-3">
            ⚠️ {interventions.length} Pending Intervention{interventions.length !== 1 && 's'}
          </h2>
          <div className="space-y-2">
            {interventions.map(intervention => (
              <InterventionCard
                key={intervention.intervention_id}
                intervention={intervention}
                onClick={() => setSelectedIntervention(intervention.intervention_id)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Active Runs */}
      <div className="rounded-lg border p-4">
        <h2 className="text-lg font-semibold mb-3">
          🏃 Active Runs
        </h2>
        {activeRuns.length === 0 ? (
          <p className="text-sm text-gray-500">No active runs</p>
        ) : (
          <div className="space-y-2">
            {activeRuns.map(run => (
              <RunCard key={run.run_id} run={run} />
            ))}
          </div>
        )}
      </div>

      {/* Intervention Modal */}
      {selectedIntervention && (
        <InterventionModal
          interventionId={selectedIntervention}
          onClose={() => setSelectedIntervention(null)}
        />
      )}
    </div>
  );
}

function RunCard({ run }: { run: Run }) {
  return (
    <div className="flex items-center justify-between p-3 bg-blue-50 rounded border border-blue-200">
      <div>
        <div className="text-sm font-medium">Run {run.run_id.substring(0, 8)}...</div>
        <div className="text-xs text-gray-600 mt-1">{run.target_url.substring(0, 60)}...</div>
      </div>
      <div className="flex items-center gap-2">
        <div className="h-2 w-2 rounded-full bg-blue-600 animate-pulse" />
        <span className="text-xs text-blue-700">Running</span>
      </div>
    </div>
  );
}

function InterventionCard({ intervention, onClick }: { intervention: Intervention; onClick: () => void }) {
  const priorityColors = {
    low: 'bg-gray-100 text-gray-700',
    normal: 'bg-blue-100 text-blue-700',
    high: 'bg-orange-100 text-orange-700',
    critical: 'bg-red-100 text-red-700',
  };

  return (
    <button
      onClick={onClick}
      className="w-full flex items-center justify-between p-3 bg-white rounded border border-orange-200 hover:border-orange-400 transition-colors text-left"
    >
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium capitalize">
            {intervention.intervention_type.replace('_', ' ')}
          </span>
          <span className={`text-xs px-2 py-0.5 rounded ${priorityColors[intervention.priority as keyof typeof priorityColors]}`}>
            {intervention.priority}
          </span>
        </div>
        <div className="text-xs text-gray-600">
          Reason: {intervention.reason}
        </div>
      </div>
      <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
      </svg>
    </button>
  );
}

function InterventionModal({ interventionId, onClose }: { interventionId: string; onClose: () => void }) {
  const [intervention, setIntervention] = useState<InterventionDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch intervention details
    const SCRAPER_API_URL = process.env.NEXT_PUBLIC_SCRAPER_API_URL || 'http://localhost:8000';
    fetch(`${SCRAPER_API_URL}/interventions/${interventionId}`)
      .then(res => res.json())
      .then(data => {
        setIntervention(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to fetch intervention:', err);
        toast.error('Failed to load intervention details');
        onClose();
      });
  }, [interventionId, onClose]);

  const handleResolve = async () => {
    const SCRAPER_API_URL = process.env.NEXT_PUBLIC_SCRAPER_API_URL || 'http://localhost:8000';
    
    // For now, simple resolution
    // In full implementation, would show session capture UI
    try {
      await fetch(`${SCRAPER_API_URL}/interventions/${interventionId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resolution: {
            action: 'manual_completion',
            completed_at: new Date().toISOString()
          },
          resolved_by: 'user'
        })
      });
      
      toast.success('Intervention resolved');
      onClose();
    } catch (err) {
      toast.error('Failed to resolve intervention');
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-auto">
        <div className="p-6">
          <div className="flex items-start justify-between mb-4">
            <h2 className="text-xl font-bold">Intervention Required</h2>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {loading ? (
            <div className="py-8 text-center text-gray-500">Loading...</div>
          ) : intervention ? (
            <>
              <div className="space-y-4 mb-6">
                <div>
                  <label className="text-sm font-medium text-gray-700">Type</label>
                  <p className="mt-1 text-sm capitalize">{intervention.intervention_type.replace('_', ' ')}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700">Reason</label>
                  <p className="mt-1 text-sm">{intervention.reason}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700">Priority</label>
                  <p className="mt-1 text-sm capitalize">{intervention.priority}</p>
                </div>
                {intervention.payload && (
                  <div>
                    <label className="text-sm font-medium text-gray-700">Details</label>
                    <pre className="mt-1 text-xs bg-gray-50 p-3 rounded overflow-auto">
                      {JSON.stringify(intervention.payload, null, 2)}
                    </pre>
                  </div>
                )}
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded p-4 mb-6">
                <p className="text-sm text-blue-900">
                  <strong>What to do:</strong> Complete this task manually using your browser, then click "Mark as Resolved" below.
                </p>
                {intervention.payload?.url && (
                  <a
                    href={intervention.payload.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-2 inline-block text-sm text-blue-600 hover:text-blue-800 underline"
                  >
                    Open site in new tab →
                  </a>
                )}
              </div>

              <div className="flex gap-3">
                <button
                  onClick={handleResolve}
                  className="flex-1 bg-green-600 text-white py-2 px-4 rounded hover:bg-green-700 transition-colors"
                >
                  Mark as Resolved
                </button>
                <button
                  onClick={onClose}
                  className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
