#!/usr/bin/env python3
"""
Sweedle Launcher - One-click start for the 3D Asset Generator

This script:
1. Checks/installs dependencies
2. Builds the frontend (if needed)
3. Starts the server
4. Opens the browser
"""

import subprocess
import sys
import os
import time
import webbrowser
from pathlib import Path

# Colors for terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_banner():
    print(f"""
{Colors.CYAN}{Colors.BOLD}
  ███████╗██╗    ██╗███████╗███████╗██████╗ ██╗     ███████╗
  ██╔════╝██║    ██║██╔════╝██╔════╝██╔══██╗██║     ██╔════╝
  ███████╗██║ █╗ ██║█████╗  █████╗  ██║  ██║██║     █████╗
  ╚════██║██║███╗██║██╔══╝  ██╔══╝  ██║  ██║██║     ██╔══╝
  ███████║╚███╔███╔╝███████╗███████╗██████╔╝███████╗███████╗
  ╚══════╝ ╚══╝╚══╝ ╚══════╝╚══════╝╚═════╝ ╚══════╝╚══════╝
{Colors.END}
{Colors.GREEN}  Local 3D Asset Generator for Game Development{Colors.END}
{Colors.BLUE}  Powered by Hunyuan3D-2.1{Colors.END}
""")

def run_command(cmd, cwd=None, check=True):
    """Run a command and return success status."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            shell=True,
            capture_output=True,
            text=True
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_node():
    """Check if Node.js is installed."""
    success, stdout, _ = run_command("node --version")
    if success:
        version = stdout.strip()
        print(f"  {Colors.GREEN}✓{Colors.END} Node.js {version}")
        return True
    print(f"  {Colors.FAIL}✗{Colors.END} Node.js not found")
    print(f"    Install from: https://nodejs.org/")
    return False

def check_npm():
    """Check if npm is installed."""
    success, stdout, _ = run_command("npm --version")
    if success:
        print(f"  {Colors.GREEN}✓{Colors.END} npm {stdout.strip()}")
        return True
    return False

def setup_frontend(root_dir):
    """Install frontend dependencies and build."""
    frontend_dir = root_dir / "frontend"
    node_modules = frontend_dir / "node_modules"
    dist_dir = frontend_dir / "dist"

    # Install dependencies if needed
    if not node_modules.exists():
        print(f"\n{Colors.CYAN}Installing frontend dependencies...{Colors.END}")
        success, _, stderr = run_command("npm install", cwd=frontend_dir)
        if not success:
            print(f"{Colors.FAIL}Failed to install frontend dependencies{Colors.END}")
            print(stderr)
            return False

    # Build frontend if needed
    if not dist_dir.exists():
        print(f"\n{Colors.CYAN}Building frontend...{Colors.END}")
        success, _, stderr = run_command("npm run build", cwd=frontend_dir)
        if not success:
            print(f"{Colors.FAIL}Failed to build frontend{Colors.END}")
            print(stderr)
            return False
        print(f"  {Colors.GREEN}✓{Colors.END} Frontend built successfully")

    return True

def setup_backend(root_dir):
    """Install backend dependencies."""
    backend_dir = root_dir / "backend"
    requirements = backend_dir / "requirements.txt"

    print(f"\n{Colors.CYAN}Checking backend dependencies...{Colors.END}")

    # Check for required packages
    try:
        import fastapi
        import uvicorn
        print(f"  {Colors.GREEN}✓{Colors.END} Core dependencies installed")
        return True
    except ImportError:
        print(f"  {Colors.WARNING}Installing backend dependencies...{Colors.END}")
        success, _, stderr = run_command(
            f"{sys.executable} -m pip install -r requirements.txt",
            cwd=backend_dir
        )
        if not success:
            print(f"{Colors.FAIL}Failed to install backend dependencies{Colors.END}")
            return False
        return True

def start_server(root_dir, port=8000, dev_mode=False):
    """Start the Sweedle server."""
    backend_dir = root_dir / "backend"

    # Add backend to path
    sys.path.insert(0, str(backend_dir))
    os.chdir(backend_dir)

    print(f"\n{Colors.GREEN}{Colors.BOLD}Starting Sweedle...{Colors.END}")
    print(f"  {Colors.CYAN}→{Colors.END} http://localhost:{port}")
    print(f"  {Colors.CYAN}→{Colors.END} API docs: http://localhost:{port}/docs")
    print(f"\n  Press {Colors.BOLD}Ctrl+C{Colors.END} to stop\n")

    # Open browser after a delay
    def open_browser():
        time.sleep(2)
        webbrowser.open(f"http://localhost:{port}")

    import threading
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    # Start uvicorn
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="127.0.0.1",
        port=port,
        reload=dev_mode,
        log_level="info"
    )

def main():
    print_banner()

    root_dir = Path(__file__).parent.absolute()

    print(f"{Colors.BOLD}Checking requirements...{Colors.END}\n")

    # Check Python version
    py_version = sys.version_info
    if py_version < (3, 10):
        print(f"{Colors.FAIL}Python 3.10+ required (found {py_version.major}.{py_version.minor}){Colors.END}")
        sys.exit(1)
    print(f"  {Colors.GREEN}✓{Colors.END} Python {py_version.major}.{py_version.minor}.{py_version.micro}")

    # Check Node.js (for frontend build)
    if not check_node():
        print(f"\n{Colors.WARNING}Node.js is required for first-time setup.{Colors.END}")
        print("Install from: https://nodejs.org/")
        sys.exit(1)

    check_npm()

    # Setup frontend
    if not setup_frontend(root_dir):
        sys.exit(1)

    # Setup backend
    if not setup_backend(root_dir):
        sys.exit(1)

    # Parse arguments
    dev_mode = "--dev" in sys.argv
    port = 8000
    for arg in sys.argv[1:]:
        if arg.startswith("--port="):
            port = int(arg.split("=")[1])

    # Start server
    try:
        start_server(root_dir, port=port, dev_mode=dev_mode)
    except KeyboardInterrupt:
        print(f"\n{Colors.CYAN}Shutting down...{Colors.END}")
        sys.exit(0)

if __name__ == "__main__":
    main()
