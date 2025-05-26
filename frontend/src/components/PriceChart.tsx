import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { PriceData } from '../types/energy';

interface PriceChartProps {
  data: PriceData[];
}

const PriceChart: React.FC<PriceChartProps> = ({ data }) => {
  const chartData = data.map(point => ({
    hour: new Date(point.timestamp).getHours(),
    price: point.price,
    time: new Date(point.timestamp).toLocaleTimeString('fi-FI', { hour: '2-digit' })
  }));

  return (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="time" />
        <YAxis />
        <Tooltip formatter={(value) => [`${value} €/MWh`, 'Price']} />
        <Bar dataKey="price" fill="#8884d8" />
      </BarChart>
    </ResponsiveContainer>
  );
};

export default PriceChart;