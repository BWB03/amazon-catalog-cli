"""Backward-compatible re-export from catalog.core.query_engine"""
from .core.query_engine import QueryPlugin, QueryEngine, QueryResult

__all__ = ['QueryPlugin', 'QueryEngine', 'QueryResult']
