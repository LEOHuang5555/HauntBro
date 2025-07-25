"""
ETL Medallion Architecture Package
Bronze → Silver → Gold data processing pipeline
"""

__version__ = "1.0.0"
__author__ = "ETL Medallion Architecture Team"

from .bronze_processor import BronzeProcessor
from .quality_manager import QualityManager

__all__ = ["BronzeProcessor", "QualityManager"]