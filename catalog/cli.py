"""
CLI Interface for Amazon Catalog Tool
"""

import click
from pathlib import Path
from .parser import CLRParser
from .query_engine import QueryEngine
from .output import format_terminal, format_json, format_csv, print_summary, console
from .queries import (
    MissingAttributesQuery,
    MissingAnyAttributesQuery,
    LongTitlesQuery,
    TitleProhibitedCharsQuery,
    RufusBulletsQuery,
    ProhibitedCharsQuery,
    ProductTypeMismatchQuery,
    MissingVariationsQuery,
    NewAttributesQuery
)


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Amazon Catalog CLI - Agent-native CLR query tool"""
    pass


@cli.command()
@click.argument('clr_file', type=click.Path(exists=True))
def list_queries(clr_file):
    """List available queries"""
    
    # Initialize parser and engine
    parser = CLRParser(clr_file)
    engine = QueryEngine(parser)
    
    # Register all queries
    _register_queries(engine)
    
    # List queries
    console.print("\n[bold cyan]Available Queries:[/bold cyan]\n")
    
    for query_info in engine.list_queries():
        console.print(f"  • [bold]{query_info['name']}[/bold]")
        console.print(f"    {query_info['description']}\n")


@cli.command()
@click.argument('query_name')
@click.argument('clr_file', type=click.Path(exists=True))
@click.option('--format', 'output_format', type=click.Choice(['terminal', 'json', 'csv']), 
              default='terminal', help='Output format')
@click.option('--output', 'output_path', type=click.Path(), help='Output file path (for JSON/CSV)')
@click.option('--show-details/--no-details', default=True, help='Show detailed results')
def check(query_name, clr_file, output_format, output_path, show_details):
    """Run a specific query on a CLR file"""
    
    console.print(f"\n[cyan]Loading CLR: {clr_file}[/cyan]")
    
    try:
        # Initialize parser and engine
        parser = CLRParser(clr_file)
        engine = QueryEngine(parser)
        
        # Register all queries
        _register_queries(engine)
        
        console.print(f"[cyan]Running query: {query_name}[/cyan]\n")
        
        # Execute query
        result = engine.execute(query_name)
        
        # Output results
        if output_format == 'terminal':
            format_terminal([result], show_details=show_details)
        
        elif output_format == 'json':
            json_output = format_json([result])
            if output_path:
                with open(output_path, 'w') as f:
                    f.write(json_output)
                console.print(f"[green]✓ JSON exported to {output_path}[/green]")
            else:
                console.print(json_output)
        
        elif output_format == 'csv':
            if not output_path:
                output_path = f"{query_name}_results.csv"
            format_csv([result], output_path)
    
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print(f"\nRun [bold]catalog list-queries {clr_file}[/bold] to see available queries.")
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
@click.argument('clr_file', type=click.Path(exists=True))
@click.option('--format', 'output_format', type=click.Choice(['terminal', 'json', 'csv']), 
              default='terminal', help='Output format')
@click.option('--output', 'output_path', type=click.Path(), help='Output file path (for JSON/CSV)')
@click.option('--show-details/--no-details', default=False, 
              help='Show detailed results (default: summary only)')
def scan(clr_file, output_format, output_path, show_details):
    """Run all queries on a CLR file"""
    
    console.print(f"\n[cyan]Loading CLR: {clr_file}[/cyan]")
    
    try:
        # Initialize parser and engine
        parser = CLRParser(clr_file)
        engine = QueryEngine(parser)
        
        # Register all queries
        _register_queries(engine)
        
        console.print(f"[cyan]Running all queries...[/cyan]\n")
        
        # Execute all queries
        results = engine.execute_all()
        
        # Output results
        if output_format == 'terminal':
            if show_details:
                format_terminal(results, show_details=True)
            else:
                # Summary only
                print_summary(results)
                console.print("[dim]Tip: Use --show-details to see full results[/dim]")
        
        elif output_format == 'json':
            json_output = format_json(results)
            if output_path:
                with open(output_path, 'w') as f:
                    f.write(json_output)
                console.print(f"[green]✓ JSON exported to {output_path}[/green]")
            else:
                console.print(json_output)
        
        elif output_format == 'csv':
            if not output_path:
                output_path = "catalog_scan_results.csv"
            format_csv(results, output_path)
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def _register_queries(engine: QueryEngine):
    """Register all available query plugins"""
    engine.register_query(MissingAttributesQuery())
    engine.register_query(MissingAnyAttributesQuery())
    engine.register_query(LongTitlesQuery())
    engine.register_query(TitleProhibitedCharsQuery())
    engine.register_query(RufusBulletsQuery())
    engine.register_query(ProhibitedCharsQuery())
    engine.register_query(ProductTypeMismatchQuery())
    engine.register_query(MissingVariationsQuery())
    engine.register_query(NewAttributesQuery())


if __name__ == '__main__':
    cli()
