import { Activity, Zap, Heart, Timer, ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from './ui/button';
import { cn } from './ui/utils';

interface DashboardSidebarProps {
  selectedSensor: 'ECG' | 'EMG' | 'Pulse Oximeter' | 'Reaction Time';
  onSensorChange: (sensor: 'ECG' | 'EMG' | 'Pulse Oximeter' | 'Reaction Time') => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

export function DashboardSidebar({ 
  selectedSensor, 
  onSensorChange, 
  isCollapsed,
  onToggleCollapse 
}: DashboardSidebarProps) {
  const sensors = [
    { id: 'ECG' as const, name: 'ECG', icon: Activity, description: 'Electrocardiogram' },
    { id: 'EMG' as const, name: 'EMG', icon: Zap, description: 'Electromyography' },
    { id: 'Pulse Oximeter' as const, name: 'Pulse Oximeter', icon: Heart, description: 'Blood Oxygen' },
    { id: 'Reaction Time' as const, name: 'Reaction Time', icon: Timer, description: 'Response Test' }
  ];

  return (
    <div 
      className={cn(
        "relative h-full bg-black border-r border-[#ff0040]/20 transition-all duration-300",
        isCollapsed ? "w-16" : "w-64"
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-[#ff0040]/20">
        {!isCollapsed && (
          <div>
            <h2 className="text-[#ff0040]">CyVital</h2>
            <p className="text-[#ffea00]/60 text-xs">Biomedical Monitor</p>
          </div>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggleCollapse}
          className="text-[#ffea00] hover:text-[#ffea00] hover:bg-[#ff0040]/10"
        >
          {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </Button>
      </div>

      {/* Sensor List */}
      <div className="p-2">
        <div className="space-y-1">
          {sensors.map((sensor) => {
            const Icon = sensor.icon;
            const isActive = selectedSensor === sensor.id;
            
            return (
              <button
                key={sensor.id}
                onClick={() => onSensorChange(sensor.id)}
                className={cn(
                  "w-full flex items-center gap-3 p-3 rounded-lg transition-all duration-200",
                  isActive 
                    ? "bg-[#ff0040]/20 text-[#ffea00] shadow-[0_0_20px_rgba(255,0,64,0.3)]" 
                    : "text-[#ff0040]/60 hover:text-[#ff0040] hover:bg-[#ff0040]/10"
                )}
              >
                <Icon className="h-5 w-5 flex-shrink-0" />
                {!isCollapsed && (
                  <div className="flex flex-col items-start">
                    <span className="text-sm">{sensor.name}</span>
                    <span className="text-xs opacity-70">{sensor.description}</span>
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Pulse indicator */}
      {!isCollapsed && (
        <div className="absolute bottom-4 left-4 right-4 p-3 rounded-lg bg-[#ff0040]/5 border border-[#ff0040]/20">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-[#ff0040] animate-pulse shadow-[0_0_10px_rgba(255,0,64,0.8)]"></div>
            <span className="text-xs text-[#ffea00]/80">Live Monitoring</span>
          </div>
        </div>
      )}
    </div>
  );
}
