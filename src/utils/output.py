"""Utilidades para formatear y mostrar resultados en terminal con Rich."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.schemas.product import DealResult
from src.utils.price import calculate_discount, format_clp

console = Console()


def print_deal_result(result: DealResult) -> None:
    """Imprime el resultado final de DealScout en formato bonito con Rich.

    Args:
        result: DealResult con la mejor opcion y alternativas
    """
    best = result.best_deal

    # ─── Mejor opcion ────────────────────────────────────────────────────────
    best_lines: list[str] = []
    best_lines.append(f"[bold white]{best.name}[/bold white]")
    best_lines.append(f"[bold green]{format_clp(best.price)}[/bold green] en [cyan]{best.store}[/cyan]")

    if best.original_price:
        discount = calculate_discount(best.original_price, best.price)
        best_lines.append(
            f"[dim]Precio original: {format_clp(best.original_price)}[/dim] "
            f"[green](-{discount['percentage']}% — ahorras {format_clp(discount['amount'])})[/green]"
        )

    if best.shipping_info:
        best_lines.append(f"[blue]{best.shipping_info}[/blue]")

    if best.rating:
        stars = "★" * int(best.rating) + "☆" * (5 - int(best.rating))
        best_lines.append(f"[yellow]{stars}[/yellow] {best.rating:.1f}/5.0")

    best_lines.append(f"[dim underline]{best.url}[/dim underline]")

    console.print(Panel(
        "\n".join(best_lines),
        title="[bold green]🏆 MEJOR OPCION[/bold green]",
        border_style="green",
        padding=(1, 2),
    ))

    # ─── Recomendacion ────────────────────────────────────────────────────────
    console.print(f"\n[italic]{result.recommendation}[/italic]\n")

    # ─── Alternativas ─────────────────────────────────────────────────────────
    if result.alternatives:
        table = Table(
            title="[bold blue]📊 ALTERNATIVAS[/bold blue]",
            show_header=True,
            header_style="bold blue",
            border_style="blue",
            show_lines=True,
        )
        table.add_column("#", style="dim", width=3, justify="center")
        table.add_column("Tienda", style="cyan", min_width=12)
        table.add_column("Precio", style="green", justify="right", min_width=12)
        table.add_column("Diferencia", justify="right", min_width=10)
        table.add_column("Envio", style="blue", min_width=14)
        table.add_column("Link", style="dim underline", max_width=40, overflow="fold")

        for i, alt in enumerate(result.alternatives, 1):
            diff = alt.price - best.price
            diff_str = (
                f"[red]+{format_clp(diff)}[/red]"
                if diff > 0
                else f"[green]{format_clp(diff)}[/green]"
            )
            table.add_row(
                str(i),
                alt.store,
                format_clp(alt.price),
                diff_str,
                alt.shipping_info or "No informado",
                alt.url,
            )

        console.print(table)

    # ─── Historial de precios ─────────────────────────────────────────────────
    if result.price_history:
        hist = result.price_history
        console.print(f"\n[dim]📈 HISTORIAL DE PRECIOS ({hist.store})[/dim]")
        console.print(f"  Precio promedio (90 dias): [yellow]{format_clp(hist.average_price)}[/yellow]")
        console.print(f"  Precio mas bajo historico: [green]{format_clp(hist.lowest_price)}[/green]")
        console.print(f"  Precio mas alto historico: [red]{format_clp(hist.highest_price)}[/red]")

        savings_vs_avg = hist.average_price - best.price
        if savings_vs_avg > 0:
            console.print(
                f"  [bold green]Estas ahorrando {format_clp(savings_vs_avg)} vs el promedio historico[/bold green]"
            )

    # ─── Footer ───────────────────────────────────────────────────────────────
    console.print(f"\n[dim]Fuentes consultadas: {', '.join(result.sources_consulted)}[/dim]")
    console.print(
        f"[dim]Busqueda completada en {result.search_duration_seconds:.1f}s "
        f"({result.total_results_found} resultados encontrados)[/dim]\n"
    )


def print_searching_status(message: str) -> None:
    """Imprime un mensaje de estado de busqueda.

    Args:
        message: Mensaje a mostrar al usuario
    """
    console.print(f"[dim]⟳ {message}[/dim]")


def print_error(message: str) -> None:
    """Imprime un mensaje de error en rojo.

    Args:
        message: Mensaje de error a mostrar
    """
    console.print(Panel(
        f"[red]{message}[/red]",
        title="[bold red]Error[/bold red]",
        border_style="red",
    ))
