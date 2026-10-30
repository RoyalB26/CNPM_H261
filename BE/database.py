"""
Database Access Layer for Smart E-Mobility Hub Backend
Smart E-Mobility Hub - ĐHQG-HCM

Provides centralized in-memory mock database store (dict/list) connecting
User, Operator, and Staff subsystems.
"""

from mock_db import MockDatabaseStore, db

__all__ = ["MockDatabaseStore", "db"]
