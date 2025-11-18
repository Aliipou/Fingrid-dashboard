// Type definitions for energy data

export interface EnergyDataPoint {
  timestamp: Date | string;
  value: number;
  unit: string;
}

export interface EnergyData {
  dataset_id: number;
  name: string;
  dataset_type: string;
  data: EnergyDataPoint[];
  last_updated: Date | string;
  metadata?: Record<string, any>;
}

export interface PriceData {
  timestamp: Date | string;
  price: number;
  unit: string;
  area: string;
}

export interface DifferentialPoint {
  timestamp: Date | string;
  production: number;
  consumption: number;
  differential: number;
  status: 'surplus' | 'deficit' | 'balanced';
  percentage: number;
}

export interface DifferentialAnalysis {
  analysis_period: string;
  data: DifferentialPoint[];
  summary: {
    total_data_points: number;
    surplus_hours: number;
    deficit_hours: number;
    balanced_hours: number;
    surplus_percentage: number;
    deficit_percentage: number;
    total_surplus_mwh: number;
    total_deficit_mwh: number;
    net_balance_mwh: number;
  };
  generated_at: Date | string;
}

export enum DatasetType {
  CONSUMPTION_REALTIME = 'consumption_realtime',
  PRODUCTION_REALTIME = 'production_realtime',
  WIND_PRODUCTION = 'wind_production',
  CONSUMPTION_FORECAST = 'consumption_forecast',
}

export interface SystemStatus {
  status: string;
  timestamp: Date | string;
  services: {
    api: boolean;
    redis: boolean;
    fingrid: boolean;
    entsoe: boolean;
  };
}
