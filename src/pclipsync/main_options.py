"""Click option helpers for mutual exclusivity."""
import click


def _check_mutual_exclusion(name: str, not_required_if: list[str], opts: dict) -> None:
    """Raise UsageError if mutually exclusive options are both present.

    Args:
        name: Name of the current option.
        not_required_if: List of option names that are mutually exclusive.
        opts: Dictionary of parsed options.

    Raises:
        click.UsageError: If both options are present.
    """
    for other in not_required_if:
        if other in opts:
            msg = f"Options --{name} and --{other} are mutually exclusive"
            raise click.UsageError(msg)


class MutuallyExclusiveOption(click.Option):
    """Click option that enforces mutual exclusivity with another option."""

    def __init__(self, *args, **kwargs):
        """Initialize with not_required_if parameter for mutual exclusion."""
        self.not_required_if = kwargs.pop("not_required_if", [])
        super().__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        """Check mutual exclusion and enforce exactly one mode selected."""
        if self.name in opts:
            _check_mutual_exclusion(self.name, self.not_required_if, opts)
        return super().handle_parse_result(ctx, opts, args)
