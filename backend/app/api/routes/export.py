# backend/app/api/routes/export.py
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from datetime import datetime, timedelta
from typing import Optional, List
import csv
import json
import io
import zipfile
from app.services.fingrid_service import fingrid_service
from app.services.entsoe_service import entsoe_service
from app.models.energy import DatasetType
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class ExportService:
    """Service for exporting energy data in various formats"""
    
    def __init__(self):
        self.supported_formats = ["csv", "json", "excel", "xml"]
    
    async def export_fingrid_data(
        self,
        dataset_type: DatasetType,
        start_date: datetime,
        end_date: datetime,
        format_type: str = "csv"
    ) -> bytes:
        """Export Fingrid data in specified format"""
        try:
            # Get data based on type
            if dataset_type == DatasetType.CONSUMPTION_REALTIME:
                data = await fingrid_service.get_consumption_realtime(start_date, end_date)
                filename_prefix = "consumption_realtime"
            elif dataset_type == DatasetType.PRODUCTION_REALTIME:
                data = await fingrid_service.get_production_realtime(start_date, end_date)
                filename_prefix = "production_realtime"
            elif dataset_type == DatasetType.WIND_PRODUCTION:
                data = await fingrid_service.get_wind_production(start_date, end_date)
                filename_prefix = "wind_production"
            elif dataset_type == DatasetType.CONSUMPTION_FORECAST:
                data = await fingrid_service.get_consumption_forecast(start_date, end_date)
                filename_prefix = "consumption_forecast"
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported dataset type: {dataset_type}"
                )
            
            if not data.data:
                raise HTTPException(
                    status_code=404,
                    detail="No data available for export"
                )
            
            # Convert data to exportable format
            export_data = []
            for point in data.data:
                export_data.append({
                    "timestamp": point.timestamp.isoformat(),
                    "value": point.value,
                    "unit": point.unit
                })
            
            # Export based on format
            if format_type == "csv":
                return self._export_csv(export_data, filename_prefix)
            elif format_type == "json":
                return self._export_json(export_data, data.dict(), filename_prefix)
            elif format_type == "excel":
                return self._export_excel(export_data, filename_prefix)
            elif format_type == "xml":
                return self._export_xml(export_data, filename_prefix)
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported format: {format_type}"
                )
                
        except Exception as e:
            logger.error(f"Error exporting data: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Export failed: {str(e)}"
            )
    
    def _export_csv(self, data: List[dict], filename_prefix: str) -> bytes:
        """Export data as CSV"""
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        
        # Convert to bytes
        csv_content = output.getvalue()
        return csv_content.encode('utf-8')
    
    def _export_json(self, data: List[dict], metadata: dict, filename_prefix: str) -> bytes:
        """Export data as JSON with metadata"""
        export_object = {
            "metadata": {
                "export_timestamp": datetime.utcnow().isoformat(),
                "dataset_name": metadata.get("name", "Unknown"),
                "dataset_id": metadata.get("dataset_id", 0),
                "total_records": len(data),
                "source": "Fingrid Open Data API"
            },
            "data": data
        }
        
        json_content = json.dumps(export_object, indent=2, ensure_ascii=False)
        return json_content.encode('utf-8')
    
    def _export_excel(self, data: List[dict], filename_prefix: str) -> bytes:
        """Export data as Excel file"""
        try:
            import pandas as pd
            import io
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Create Excel file in memory
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Energy Data', index=False)
                
                # Add metadata sheet
                metadata_df = pd.DataFrame([
                    ["Export Date", datetime.utcnow().isoformat()],
                    ["Dataset", filename_prefix],
                    ["Total Records", len(data)],
                    ["Source", "Fingrid Open Data API"]
                ], columns=["Field", "Value"])
                
                metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
            
            output.seek(0)
            return output.getvalue()
            
        except ImportError:
            raise HTTPException(
                status_code=500,
                detail="Excel export requires pandas and openpyxl libraries"
            )
    
    def _export_xml(self, data: List[dict], filename_prefix: str) -> bytes:
        """Export data as XML"""
        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_lines.append('<energy_data>')
        xml_lines.append(f'  <metadata>')
        xml_lines.append(f'    <export_timestamp>{datetime.utcnow().isoformat()}</export_timestamp>')
        xml_lines.append(f'    <dataset>{filename_prefix}</dataset>')
        xml_lines.append(f'    <total_records>{len(data)}</total_records>')
        xml_lines.append(f