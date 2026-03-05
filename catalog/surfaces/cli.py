"""
CLI Surface for Amazon Catalog Tool (v2.0)
Agent-first redesign with --json input, schema introspection, and field masks.
Backward compatible with all v1.x commands.
"""

import sys
import json as json_mod

import click
from rich.console import Console

from catalog.core.engine import execute_scan, execute_check, list_queries, get_schema
from catalog.core.models import ScanRequest, CheckRequest
from catalog.core.validation import ValidationError
from catalog.output import format_terminal, format_json, format_csv, format_ndjson, print_summary

console = Console()


def _parse_json_input(json_str: str | None, stdin: bool) -> dict | None:
    """Parse JSON from --json flag or --stdin."""
    if stdin:
        raw = sys.stdin.read()
        if raw.strip():
            return json_mod.loads(raw)
    if json_str:
        return json_mod.loads(json_str)
    return None


@click.group()
@click.version_option(version="2.0.0")
def cli():
    """Catalog CLI - Agent-native Amazon catalog auditing tool"""
    pass


@cli.command()
@click.argument('clr_file', required=False, type=click.Path(exists=True))
@click.option('--format', 'output_format', type=click.Choice(['terminal', 'json', 'csv', 'ndjson']),
              default=None, help='Output format')
@click.option('--output', 'output_path', type=click.Path(), help='Output file path')
@click.option('--show-details/--no-details', default=False,
              help='Show detailed results (default: summary only)')
@click.option('--include-fbm-duplicates', is_flag=True, default=False,
              help='Include FBM/MFN duplicates (default: skip them)')
@click.option('--json', 'json_input', type=str, default=None,
              help='JSON request body (agent-friendly input)')
@click.option('--stdin', 'use_stdin', is_flag=True, default=False,
              help='Read JSON request from stdin')
@click.option('--queries', 'query_list', type=str, default=None,
              help='Comma-separated list of query names to run')
@click.option('--fields', 'field_list', type=str, default=None,
              help='Comma-separated field mask')
@click.option('--limit', type=int, default=None, help='Max issues to return')
@click.option('--offset', type=int, default=None, help='Skip first N issues')
def scan(clr_file, output_format, output_path, show_details, include_fbm_duplicates,
         json_input, use_stdin, query_list, field_list, limit, offset):
    """Run all queries on a CLR file"""
    try:
        json_data = _parse_json_input(json_input, use_stdin)

        if json_data:
            request = ScanRequest(**json_data)
        else:
            if not clr_file:
                raise click.UsageError("CLR_FILE is required (or use --json/--stdin)")

            # Default format based on context
            fmt = output_format or _default_format()

            request = ScanRequest(
                file=clr_file,
                queries=query_list.split(",") if query_list else None,
                fields=field_list.split(",") if field_list else None,
                limit=limit,
                offset=offset,
                exclude_fbm=not include_fbm_duplicates,
                format=fmt,
            )

        # Override format from CLI flags if explicitly set
        if output_format:
            request.format = output_format

        response = execute_scan(request)
        _output_scan_response(response, request.format, output_path, show_details)

    except (ValidationError, Exception) as e:
        fmt = output_format or _default_format()
        _error_output(str(e), fmt)
        raise SystemExit(1)


@cli.command()
@click.argument('query_name', required=False)
@click.argument('clr_file', required=False, type=click.Path(exists=True))
@click.option('--format', 'output_format', type=click.Choice(['terminal', 'json', 'csv', 'ndjson']),
              default=None, help='Output format')
@click.option('--output', 'output_path', type=click.Path(), help='Output file path')
@click.option('--show-details/--no-details', default=True, help='Show detailed results')
@click.option('--include-fbm-duplicates', is_flag=True, default=False,
              help='Include FBM/MFN duplicates (default: skip them)')
@click.option('--json', 'json_input', type=str, default=None,
              help='JSON request body (agent-friendly input)')
@click.option('--stdin', 'use_stdin', is_flag=True, default=False,
              help='Read JSON request from stdin')
@click.option('--fields', 'field_list', type=str, default=None,
              help='Comma-separated field mask')
