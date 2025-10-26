import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from './ui/dialog';
import { Button } from './ui/button';
import { FileText, Table, X } from 'lucide-react';
import { toast } from 'sonner';

interface SelectionExportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  selectedData: Array<{ timestamp: number; value: number; sensor: string }>;
  sensorType: string;
}

export function SelectionExportDialog({ isOpen, onClose, selectedData, sensorType }: SelectionExportDialogProps) {
  const handleExportCSV = () => {
    if (selectedData.length === 0) return;

    // Create CSV content
    const csvHeader = 'Timestamp,Value,Sensor\n';
    const csvRows = selectedData.map(row => 
      `${new Date(row.timestamp).toISOString()},${row.value.toFixed(6)},${row.sensor}`
    ).join('\n');
    const csvContent = csvHeader + csvRows;

    // Create and download CSV file
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${sensorType}_selection_${Date.now()}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    
    toast.success(`Exported ${selectedData.length} selected data points as CSV`, {
      description: 'Your CSV file has been downloaded.',
    });
    
    onClose();
  };

  const handleExportPDF = () => {
    toast.success(`Exporting ${selectedData.length} selected ${sensorType} data points as PDF...`, {
      description: 'Your PDF report is being generated.',
    });
    onClose();
  };

  const stats = selectedData.length > 0 ? {
    count: selectedData.length,
    min: Math.min(...selectedData.map(d => d.value)).toFixed(3),
    max: Math.max(...selectedData.map(d => d.value)).toFixed(3),
    avg: (selectedData.reduce((sum, d) => sum + d.value, 0) / selectedData.length).toFixed(3),
  } : null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="bg-black border-[#ff0040]/30 text-[#ffea00] shadow-[0_0_40px_rgba(255,0,64,0.3)]">
        <DialogHeader>
          <DialogTitle className="text-[#ff0040] text-2xl">Export Selected Data</DialogTitle>
          <DialogDescription className="text-[#ffea00]/60">
            {selectedData.length} data points selected from {sensorType} sensor
          </DialogDescription>
        </DialogHeader>

        {stats && (
          <div className="grid grid-cols-2 gap-3 my-4">
            <div className="p-3 rounded-lg bg-[#ff0040]/5 border border-[#ff0040]/20">
              <div className="text-[#ffea00]/60 text-xs mb-1">Data Points</div>
              <div className="text-[#ffea00]">{stats.count}</div>
            </div>
            <div className="p-3 rounded-lg bg-[#ff0040]/5 border border-[#ff0040]/20">
              <div className="text-[#ffea00]/60 text-xs mb-1">Average</div>
              <div className="text-[#ffea00]">{stats.avg}</div>
            </div>
            <div className="p-3 rounded-lg bg-[#ff0040]/5 border border-[#ff0040]/20">
              <div className="text-[#ffea00]/60 text-xs mb-1">Minimum</div>
              <div className="text-[#ffea00]">{stats.min}</div>
            </div>
            <div className="p-3 rounded-lg bg-[#ff0040]/5 border border-[#ff0040]/20">
              <div className="text-[#ffea00]/60 text-xs mb-1">Maximum</div>
              <div className="text-[#ffea00]">{stats.max}</div>
            </div>
          </div>
        )}

        <DialogFooter className="gap-2">
          <Button
            onClick={onClose}
            variant="outline"
            className="bg-transparent text-[#ffea00]/60 border-[#ff0040]/20 hover:bg-[#ff0040]/10 hover:text-[#ffea00]"
          >
            <X className="mr-2 h-4 w-4" />
            Cancel
          </Button>
          <Button
            onClick={handleExportPDF}
            variant="outline"
            className="bg-[#ff0040]/10 text-[#ffea00] border-[#ff0040]/30 hover:bg-[#ff0040]/20 hover:shadow-[0_0_15px_rgba(255,0,64,0.3)]"
          >
            <FileText className="mr-2 h-4 w-4" />
            Export PDF
          </Button>
          <Button
            onClick={handleExportCSV}
            className="bg-[#ff0040]/20 text-[#ffea00] border-[#ff0040]/40 hover:bg-[#ff0040]/30 hover:shadow-[0_0_15px_rgba(255,0,64,0.3)]"
          >
            <Table className="mr-2 h-4 w-4" />
            Export CSV
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

