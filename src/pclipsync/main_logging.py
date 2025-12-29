"""Logging configuration for pclipsync CLI."""
import logging


def configure_logging(verbose: bool) -> None:
    """Configure logging level based on verbosity setting.

    Args:
        verbose: If True, set DEBUG level; otherwise WARNING level.

    Errors are always printed to stderr regardless of verbosity.
    """
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        handlers=[logging.StreamHandler()],
    )