@click.option('--limit', type=int, default=None, help='Max issues to return')
@click.option('--offset', type=int, default=None, help='Skip first N issues')
def check(query_name, clr_file, output_format, output_path, show_details, include_fbm_duplicates,
          json_input, use_stdin, field_list, limit, offset):
    """Run a specific query on a CLR file"""
    try:
        json_data = _parse_json_input(json_input, use_stdin)

        if json_data:
            request = CheckRequest(**json_data)
        else:
            if not query_name or not clr_file:
                raise click.UsageError("QUERY_NAME and CLR_FILE are required (or use --json/--stdin)")

            fmt = output_format or _default_format()

            request = CheckRequest(
                query=query_name,
                file=clr_file,
                fields=field_list.split(",") if field_list else None,
                limit=limit,
                offset=offset,
                exclude_fbm=not include_fbm_duplicates,
                format=fmt,
            )

        if output_format:
            request.format = output_format

        response = execute_check(request)
        _output_check_response(response, request.format, output_path, show_details)

    except (ValidationError, ValueError, Exception) as e:
        fmt = output_format or _default_format()
        _error_output(str(e), fmt)
        if isinstance(e, ValueError) and fmt == 'terminal':
            console.print(f"\nRun [bold]catalog list-queries[/bold] to see available queries.")
        raise SystemExit(1)


@cli.command('list-queries')
@click.argument('clr_file', required=False, type=click.Path(exists=True))
@click.option('--format', 'output_format', type=click.Choice(['terminal', 'json']),
              default=None, help='Output format')
def list_queries_cmd(clr_file, output_format):
    """List available queries"""
    fmt = output_format or _default_format()
    queries = list_queries(clr_file)

    if fmt == 'json':
        click.echo(json_mod.dumps([q.model_dump() for q in queries], indent=2))
    else:
        console.print("\n[bold cyan]Available Queries:[/bold cyan]\n")
        for q in queries:
            console.print(f"  * [bold]{q.name}[/bold]")
            console.print(f"    {q.description}\n")


@cli.command()
@click.argument('query_name', required=False)
@click.option('--format', 'output_format', type=click.Choice(['terminal', 'json']),
              default=None, help='Output format')
def schema(query_name, output_format):
    """Show schema for queries, params, and response shapes"""
    fmt = output_format or _default_format()
    response = get_schema(query_name)

    if fmt == 'json':
        click.echo(json_mod.dumps(response.model_dump(), indent=2))
    else:
        console.print("\n[bold cyan]Catalog CLI Schema[/bold cyan]\n")

        for q in response.queries:
            console.print(f"  [bold]{q.name}[/bold]")
            console.print(f"    {q.description}")
            if q.example_usage:
                console.print(f"    Example: [dim]{q.example_usage}[/dim]")
            console.print()

        if not query_name:
            console.print("[dim]Tip: catalog schema <query_name> for details on a specific query[/dim]")
            console.print("[dim]Tip: catalog schema --format json for machine-readable output[/dim]")


@cli.command()
def mcp():
    """Start the MCP server (stdio transport)"""
    from catalog.surfaces.mcp import run_mcp_server
    run_mcp_server()


# --- Output helpers ---

def _default_format() -> str:
    """Return default format based on environment."""
    import os
    return os.environ.get("CATALOG_CLI_DEFAULT_FORMAT", "terminal")


def _error_output(message: str, fmt: str):
    """Output an error in the appropriate format."""
    if fmt in ("json", "ndjson"):
        click.echo(json_mod.dumps({"error": message}))
    else:
        console.print(f"[red]Error: {message}[/red]")


def _output_scan_response(response, fmt, output_path, show_details):
    """Route scan response to the right formatter."""
    if fmt == 'json':
        output = json_mod.dumps(response.model_dump(), indent=2)
        if output_path:
            with open(output_path, 'w') as f:
                f.write(output)
            console.print(f"[green]JSON exported to {output_path}[/green]")
        else:
            click.echo(output)

    elif fmt == 'ndjson':
        output = format_ndjson(response)
        if output_path:
            with open(output_path, 'w') as f:
                f.write(output)
        else:
            click.echo(output, nl=False)

    elif fmt == 'csv':
        path = output_path or "catalog_scan_results.csv"
        format_csv_from_response(response, path)

    else:  # terminal
        if show_details:
            _print_terminal_scan(response, show_details=True)
        else:
            _print_terminal_summary(response)
            console.print("[dim]Tip: Use --show-details to see full results[/dim]")


def _output_check_response(response, fmt, output_path, show_details):
    """Route check response to the right formatter."""
    if fmt == 'json':
        output = json_mod.dumps(response.model_dump(), indent=2)
        if output_path:
            with open(output_path, 'w') as f:
                f.write(output)
            console.print(f"[green]JSON exported to {output_path}[/green]")
        else:
            click.echo(output)

    elif fmt == 'ndjson':
        output = format_ndjson_check(response)
        if output_path:
            with open(output_path, 'w') as f:
                f.write(output)
        else:
            click.echo(output, nl=False)

    elif fmt == 'csv':
        path = output_path or f"{response.query_name}_results.csv"
        format_csv_check_from_response(response, path)

    else:  # terminal
        _print_terminal_check(response, show_details)


