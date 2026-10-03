import os
from pathlib import Path


def main():
    # Load environment variables if python-dotenv is installed
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    app_name = os.getenv("APP_NAME", "scribby")
    env = os.getenv("ENVIRONMENT", "development")
    print(f"Hello from {app_name}! [Environment: {env}]")


if __name__ == "__main__":
    main()
