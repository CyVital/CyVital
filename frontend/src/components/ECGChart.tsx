import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip } from 'recharts';
import { useEffect, useState, useRef } from 'react';

interface ECGChartProps {
  sensorType: 'ECG' | 'EMG' | 'Pulse Oximeter' | 'Reaction Time';
  isRecording: boolean;
  onDataPoint: (value: number, timestamp: number) => void;
  isPaused: boolean;
  onSelectionComplete: (selectedData: Array<{ timestamp: number; value: number; sensor: string }>) => void;
  allDataHistory: Array<{ timestamp: number; value: number; sensor: string }>;
}

// Custom tooltip component
function CustomTooltip({ active, payload, label, unit }: any) {
  if (active && payload && payload.length) {
    return (
      <div className="bg-black/90 border border-[#ff0040]/50 rounded-lg px-3 py-2 shadow-[0_0_20px_rgba(255,0,64,0.4)]">
        <p className="text-[#ffea00] text-sm">
          <span className="opacity-60">Value: </span>
          <span className="font-mono">{payload[0].value.toFixed(3)}</span>
          <span className="ml-1 text-xs">{unit}</span>
        </p>
      </div>
    );
  }
  return null;
}

export function ECGChart({ sensorType, isRecording, onDataPoint, isPaused, onSelectionComplete, allDataHistory }: ECGChartProps) {
  const [data, setData] = useState<{ time: number; value: number; timestamp: number }[]>([]);
  const [offset, setOffset] = useState(0);
  const [isSelecting, setIsSelecting] = useState(false);
  const [selectionStart, setSelectionStart] = useState<{ x: number; y: number } | null>(null);
  const [selectionEnd, setSelectionEnd] = useState<{ x: number; y: number } | null>(null);
  const chartContainerRef = useRef<HTMLDivElement>(null);

  // Generate realistic waveform data based on sensor type
  const generateWaveform = (time: number): number => {
    switch (sensorType) {
      case 'ECG':
        // ECG pattern: P wave, QRS complex, T wave
        const t = time % 1.0;
        if (t < 0.15) return 0.1 * Math.sin(t * 20);
        if (t < 0.2) return 0;
        if (t < 0.25) return -0.3;
        if (t < 0.3) return 1.0;
        if (t < 0.35) return -0.2;
        if (t < 0.4) return 0;
        if (t < 0.6) return 0.3 * Math.sin((t - 0.4) * 15);
        return 0;
      
      case 'EMG':
        // Muscle activity: random noise with bursts
        return (Math.random() - 0.5) * 0.4 + Math.sin(time * 10) * 0.3;
      
      case 'Pulse Oximeter':
        // Pulse wave: smooth periodic wave
        return Math.sin(time * 5) * 0.7;
      
      case 'Reaction Time':
        // Step function for reaction events
        return time % 3 < 0.1 ? 1.0 : Math.random() * 0.1;
      
      default:
        return 0;
    }
  };

  useEffect(() => {
    if (isPaused) return;
    
    const interval = setInterval(() => {
      setOffset(prev => prev + 0.05);
      
      const currentTimestamp = Date.now();
      const newData = Array.from({ length: 100 }, (_, i) => {
        const time = offset + i * 0.05;
        const value = generateWaveform(time);
        const timestamp = currentTimestamp + i * 50;
        
        // Record the last data point if recording is active
        if (i === 99) {
          onDataPoint(value, timestamp);
        }
        
        return {
          time: i,
          value,
          timestamp
        };
      });
      
      setData(newData);
    }, 50);

    return () => clearInterval(interval);
  }, [offset, sensorType, isRecording, isPaused]);

  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!chartContainerRef.current) return;
    const rect = chartContainerRef.current.getBoundingClientRect();
    setIsSelecting(true);
    setSelectionStart({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    setSelectionEnd({ x: e.clientX - rect.left, y: e.clientY - rect.top });
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isSelecting || !chartContainerRef.current) return;
    const rect = chartContainerRef.current.getBoundingClientRect();
    setSelectionEnd({ x: e.clientX - rect.left, y: e.clientY - rect.top });
  };

  const handleMouseUp = () => {
    if (!isSelecting || !selectionStart || !selectionEnd || !chartContainerRef.current) return;
    
    const rect = chartContainerRef.current.getBoundingClientRect();
    const chartWidth = rect.width;
    
    // Calculate the time range based on selection
    const startX = Math.min(selectionStart.x, selectionEnd.x);
    const endX = Math.max(selectionStart.x, selectionEnd.x);
    
    // Convert X coordinates to time indices (accounting for margins)
    const marginLeft = 20;
    const marginRight = 30;
    const effectiveWidth = chartWidth - marginLeft - marginRight;
    
    const startTimeIndex = Math.floor(((startX - marginLeft) / effectiveWidth) * 100);
    const endTimeIndex = Math.ceil(((endX - marginLeft) / effectiveWidth) * 100);
    
    // Get the selected data from current visible data
    const selectedVisibleData = data.slice(
      Math.max(0, startTimeIndex), 
      Math.min(100, endTimeIndex)
    );
    
    // Map to the format expected
    const selectedData = selectedVisibleData.map(d => ({
      timestamp: d.timestamp,
      value: d.value,
      sensor: sensorType
    }));
    
    if (selectedData.length > 0) {
      onSelectionComplete(selectedData);
    }
    
    setIsSelecting(false);
    setSelectionStart(null);
    setSelectionEnd(null);
  };

  const getChartConfig = () => {
    switch (sensorType) {
      case 'ECG':
        return { color: '#ff0040', label: 'mV', range: [-0.5, 1.2] };
      case 'EMG':
        return { color: '#ff0040', label: 'µV', range: [-1, 1] };
      case 'Pulse Oximeter':
        return { color: '#ff0040', label: '%', range: [-1, 1] };
      case 'Reaction Time':
        return { color: '#ff0040', label: 'Signal', range: [-0.2, 1.2] };
      default:
        return { color: '#ff0040', label: 'Value', range: [-1, 1] };
    }
  };

  const config = getChartConfig();

  const selectionRect = selectionStart && selectionEnd ? {
    x: Math.min(selectionStart.x, selectionEnd.x),
    y: Math.min(selectionStart.y, selectionEnd.y),
    width: Math.abs(selectionEnd.x - selectionStart.x),
    height: Math.abs(selectionEnd.y - selectionStart.y),
  } : null;

  return (
    <div 
      className="relative h-full w-full" 
      ref={chartContainerRef}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={() => {
        if (isSelecting) {
          setIsSelecting(false);
          setSelectionStart(null);
          setSelectionEnd(null);
        }
      }}
      style={{ cursor: isSelecting ? 'crosshair' : 'default' }}
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid 
            strokeDasharray="3 3" 
            stroke="#3a1a1a" 
            strokeOpacity={0.3}
          />
          <XAxis 
            dataKey="time" 
            stroke="#ff0040"
            strokeOpacity={0.3}
            tick={{ fill: '#ff0040', fontSize: 10 }}
            hide
          />
          <YAxis 
            stroke="#ffea00"
            strokeOpacity={0.3}
            tick={{ fill: '#ffea00', fontSize: 11 }}
            domain={config.range}
            label={{ value: config.label, angle: -90, position: 'insideLeft', fill: '#ffea00', opacity: 0.6, fontSize: 11 }}
          />
          <Tooltip 
            content={<CustomTooltip unit={config.label} />}
            cursor={{ stroke: '#ffea00', strokeWidth: 1, strokeDasharray: '5 5' }}
            isAnimationActive={false}
          />
          <Line 
            type="monotone" 
            dataKey="value" 
            stroke={config.color}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
            filter="url(#glow)"
          />
          <defs>
            <filter id="glow">
              <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
          </defs>
        </LineChart>
      </ResponsiveContainer>
      
      {/* Selection rectangle overlay */}
      {selectionRect && (
        <div
          className="absolute pointer-events-none border-2 border-[#ffea00] bg-[#ffea00]/10"
          style={{
            left: selectionRect.x,
            top: selectionRect.y,
            width: selectionRect.width,
            height: selectionRect.height,
          }}
        />
      )}
      
      {/* Instruction overlay */}
      {!isPaused && (
        <div className="absolute top-2 left-2 text-[#ffea00]/40 text-xs pointer-events-none">
          Drag to select data range
        </div>
      )}
    </div>
  );
}