def _print_terminal_scan(response, show_details=True):
    """Print scan results in terminal format."""
    from rich.table import Table
    from rich.panel import Panel

    for block in response.results:
        console.print()
        console.print(Panel(
            f"[bold]{block.description}[/bold]\n"
            f"Issues: {block.total_issues} | Affected SKUs: {block.affected_skus}",
            title=f"[bold]{block.query_name}[/bold]",
            border_style="blue"
        ))

        if block.total_issues == 0:
            console.print("[green]No issues found[/green]\n")
            continue

        if show_details and block.issues:
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Row", width=6)
            table.add_column("SKU", width=15)
            table.add_column("Field", width=20)
            table.add_column("Severity", width=12)
            table.add_column("Details", width=60)

            for issue in block.issues[:20]:
                severity_color = {
                    'required': 'red', 'conditional': 'yellow',
                    'warning': 'orange1', 'info': 'blue',
                    'critical': 'red', 'awareness': 'cyan',
                }.get(issue.severity, 'white')

                table.add_row(
                    str(issue.row),
                    issue.sku[:15],
                    issue.field[:20],
                    f"[{severity_color}]{issue.severity}[/{severity_color}]",
                    issue.details[:60],
                )

            if len(block.issues) > 20:
                table.add_row("...", f"+{len(block.issues) - 20} more", "", "", "")

            console.print(table)
        console.print()


def _print_terminal_summary(response):
    """Print summary for scan."""
    from rich.panel import Panel

    console.print()
    console.print(Panel(
        f"[bold]Total Issues:[/bold] {response.total_issues}\n"
        f"[bold]Affected SKUs:[/bold] {response.total_affected_skus}\n"
        f"[bold]Queries Run:[/bold] {response.total_queries}",
        title="Summary",
        border_style="green"
    ))
    console.print()


def _print_terminal_check(response, show_details=True):
    """Print check results in terminal format."""
    from rich.table import Table
    from rich.panel import Panel

    console.print()
    console.print(Panel(
        f"[bold]{response.description}[/bold]\n"
        f"Issues: {response.total_issues} | Affected SKUs: {response.affected_skus}",
        title=f"[bold]{response.query_name}[/bold]",
        border_style="blue"
    ))

    if response.total_issues == 0:
        console.print("[green]No issues found[/green]\n")
        return

    if show_details and response.issues:
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Row", width=6)
        table.add_column("SKU", width=15)
        table.add_column("Field", width=20)
        table.add_column("Severity", width=12)
        table.add_column("Details", width=60)

        for issue in response.issues[:20]:
            severity_color = {
                'required': 'red', 'conditional': 'yellow',
                'warning': 'orange1', 'info': 'blue',
                'critical': 'red', 'awareness': 'cyan',
            }.get(issue.severity, 'white')

            table.add_row(
                str(issue.row),
                issue.sku[:15],
                issue.field[:20],
                f"[{severity_color}]{issue.severity}[/{severity_color}]",
                issue.details[:60],
            )

        if len(response.issues) > 20:
            table.add_row("...", f"+{len(response.issues) - 20} more", "", "", "")

        console.print(table)
    console.print()


def format_csv_from_response(response, output_path):
    """Write scan response to CSV."""
    import csv
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['query', 'row', 'sku', 'field', 'severity', 'details', 'product_type'])
        writer.writeheader()
        for block in response.results:
            for issue in block.issues:
                writer.writerow({
                    'query': block.query_name,
                    'row': issue.row,
                    'sku': issue.sku,
                    'field': issue.field,
                    'severity': issue.severity,
                    'details': issue.details,
                    'product_type': issue.product_type,
                })
    console.print(f"[green]CSV exported to {output_path}[/green]")


def format_csv_check_from_response(response, output_path):
    """Write check response to CSV."""
    import csv
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['query', 'row', 'sku', 'field', 'severity', 'details', 'product_type'])
        writer.writeheader()
        for issue in response.issues:
            writer.writerow({
                'query': response.query_name,
                'row': issue.row,
                'sku': issue.sku,
                'field': issue.field,
                'severity': issue.severity,
                'details': issue.details,
                'product_type': issue.product_type,
            })
    console.print(f"[green]CSV exported to {output_path}[/green]")


if __name__ == '__main__':
    cli()
