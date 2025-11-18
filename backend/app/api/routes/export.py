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
        xml_lines.append('  <metadata>')
        xml_lines.append(f'    <export_timestamp>{datetime.utcnow().isoformat()}</export_timestamp>')
        xml_lines.append(f'    <dataset>{filename_prefix}</dataset>')
        xml_lines.append(f'    <total_records>{len(data)}</total_records>')
        xml_lines.append('    <source>Fingrid Open Data API</source>')
        xml_lines.append('  </metadata>')
        xml_lines.append('  <data_points>')

        # Add each data point
        for point in data:
            xml_lines.append('    <data_point>')
            for key, value in point.items():
                # Escape XML special characters
                value_str = str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                xml_lines.append(f'      <{key}>{value_str}</{key}>')
            xml_lines.append('    </data_point>')

        xml_lines.append('  </data_points>')
        xml_lines.append('</energy_data>')

        xml_content = '\n'.join(xml_lines)
        return xml_content.encode('utf-8')


# Initialize export service
export_service = ExportService()


# API Endpoints
@router.get("/fingrid/{dataset_type}")
async def export_fingrid_dataset(
    dataset_type: DatasetType,
    format: str = Query("csv", description="Export format: csv, json, excel, xml"),
    start_date: Optional[datetime] = Query(None, description="Start date for export"),
    end_date: Optional[datetime] = Query(None, description="End date for export")
):
    """Export Fingrid dataset in specified format"""
    try:
        # Default to last 24 hours if not specified
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(hours=24)

        # Generate export
        export_data = await export_service.export_fingrid_data(
            dataset_type,
            start_date,
            end_date,
            format
        )

        # Determine content type and filename
        content_types = {
            "csv": "text/csv",
            "json": "application/json",
            "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "xml": "application/xml"
        }

        extensions = {
            "csv": "csv",
            "json": "json",
            "excel": "xlsx",
            "xml": "xml"
        }

        filename = f"{dataset_type.value}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.{extensions[format]}"

        return Response(
            content=export_data,
            media_type=content_types[format],
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except Exception as e:
        logger.error(f"Export endpoint error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Export failed: {str(e)}"
        )


@router.get("/prices/{date_range}")
async def export_prices(
    date_range: str = Query(..., description="Date range: today, tomorrow, week"),
    format: str = Query("csv", description="Export format: csv, json, excel, xml")
):
    """Export electricity price data"""
    try:
        # Get price data based on range
        if date_range == "today":
            prices = await entsoe_service.get_today_prices()
            filename_prefix = "prices_today"
        elif date_range == "tomorrow":
            prices = await entsoe_service.get_tomorrow_prices()
            filename_prefix = "prices_tomorrow"
        elif date_range == "week":
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = today + timedelta(days=6)

            all_prices = []
            current_date = today

            while current_date <= end_date:
                try:
                    daily_prices = await entsoe_service.get_day_ahead_prices(current_date)
                    all_prices.extend(daily_prices)
                except Exception as e:
                    logger.warning(f"Failed to get prices for {current_date.date()}: {str(e)}")

                current_date += timedelta(days=1)

            prices = all_prices
            filename_prefix = "prices_week"
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid date range. Use: today, tomorrow, or week"
            )

        if not prices:
            raise HTTPException(status_code=404, detail="No price data available")

        # Convert to exportable format
        export_data = [
            {
                "timestamp": price.timestamp.isoformat(),
                "price": price.price,
                "unit": price.unit,
                "area": price.area
            }
            for price in prices
        ]

        # Export based on format
        if format == "csv":
            export_content = export_service._export_csv(export_data, filename_prefix)
        elif format == "json":
            export_content = export_service._export_json(export_data, {"name": filename_prefix}, filename_prefix)
        elif format == "excel":
            export_content = export_service._export_excel(export_data, filename_prefix)
        elif format == "xml":
            export_content = export_service._export_xml(export_data, filename_prefix)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")

        # Determine content type and filename
        content_types = {
            "csv": "text/csv",
            "json": "application/json",
            "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "xml": "application/xml"
        }

        extensions = {
            "csv": "csv",
            "json": "json",
            "excel": "xlsx",
            "xml": "xml"
        }

        filename = f"{filename_prefix}_{datetime.now().strftime('%Y%m%d')}.{extensions[format]}"

        return Response(
            content=export_content,
            media_type=content_types[format],
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except Exception as e:
        logger.error(f"Price export error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Price export failed: {str(e)}"
        )
