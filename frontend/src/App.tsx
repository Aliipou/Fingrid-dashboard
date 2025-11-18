import React, { useState, useEffect } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  PieChart, Pie, Cell, BarChart, Bar, ResponsiveContainer, AreaChart, Area
} from 'recharts';
import './App.css';

// Types
interface EnergyDataPoint {
  timestamp: string;
  value: number;
  unit: string;
}

interface EnergyData {
  dataset_id: number;
  name: string;
  dataset_type: string;
  data: EnergyDataPoint[];
  last_updated: string;
}

interface DifferentialPoint {
  timestamp: string;
  production: number;
  consumption: number;
  differential: number;
  status: string;
  percentage: number;
}

interface DifferentialAnalysis {
  analysis_period: string;
  data: DifferentialPoint[];
  summary: Record<string, number>;
  generated_at: string;
}

interface PriceData {
  timestamp: string;
  price: number;
  unit: string;
  area: string;
}

// API Service
class ApiService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
  }

  async get<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  }

  // Fingrid API endpoints
  async getRealtimeConsumption(): Promise<EnergyData> {
    return this.get('/api/v1/fingrid/consumption/realtime');
  }

  async getRealtimeProduction(): Promise<EnergyData> {
    return this.get('/api/v1/fingrid/production/realtime');
  }

  async getWindProduction(): Promise<EnergyData> {
    return this.get('/api/v1/fingrid/wind/realtime');
  }

  async getConsumptionForecast(): Promise<EnergyData> {
    return this.get('/api/v1/fingrid/consumption/forecast');
  }

  async getDifferentialAnalysis(): Promise<DifferentialAnalysis> {
    return this.get('/api/v1/fingrid/differential');
  }

  async getDashboardData(): Promise<any> {
    return this.get('/api/v1/fingrid/dashboard');
  }

  // Entso-E API endpoints
  async getTomorrowPrices(): Promise<PriceData[]> {
    return this.get('/api/v1/entsoe/prices/tomorrow');
  }

  async getTodayPrices(): Promise<PriceData[]> {
    return this.get('/api/v1/entsoe/prices/today');
  }
}

const apiService = new ApiService();

// Utility functions
const formatTimestamp = (timestamp: string) => {
  return new Date(timestamp).toLocaleTimeString('fi-FI', {
    hour: '2-digit',
    minute: '2-digit'
  });
};

