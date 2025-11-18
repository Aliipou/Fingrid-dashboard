import React from 'react';

interface MetricCardProps {
  title: string;
  value: string;
  subtitle?: string;
  trend?: 'up' | 'down' | 'stable';
  color?: string;
}

const MetricCard: React.FC<MetricCardProps> = ({ 
  title, 
  value, 
  subtitle, 
  trend = 'stable', 
  color = '#667eea' 
}) => {
  return (
    <div className="metric-card" style={{ borderLeftColor: color }}>
      <h3 className="metric-title">{title}</h3>
      <div className="metric-value" style={{ color }}>{value}</div>
      {subtitle && <p className="metric-subtitle">{subtitle}</p>}
      <div className={`metric-trend trend-${trend}`}>
        {trend === 'up' && '↗'}
        {trend === 'down' && '↘'}
        {trend === 'stable' && '→'}
      </div>
    </div>
  );
};

export default MetricCard;