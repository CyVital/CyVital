import { useState, useRef } from 'react';
import { DashboardSidebar } from './components/DashboardSidebar';
import { ECGChart } from './components/ECGChart';
import { ExportPanel } from './components/ExportPanel';
import { StatsDisplay } from './components/StatsDisplay';
import { SelectionExportDialog } from './components/SelectionExportDialog';
import { Toaster } from './components/ui/sonner';
import { Play, Pause } from 'lucide-react';
import { Button } from './components/ui/button';

export default function App() {
  const [selectedSensor, setSelectedSensor] = useState<'ECG' | 'EMG' | 'Pulse Oximeter' | 'Reaction Time'>('ECG');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isSelectionPaused, setIsSelectionPaused] = useState(false);
  const [isSelectionDialogOpen, setIsSelectionDialogOpen] = useState(false);
  const [selectedData, setSelectedData] = useState<Array<{ timestamp: number; value: number; sensor: string }>>([]);
  const recordedDataRef = useRef<Array<{ timestamp: number; value: number; sensor: string }>>([]);
  const allDataHistoryRef = useRef<Array<{ timestamp: number; value: number; sensor: string }>>([]);

  const handleToggleRecording = () => {
    if (!isRecording) {
      // Start recording - clear previous data
      recordedDataRef.current = [];
    }
    setIsRecording(!isRecording);
  };

  const addRecordedData = (value: number, timestamp: number) => {
    // Always add to history for selection purposes
    allDataHistoryRef.current.push({
      timestamp,
      value,
      sensor: selectedSensor
    });
    
    // Keep only last 1000 points in history to prevent memory issues
    if (allDataHistoryRef.current.length > 1000) {
      allDataHistoryRef.current = allDataHistoryRef.current.slice(-1000);
    }
    
    // Add to recorded data only if recording is active
    if (isRecording) {
      recordedDataRef.current.push({
        timestamp,
        value,
        sensor: selectedSensor
      });
    }
  };

  const handleSelectionComplete = (data: Array<{ timestamp: number; value: number; sensor: string }>) => {
    setSelectedData(data);
    setIsSelectionPaused(true);
    setIsSelectionDialogOpen(true);
  };

  const handleCloseSelectionDialog = () => {
    setIsSelectionDialogOpen(false);
    setIsSelectionPaused(false);
    setSelectedData([]);
  };

  return (
    <div className="flex h-screen bg-[#0a0e0a] overflow-hidden">
      <Toaster theme="dark" />
      
      {/* Sidebar */}
      <DashboardSidebar
        selectedSensor={selectedSensor}
        onSensorChange={setSelectedSensor}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="border-b border-[#ff0040]/20 bg-black/50 backdrop-blur-sm">
          <div className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-[#ff0040] text-2xl tracking-tight">
                  {selectedSensor} Monitor
                </h1>
                <p className="text-[#ffea00]/60 text-sm mt-0.5">
                  Real-time biomedical signal analysis
                </p>
              </div>
              <div className="flex items-center gap-3">
                {/* Play/Pause Button */}
                <Button
                  onClick={handleToggleRecording}
                  className={`${
                    isRecording 
                      ? 'bg-[#ff0040]/20 hover:bg-[#ff0040]/30 border-[#ff0040]/50' 
                      : 'bg-[#ffea00]/20 hover:bg-[#ffea00]/30 border-[#ffea00]/50'
                  } border transition-all duration-200 shadow-[0_0_15px_rgba(255,234,0,0.2)]`}
                  size="icon"
                >
                  {isRecording ? (
                    <Pause className="h-5 w-5 text-[#ff0040]" />
                  ) : (
                    <Play className="h-5 w-5 text-[#ffea00]" />
                  )}
                </Button>
                
                {/* Recording Status Indicator */}
                <div className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-all duration-200 ${
                  isRecording 
                    ? 'bg-[#ff0040]/5 border-[#ff0040]/20' 
                    : 'bg-gray-500/5 border-gray-500/20'
                }`}>
                  <div className={`h-2 w-2 rounded-full ${
                    isRecording 
                      ? 'bg-[#ff0040] animate-pulse shadow-[0_0_10px_rgba(255,0,64,0.8)]' 
                      : 'bg-gray-500'
                  }`}></div>
                  <span className={`text-sm ${isRecording ? 'text-[#ffea00]' : 'text-gray-500'}`}>
                    {isRecording ? 'Recording' : 'Paused'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </header>

        {/* Main Chart Area */}
        <main className="flex-1 p-4 overflow-auto">
          <div className="max-w-7xl mx-auto h-full flex flex-col">
            {/* Stats */}
            <StatsDisplay sensorType={selectedSensor} />

            {/* Chart Container */}
            <div className="flex-1 rounded-lg bg-black border border-[#ff0040]/20 p-6 shadow-[0_0_30px_rgba(255,0,64,0.1)]">
              <ECGChart 
                sensorType={selectedSensor} 
                isRecording={isRecording}
                onDataPoint={addRecordedData}
                isPaused={isSelectionPaused}
                onSelectionComplete={handleSelectionComplete}
                allDataHistory={allDataHistoryRef.current}
              />
            </div>

            {/* Grid background effect */}
            <div 
              className="fixed inset-0 pointer-events-none opacity-[0.02]"
              style={{
                backgroundImage: `
                  linear-gradient(#ff0040 1px, transparent 1px),
                  linear-gradient(90deg, #ff0040 1px, transparent 1px)
                `,
                backgroundSize: '50px 50px'
              }}
            />
          </div>
        </main>

        {/* Export Panel */}
        <ExportPanel 
          sensorType={selectedSensor}
          recordedData={recordedDataRef.current}
          isRecording={isRecording}
        />
      </div>
      
      {/* Selection Export Dialog */}
      <SelectionExportDialog
        isOpen={isSelectionDialogOpen}
        onClose={handleCloseSelectionDialog}
        selectedData={selectedData}
        sensorType={selectedSensor}
      />
    </div>
  );
}
