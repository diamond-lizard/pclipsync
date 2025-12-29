"""Click option helpers for mutual exclusivity."""
import click


class MutuallyExclusiveOption(click.Option):
    """Click option that enforces mutual exclusivity with another option."""

    def __init__(self, *args, **kwargs):
        """Initialize with not_required_if parameter for mutual exclusion."""
        self.not_required_if = kwargs.pop("not_required_if", [])
        super().__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        """Check mutual exclusion and enforce exactly one mode selected."""
        current = self.name in opts
        for other in self.not_required_if:
            if other in opts and current:
                raise click.UsageError(
                    f"Options --{self.name} and --{other} are mutually exclusive"
                )
        return super().handle_parse_result(ctx, opts, args)
