"""
Output formatters for query results
"""

import json
import csv
from typing import List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from .query_engine import QueryResult


console = Console()


def format_terminal(results: List[QueryResult], show_details: bool = True):
    """Pretty terminal output using Rich"""
    
    for result in results:
        # Header
        console.print()
        console.print(Panel(
            f"[bold]{result.query_description}[/bold]\n"
            f"Issues: {result.total_issues} | Affected SKUs: {result.affected_skus}",
            title=f"🔍 {result.query_name}",
            border_style="blue"
        ))
        
        if result.total_issues == 0:
            console.print("[green]✓ No issues found[/green]\n")
            continue
        
        if show_details and result.issues:
            # Create table
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Row", width=6)
            table.add_column("SKU", width=15)
            table.add_column("Field", width=20)
            table.add_column("Severity", width=12)
            table.add_column("Details", width=60)
            
            # Add rows (limit to 20 for readability)
            for issue in result.issues[:20]:
                severity_color = {
                    'required': 'red',
                    'conditional': 'yellow',
                    'warning': 'orange1',
                    'info': 'blue'
                }.get(issue.get('severity', 'info'), 'white')
                
                table.add_row(
                    str(issue.get('row', '')),
                    issue.get('sku', '')[:15],
                    issue.get('field', '')[:20],
                    f"[{severity_color}]{issue.get('severity', '')}[/{severity_color}]",
                    issue.get('details', '')[:60]
                )
            
            if len(result.issues) > 20:
                table.add_row(
                    "...",
                    f"+{len(result.issues) - 20} more",
                    "",
                    "",
                    ""
                )
            
            console.print(table)
        
        console.print()


def format_json(results: List[QueryResult]) -> str:
    """JSON output for agent/script consumption"""
    
    output = {
        'timestamp': results[0].timestamp if results else None,
        'total_queries': len(results),
        'total_issues': sum(r.total_issues for r in results),
        'total_affected_skus': sum(r.affected_skus for r in results),
        'queries': []
    }
    
    for result in results:
        output['queries'].append({
            'query_name': result.query_name,
            'description': result.query_description,
            'total_issues': result.total_issues,
            'affected_skus': result.affected_skus,
            'issues': result.issues,
            'metadata': result.metadata
        })
    
    return json.dumps(output, indent=2)


def format_csv(results: List[QueryResult], output_path: str):
    """CSV export"""
    
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['query', 'row', 'sku', 'field', 'severity', 'details', 'product_type']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        
        for result in results:
            for issue in result.issues:
                writer.writerow({
                    'query': result.query_name,
                    'row': issue.get('row', ''),
                    'sku': issue.get('sku', ''),
                    'field': issue.get('field', ''),
                    'severity': issue.get('severity', ''),
                    'details': issue.get('details', ''),
                    'product_type': issue.get('product_type', '')
                })
    
    console.print(f"[green]✓ CSV exported to {output_path}[/green]")


def print_summary(results: List[QueryResult]):
    """Print high-level summary"""
    
    total_issues = sum(r.total_issues for r in results)
    total_skus = sum(r.affected_skus for r in results)
    
    console.print()
    console.print(Panel(
        f"[bold]Total Issues:[/bold] {total_issues}\n"
        f"[bold]Affected SKUs:[/bold] {total_skus}\n"
        f"[bold]Queries Run:[/bold] {len(results)}",
        title="📊 Summary",
        border_style="green"
    ))
    console.print()
