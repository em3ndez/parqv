"""
Command Line Interface for parqv application.
"""

import sys

from .app import ParqV
from .core import SUPPORTED_EXTENSIONS, FileValidationError, validate_and_detect_file, setup_logging, get_logger


def _print_user_message(message: str, log_level: str = "info") -> None:
    """
    Show a message to the user and log it.
    
    Args:
        message: message to display and log
        log_level: log level ('info', 'error', 'warning')
    """
    log = get_logger(__name__)

    print(message, file=sys.stderr)

    if log_level == "error":
        log.error(message)
    elif log_level == "warning":
        log.warning(message)
    else:
        log.info(message)


def validate_cli_arguments() -> str:
    """
    Validates command line arguments.
    
    Returns:
        The file path string from command line arguments
        
    Raises:
        SystemExit: If arguments are invalid
    """
    log = get_logger(__name__)

    if len(sys.argv) < 2:
        usage_message = "Usage: parqv <path_to_parquet_or_json_file>"
        supported_message = f"Supported file types: {', '.join(SUPPORTED_EXTENSIONS.keys())}"

        _print_user_message(usage_message, "error")
        _print_user_message(supported_message, "info")

        log.error("No file path provided via CLI arguments")
        sys.exit(1)

    file_path_str = sys.argv[1]
    log.debug(f"File path received from CLI: {file_path_str}")
    return file_path_str


def run_app() -> None:
    """
    Main entry point for the parqv CLI application.
    
    This function:
    1. Sets up logging
    2. Validates command line arguments
    3. Validates the file path and type
    4. Creates and runs the Textual app
    """
    # Setup logging first
    log = setup_logging()
    log.info("--- parqv CLI started ---")

    try:
        # Get and validate CLI arguments
        file_path_str = validate_cli_arguments()

        # Validate file path and detect type (for early validation)
        file_path, file_type = validate_and_detect_file(file_path_str)
        log.info(f"File validated successfully: {file_path} (type: {file_type})")

        # Create and run the app
        log.info("Starting parqv application...")
        app = ParqV(file_path_str=file_path_str)
        app.run()

        log.info("parqv application finished successfully")

    except FileValidationError as e:
        log.error(f"File validation failed: {e}")

        error_message = f"Error: {e}"
        help_message = f"Please provide a file with one of these extensions: {', '.join(SUPPORTED_EXTENSIONS.keys())}"

        _print_user_message(error_message, "error")
        _print_user_message(help_message, "info")

        log.error("Exiting due to file validation error")
        sys.exit(1)

    except KeyboardInterrupt:
        log.info("Application interrupted by user (Ctrl+C)")
        _print_user_message("\nApplication interrupted by user.", "info")
        sys.exit(0)

    except Exception as e:
        log.exception(f"Unexpected error in CLI: {e}")
        _print_user_message(f"An unexpected error occurred: {e}", "error")
        _print_user_message("Check the log file for more details.", "info")
        sys.exit(1)


if __name__ == "__main__":
    run_app()
