import { useEffect, useState } from 'react';

interface StatsDisplayProps {
  sensorType: 'ECG' | 'EMG' | 'Pulse Oximeter' | 'Reaction Time';
}

export function StatsDisplay({ sensorType }: StatsDisplayProps) {
  const [stats, setStats] = useState({ primary: '0', secondary: '0', unit1: '', unit2: '' });

  useEffect(() => {
    const interval = setInterval(() => {
      switch (sensorType) {
        case 'ECG':
          setStats({
            primary: (70 + Math.random() * 10).toFixed(0),
            secondary: (120 + Math.random() * 20).toFixed(0),
            unit1: 'BPM',
            unit2: 'mV'
          });
          break;
        case 'EMG':
          setStats({
            primary: (50 + Math.random() * 50).toFixed(0),
            secondary: (200 + Math.random() * 100).toFixed(0),
            unit1: 'µV',
            unit2: 'Hz'
          });
          break;
        case 'Pulse Oximeter':
          setStats({
            primary: (95 + Math.random() * 3).toFixed(1),
            secondary: (75 + Math.random() * 10).toFixed(0),
            unit1: '%',
            unit2: 'BPM'
          });
          break;
        case 'Reaction Time':
          setStats({
            primary: (250 + Math.random() * 50).toFixed(0),
            secondary: (15 + Math.random() * 5).toFixed(0),
            unit1: 'ms',
            unit2: 'tests'
          });
          break;
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [sensorType]);

  return (
    <div className="grid grid-cols-2 gap-3 mb-4">
      <div className="p-3 rounded-lg bg-[#ff0040]/5 border border-[#ff0040]/20">
        <div className="text-[#ffea00]/60 text-xs mb-1">Primary Reading</div>
        <div className="text-[#ff0040] text-2xl tabular-nums">
          {stats.primary}
          <span className="text-sm ml-1">{stats.unit1}</span>
        </div>
      </div>
      <div className="p-3 rounded-lg bg-[#ff0040]/5 border border-[#ff0040]/20">
        <div className="text-[#ffea00]/60 text-xs mb-1">Secondary Reading</div>
        <div className="text-[#ff0040] text-2xl tabular-nums">
          {stats.secondary}
          <span className="text-sm ml-1">{stats.unit2}</span>
        </div>
      </div>
    </div>
  );
}