const formatDateTime = (timestamp: string) => {
  return new Date(timestamp).toLocaleString('fi-FI', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
};

const formatMegawatts = (value: number) => {
  return `${Math.round(value)} MW`;
};

const formatPrice = (value: number) => {
  return `${value.toFixed(2)} €/MWh`;
};

// Components
const LoadingSpinner: React.FC = () => (
  <div className="loading-spinner">
    <div className="spinner"></div>
    <p>Loading energy data...</p>
  </div>
);

const ErrorMessage: React.FC<{ message: string }> = ({ message }) => (
  <div className="error-message">
    <h3>⚠️ Error</h3>
    <p>{message}</p>
  </div>
);

const MetricCard: React.FC<{
  title: string;
  value: string;
  subtitle?: string;
  trend?: 'up' | 'down' | 'stable';
  color?: string;
}> = ({ title, value, subtitle, trend, color = '#2563eb' }) => (
  <div className="metric-card" style={{ borderLeftColor: color }}>
    <h3>{title}</h3>
    <div className="metric-value" style={{ color }}>
      {value}
      {trend && (
        <span className={`trend trend-${trend}`}>
          {trend === 'up' ? '↗' : trend === 'down' ? '↘' : '→'}
        </span>
      )}
    </div>
    {subtitle && <p className="metric-subtitle">{subtitle}</p>}
  </div>
);

const RealtimeChart: React.FC<{
  data: EnergyData[];
  title: string;
  colors: string[];
}> = ({ data, title, colors }) => {
  const chartData = React.useMemo(() => {
    if (!data.length || !data[0]?.data?.length) return [];

    const timestamps = data[0].data.map(point => point.timestamp);
    
    return timestamps.map(timestamp => {
      const point: any = { timestamp: formatTimestamp(timestamp) };
      
      data.forEach((dataset, index) => {
        const dataPoint = dataset.data.find(p => p.timestamp === timestamp);
        point[dataset.name] = dataPoint ? Math.round(dataPoint.value) : null;
      });
      
      return point;
    });
  }, [data]);

  return (
    <div className="chart-container">
      <h3>{title}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="timestamp" />
          <YAxis label={{ value: 'MW', angle: -90, position: 'insideLeft' }} />
          <Tooltip formatter={(value: any) => [`${value} MW`, '']} />
          <Legend />
          {data.map((dataset, index) => (
            <Line
              key={dataset.dataset_id}
              type="monotone"
              dataKey={dataset.name}
              stroke={colors[index % colors.length]}
              strokeWidth={2}
              dot={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

const DifferentialChart: React.FC<{ analysis: DifferentialAnalysis }> = ({ analysis }) => {
  const chartData = analysis.data.slice(-24).map(point => ({
    time: formatTimestamp(point.timestamp),
    production: Math.round(point.production),
    consumption: Math.round(point.consumption),
    differential: Math.round(point.differential),
    status: point.status
  }));

  return (
    <div className="chart-container">
      <h3>Production vs Consumption Analysis</h3>
      <div className="differential-summary">
        <div className="summary-stats">
          <span className="stat">
            <strong>Avg Differential:</strong> {analysis.summary.average_differential_mw} MW
          </span>
          <span className="stat">
            <strong>Total Surplus:</strong> {analysis.summary.total_surplus_mwh} MWh
          </span>
          <span className="stat">
            <strong>Total Deficit:</strong> {analysis.summary.total_deficit_mwh} MWh
          </span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={400}>
        <AreaChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="time" />
          <YAxis label={{ value: 'MW', angle: -90, position: 'insideLeft' }} />
          <Tooltip 
            formatter={(value: any, name: string) => [
              `${value} MW`, 
              name.charAt(0).toUpperCase() + name.slice(1)
            ]} 
          />
          <Legend />
          <Area
            type="monotone"
            dataKey="production"
            stackId="1"
            stroke="#10b981"
            fill="#10b981"
            fillOpacity={0.6}
          />
          <Area
            type="monotone"
            dataKey="consumption"
            stackId="2"
            stroke="#ef4444"
            fill="#ef4444"
            fillOpacity={0.6}
          />
          <Line
            type="monotone"
            dataKey="differential"
            stroke="#6366f1"
            strokeWidth={3}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

const PriceChart: React.FC<{ prices: PriceData[]; title: string }> = ({ prices, title }) => {
  const chartData = prices.map(price => ({
    time: formatDateTime(price.timestamp),
    price: Number(price.price.toFixed(2))
  }));

  const avgPrice = prices.reduce((sum, p) => sum + p.price, 0) / prices.length;
  const maxPrice = Math.max(...prices.map(p => p.price));
  const minPrice = Math.min(...prices.map(p => p.price));

  return (
    <div className="chart-container">
      <h3>{title}</h3>
      <div className="price-summary">
        <MetricCard title="Average" value={formatPrice(avgPrice)} color="#6366f1" />
        <MetricCard title="Minimum" value={formatPrice(minPrice)} color="#10b981" />
        <MetricCard title="Maximum" value={formatPrice(maxPrice)} color="#ef4444" />
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="time" />
          <YAxis label={{ value: '€/MWh', angle: -90, position: 'insideLeft' }} />
          <Tooltip formatter={(value: any) => [`${value} €/MWh`, 'Price']} />
          <Bar dataKey="price" fill="#6366f1" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

const EnergyMixPieChart: React.FC<{ data: EnergyData[] }> = ({ data }) => {
  const pieData = data.map((dataset, index) => {
    const latestValue = dataset.data[dataset.data.length - 1]?.value || 0;
    return {
      name: dataset.name.replace(' (Real-time)', ''),
      value: Math.round(latestValue),
      color: ['#10b981', '#3b82f6', '#f59e0b'][index] || '#6b7280'
    };
  }).filter(item => item.value > 0);

  return (
    <div className="chart-container">
      <h3>Current Energy Mix</h3>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={pieData}
            cx="50%"
            cy="50%"
            outerRadius={80}
            dataKey="value"
            label={({ name, value }) => `${name}: ${value} MW`}
          >
            {pieData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip formatter={(value: any) => [`${value} MW`, '']} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

// Main App Component
const App: React.FC = () => {
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [differentialAnalysis, setDifferentialAnalysis] = useState<DifferentialAnalysis | null>(null);
  const [tomorrowPrices, setTomorrowPrices] = useState<PriceData[]>([]);
  const [todayPrices, setTodayPrices] = useState<PriceData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [dashboard, differential, tomorrow, today] = await Promise.allSettled([
        apiService.getDashboardData(),
        apiService.getDifferentialAnalysis(),
        apiService.getTomorrowPrices(),
        apiService.getTodayPrices()
      ]);

      if (dashboard.status === 'fulfilled') {
        setDashboardData(dashboard.value);
      }

      if (differential.status === 'fulfilled') {
        setDifferentialAnalysis(differential.value);
      }

      if (tomorrow.status === 'fulfilled') {
        setTomorrowPrices(tomorrow.value);
      }

      if (today.status === 'fulfilled') {
        setTodayPrices(today.value);
      }

      setLastUpdate(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    
    // Set up auto-refresh every 5 minutes
    const interval = setInterval(fetchData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !dashboardData) {
    return <LoadingSpinner />;
  }

  if (error && !dashboardData) {
    return <ErrorMessage message={error} />;
  }

  const realtimeData = [
    dashboardData?.consumption_realtime,
    dashboardData?.production_realtime,
    dashboardData?.wind_production
  ].filter(Boolean);

  const currentValues = {
    consumption: dashboardData?.consumption_realtime?.data?.slice(-1)[0]?.value || 0,
    production: dashboardData?.production_realtime?.data?.slice(-1)[0]?.value || 0,
    wind: dashboardData?.wind_production?.data?.slice(-1)[0]?.value || 0
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>🔌 Fingrid Energy Dashboard</h1>
        <div className="header-info">
          <span>Finland Real-time Energy Data</span>
          <button onClick={fetchData} className="refresh-btn" disabled={loading}>
            {loading ? '🔄' : '🔁'} Refresh
          </button>
        </div>
      </header>

      <div className="status-bar">
        <span>Last updated: {lastUpdate.toLocaleTimeString('fi-FI')}</span>
        {error && <span className="error-indicator">⚠️ Some data unavailable</span>}
      </div>

      <main className="main-content">
        {/* Key Metrics */}
        <section className="metrics-grid">
          <MetricCard
            title="Current Consumption"
            value={formatMegawatts(currentValues.consumption)}
            subtitle="Real-time demand"
            color="#ef4444"
          />
          <MetricCard
            title="Total Production"
            value={formatMegawatts(currentValues.production)}
            subtitle="All sources"
            color="#10b981"
          />
          <MetricCard
            title="Wind Power"
            value={formatMegawatts(currentValues.wind)}
            subtitle={`${((currentValues.wind / currentValues.production) * 100).toFixed(1)}% of production`}
            color="#3b82f6"
          />
          <MetricCard
            title="Balance"
            value={formatMegawatts(currentValues.production - currentValues.consumption)}
            subtitle={currentValues.production > currentValues.consumption ? "Surplus" : "Deficit"}
            color={currentValues.production > currentValues.consumption ? "#10b981" : "#ef4444"}
          />
        </section>

        {/* Charts Grid */}
        <section className="charts-grid">
          {realtimeData.length > 0 && (
            <RealtimeChart
              data={realtimeData}
              title="Real-time Energy Data (24h)"
              colors={['#ef4444', '#10b981', '#3b82f6']}
            />
          )}

          {realtimeData.length >= 2 && (
            <EnergyMixPieChart data={realtimeData.slice(1)} />
          )}

          {differentialAnalysis && (
            <DifferentialChart analysis={differentialAnalysis} />
          )}

          {dashboardData?.consumption_forecast && (
            <div className="chart-container">
              <h3>24h Consumption Forecast</h3>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={dashboardData.consumption_forecast.data.map((point: EnergyDataPoint) => ({
                  time: formatTimestamp(point.timestamp),
                  forecast: Math.round(point.value),
                  actual: dashboardData.consumption_realtime?.data.find((p: EnergyDataPoint) => 
                    p.timestamp === point.timestamp)?.value || null
                }))}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis label={{ value: 'MW', angle: -90, position: 'insideLeft' }} />
                  <Tooltip formatter={(value: any) => [`${value} MW`, '']} />
                  <Legend />
                  <Line type="monotone" dataKey="forecast" stroke="#f59e0b" strokeWidth={2} strokeDasharray="5 5" />
                  <Line type="monotone" dataKey="actual" stroke="#ef4444" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {tomorrowPrices.length > 0 && (
            <PriceChart prices={tomorrowPrices} title="Tomorrow's Electricity Prices" />
          )}

          {todayPrices.length > 0 && (
            <PriceChart prices={todayPrices} title="Today's Electricity Prices" />
          )}
        </section>

        {/* Additional Information */}
        <section className="info-section">
          <div className="info-card">
            <h3>📊 Data Sources</h3>
            <ul>
              <li><strong>Fingrid Open Data</strong> - Real-time energy production, consumption, and forecasts</li>
              <li><strong>Entso-E Transparency Platform</strong> - Day-ahead electricity market prices</li>
              <li><strong>Update Frequency</strong> - Real-time data: ~3 minutes, Prices: Daily at 13:00 CET</li>
            </ul>
          </div>

          <div className="info-card">
            <h3>🔋 About Finnish Energy</h3>
            <p>
              Finland's electricity system is part of the Nordic electricity market. 
              The country produces energy from various sources including nuclear, hydro, 
              wind, and biomass. Real-time monitoring helps ensure grid stability and 
              efficient energy trading.
            </p>
          </div>

          {differentialAnalysis && (
            <div className="info-card">
              <h3>📈 Current Analysis</h3>
              <div className="analysis-stats">
                <div className="stat-row">
                  <span>Surplus Periods:</span>
                  <span>{differentialAnalysis.summary.surplus_periods}</span>
                </div>
                <div className="stat-row">
                  <span>Deficit Periods:</span>
                  <span>{differentialAnalysis.summary.deficit_periods}</span>
                </div>
                <div className="stat-row">
                  <span>Balanced Periods:</span>
                  <span>{differentialAnalysis.summary.balanced_periods}</span>
                </div>
              </div>
            </div>
          )}
        </section>
      </main>

      <footer className="app-footer">
        <p>
          Built with ❤️ for sustainable energy monitoring | 
          Data provided by <a href="https://www.fingrid.fi/en/" target="_blank" rel="noopener noreferrer">Fingrid</a> and 
          <a href="https://transparency.entsoe.eu/" target="_blank" rel="noopener noreferrer">Entso-E</a>
        </p>
      </footer>
    </div>
  );
};

export default App;