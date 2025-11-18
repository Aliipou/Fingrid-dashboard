import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { EnergyData } from '../types/energy';

interface EnergyChartProps {
  data: EnergyData[];
  timeRange: string;
}

const EnergyChart: React.FC<EnergyChartProps> = ({ data, timeRange }) => {
  // Transform data for recharts
  const chartData = data[0]?.data.map((point, index) => ({
    time: new Date(point.timestamp).toLocaleTimeString(),
    consumption: data[0]?.data[index]?.value || 0,
    production: data[1]?.data[index]?.value || 0,
    wind: data[2]?.data[index]?.value || 0,
  })) || [];

  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="time" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="consumption" stroke="#3498db" strokeWidth={2} />
        <Line type="monotone" dataKey="production" stroke="#27ae60" strokeWidth={2} />
        <Line type="monotone" dataKey="wind" stroke="#f39c12" strokeWidth={2} />
      </LineChart>
    </ResponsiveContainer>
  );
};

export default EnergyChart;