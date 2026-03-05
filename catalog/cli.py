"""Backward-compatible entry point - delegates to surfaces.cli"""
from .surfaces.cli import cli

__all__ = ['cli']

if __name__ == '__main__':
    cli()
