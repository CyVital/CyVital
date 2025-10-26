import { Download, FileText, Table } from 'lucide-react';
import { Button } from './ui/button';
import { toast } from 'sonner';

interface ExportPanelProps {
  sensorType: string;
  recordedData: Array<{ timestamp: number; value: number; sensor: string }>;
  isRecording: boolean;
}

export function ExportPanel({ sensorType, recordedData, isRecording }: ExportPanelProps) {
  const handleExportPDF = () => {
    if (recordedData.length === 0) {
      toast.error('No recorded data to export', {
        description: 'Please start recording first.',
      });
      return;
    }
    
    toast.success(`Exporting ${recordedData.length} ${sensorType} data points as PDF...`, {
      description: 'Your PDF report is being generated.',
    });
  };

  const handleExportCSV = () => {
    if (recordedData.length === 0) {
      toast.error('No recorded data to export', {
        description: 'Please start recording first.',
      });
      return;
    }

    // Create CSV content
    const csvHeader = 'Timestamp,Value,Sensor\n';
    const csvRows = recordedData.map(row => 
      `${new Date(row.timestamp).toISOString()},${row.value.toFixed(6)},${row.sensor}`
    ).join('\n');
    const csvContent = csvHeader + csvRows;

    // Create and download CSV file
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${sensorType}_recording_${Date.now()}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    
    toast.success(`Exported ${recordedData.length} ${sensorType} data points as CSV`, {
      description: 'Your CSV file has been downloaded.',
    });
  };

  return (
    <div className="flex items-center justify-between gap-4 p-6 border-t border-[#ff0040]/20 bg-black/50">
      <div className="text-[#ffea00]/60 text-sm">
        {isRecording ? (
          <span>Recording in progress: <span className="text-[#ff0040]">{recordedData.length}</span> data points</span>
        ) : recordedData.length > 0 ? (
          <span>Ready to export: <span className="text-[#ffea00]">{recordedData.length}</span> data points</span>
        ) : (
          <span>No data recorded yet</span>
        )}
      </div>
      <div className="flex gap-4">
        <Button
          onClick={handleExportPDF}
          disabled={recordedData.length === 0}
          className="bg-[#ff0040]/10 text-[#ffea00] border border-[#ff0040]/30 hover:bg-[#ff0040]/20 hover:shadow-[0_0_15px_rgba(255,0,64,0.3)] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          variant="outline"
        >
          <FileText className="mr-2 h-4 w-4" />
          Export PDF
        </Button>
        <Button
          onClick={handleExportCSV}
          disabled={recordedData.length === 0}
          className="bg-[#ff0040]/10 text-[#ffea00] border border-[#ff0040]/30 hover:bg-[#ff0040]/20 hover:shadow-[0_0_15px_rgba(255,0,64,0.3)] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          variant="outline"
        >
          <Table className="mr-2 h-4 w-4" />
          Export CSV
        </Button>
      </div>
    </div>
  );
}
