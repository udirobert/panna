"""Real-data ingestion — provider feeds → the panna event ledger."""

from src.ingest.sportmonks import IngestResult, SportmonksAdapter
from src.ingest.statsbomb import StatsBombAdapter

__all__ = ["IngestResult", "SportmonksAdapter", "StatsBombAdapter"]
