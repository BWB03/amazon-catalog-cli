"""
Query Engine
Routes queries to plugins and formats results
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class QueryResult:
    """Structured query result"""
    query_name: str
    query_description: str
    total_issues: int
    affected_skus: int
    issues: List[Dict]
    metadata: Dict
    timestamp: str = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        
        # Calculate affected SKUs if not provided
        if self.affected_skus == 0 and self.issues:
            unique_skus = set(issue.get('sku') for issue in self.issues if issue.get('sku'))
            self.affected_skus = len(unique_skus)


class QueryPlugin(ABC):
    """Base class for query plugins"""
    
    name: str = ""
    description: str = ""
    
    @abstractmethod
    def execute(self, listings: List, clr_parser) -> List[Dict]:
        """
        Execute query and return list of issues
        
        Args:
            listings: List of Listing objects from parser
            clr_parser: CLRParser instance for additional data access
        
        Returns:
            List of issue dictionaries with keys:
                - row: Row number in CLR
                - sku: Product SKU
                - field: Field name (if applicable)
                - severity: Issue severity (required/conditional/warning)
                - details: Human-readable description
                - product_type: Product type (if relevant)
        """
        pass


class QueryEngine:
    """Query orchestration and execution"""
    
    def __init__(self, clr_parser):
        """Initialize with parsed CLR"""
        self.clr_parser = clr_parser
        self.plugins = {}
        self.listings_cache = None
    
    def register_query(self, plugin: QueryPlugin):
        """Register a query plugin"""
        if not plugin.name:
            raise ValueError("Query plugin must have a name")
        
        self.plugins[plugin.name] = plugin
    
    def list_queries(self) -> List[Dict[str, str]]:
        """List available queries"""
        return [
            {
                'name': name,
                'description': plugin.description
            }
            for name, plugin in self.plugins.items()
        ]
    
    def execute(self, query_name: str, params: Optional[Dict] = None) -> QueryResult:
        """
        Execute a query
        
        Args:
            query_name: Name of query to run
            params: Optional parameters (for future use)
        
        Returns:
            QueryResult with findings
        """
        if query_name not in self.plugins:
            raise ValueError(f"Unknown query: {query_name}")
        
        plugin = self.plugins[query_name]
        
        # Get listings (cached)
        if not self.listings_cache:
            self.listings_cache = self.clr_parser.get_listings()
        
        # Execute query
        issues = plugin.execute(self.listings_cache, self.clr_parser)
        
        # Build result
        result = QueryResult(
            query_name=plugin.name,
            query_description=plugin.description,
            total_issues=len(issues),
            affected_skus=0,  # Will be calculated in post_init
            issues=issues,
            metadata={
                'total_listings': len(self.listings_cache),
                'params': params or {}
            }
        )
        
        return result
    
    def execute_all(self) -> List[QueryResult]:
        """Execute all registered queries"""
        results = []
        
        for query_name in self.plugins.keys():
            result = self.execute(query_name)
            results.append(result)
        
        return results
