#!/usr/bin/env python3
"""CLI de DealScout — busca y compara precios de productos en Chile."""

import os

import typer
from dotenv import load_dotenv
from rich.console import Console

# Cargar .env antes de cualquier import que requiera API keys
load_dotenv()

from src.main import main  # noqa: E402
from src.utils.output import print_deal_result, print_error, print_searching_status  # noqa: E402

app = typer.Typer(
    name="dealscout",
    help="Busca y compara precios de productos en el mercado chileno.",
    add_completion=False,
    rich_markup_mode="rich",
)

console = Console()


@app.command()
def search(
    product: str = typer.Argument(
        ...,
        help="Nombre del producto a buscar (ej: 'iPhone 15 128gb', 'PS5', 'notebook gamer')",
    ),
    budget: int | None = typer.Option(
        None,
        "--budget",
        "-b",
        help="Presupuesto maximo en CLP (ej: --budget 800000)",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Mostrar resultado en formato JSON en lugar de tabla formateada",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Mostrar informacion de progreso adicional",
    ),
) -> None:
    """Busca el mejor precio para un producto en el mercado chileno.

    Consulta Solotodo, MercadoLibre, Falabella, Ripley y otras tiendas
    para encontrar la mejor oferta con links directos.

    Ejemplos:

        dealscout "PlayStation 5"

        dealscout "iPhone 15 128gb" --budget 800000

        dealscout "notebook gamer" --json

        dealscout "audifonos bluetooth" -b 50000 -v
    """
    # Validar que tenemos al menos la API key principal
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print_error(
            "ANTHROPIC_API_KEY no configurada.\n\n"
            "1. Copia el archivo de ejemplo: cp .env.example .env\n"
            "2. Edita .env y agrega tu API key de Anthropic\n"
            "   Obtener en: https://console.anthropic.com/"
        )
        raise typer.Exit(code=1)

    # Mostrar header
    console.print("\n[bold]DealScout[/bold] [dim]— Buscando en el mercado chileno[/dim]")
    if os.environ.get("LANGCHAIN_TRACING_V2") == "true" and os.environ.get("LANGCHAIN_API_KEY"):
        project = os.environ.get("LANGCHAIN_PROJECT", "dealscout-agent")
        console.print(f"[dim]LangSmith tracing activo → proyecto: {project}[/dim]")
    console.print(f"[dim]Producto:[/dim] [bold cyan]{product}[/bold cyan]", end="")

    if budget:
        from src.utils.price import format_clp
        console.print(f"  [dim]Presupuesto:[/dim] [yellow]{format_clp(budget)}[/yellow]", end="")
    console.print()

    if verbose:
        print_searching_status("Iniciando agentes de busqueda...")

    try:
        with console.status(
            "[bold green]Buscando en Solotodo, MercadoLibre, Google Shopping Chile...[/bold green]",
            spinner="dots",
        ):
            result = main(query=product, budget=budget)

    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(code=1)

    except RuntimeError as e:
        print_error(str(e))
        raise typer.Exit(code=1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Busqueda cancelada por el usuario.[/yellow]")
        raise typer.Exit(code=0)

    except Exception as e:
        print_error(
            f"Error inesperado durante la busqueda:\n{e}\n\n"
            "Verifica que todas las API keys esten configuradas correctamente en .env"
        )
        if verbose:
            console.print_exception()
        raise typer.Exit(code=1)

    # Mostrar resultado
    if json_output:
        console.print(result.model_dump_json(indent=2))
    else:
        print_deal_result(result)


if __name__ == "__main__":
    app()
