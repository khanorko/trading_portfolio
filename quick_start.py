#!/usr/bin/env python3
"""
Quick Start Script for Trading Bot Dashboard
Automatically sets up and launches the dashboard
"""
import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            return True
        else:
            print(f"❌ {description} failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error during {description}: {e}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        return False
    print(f"✅ Python {version.major}.{version.minor} detected")
    return True

def install_dependencies():
    """Install required packages"""
    requirements_file = Path("dashboard_requirements.txt")
    if requirements_file.exists():
        return run_command(
            f"{sys.executable} -m pip install -r dashboard_requirements.txt",
            "Installing dashboard dependencies"
        )
    else:
        # Install core packages directly
        packages = [
            "streamlit>=1.28.0",
            "plotly>=5.15.0", 
            "pandas>=2.0.0",
            "numpy>=1.24.0"
        ]
        
        for package in packages:
            if not run_command(
                f"{sys.executable} -m pip install {package}",
                f"Installing {package.split('>=')[0]}"
            ):
                return False
        return True

def setup_sample_data():
    """Set up sample data for testing"""
    print("🧪 Setting up sample data for dashboard testing...")
    
    try:
        from dashboard_integration import DashboardIntegration
        integration = DashboardIntegration()
        integration.create_sample_data()
        return True
    except Exception as e:
        print(f"❌ Error setting up sample data: {e}")
        return False

def launch_dashboard():
    """Launch the Streamlit dashboard"""
    dashboard_file = Path("trading_dashboard.py")
    if not dashboard_file.exists():
        print("❌ trading_dashboard.py not found")
        return False
    
    print("🚀 Launching trading dashboard...")
    print("📱 Dashboard will open in your default browser")
    print("🌐 URL: http://localhost:8501")
    print("\n💡 To stop the dashboard, press Ctrl+C in this terminal")
    print("=" * 60)
    
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "trading_dashboard.py"])
        return True
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped by user")
        return True
    except Exception as e:
        print(f"❌ Error launching dashboard: {e}")
        return False

def main():
    """Main setup and launch function"""
    print("🤖 Trading Bot Dashboard Quick Start")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    print("\n📦 Installing Dependencies...")
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        print("💡 Try running manually: pip install streamlit plotly pandas numpy")
        sys.exit(1)
    
    # Check if sample data should be created
    print("\n📊 Dashboard Data Setup")
    choice = input("Create sample data for testing? (y/n): ").lower().strip()
    
    if choice in ['y', 'yes']:
        if not setup_sample_data():
            print("⚠️ Sample data setup failed, but dashboard can still run")
    
    # Launch dashboard
    print("\n🚀 Launching Dashboard...")
    if not launch_dashboard():
        print("❌ Failed to launch dashboard")
        print("\n🔧 Manual launch instructions:")
        print("1. Install streamlit: pip install streamlit")
        print("2. Run dashboard: streamlit run trading_dashboard.py")
        sys.exit(1)

def show_help():
    """Show help information"""
    print("""
🤖 Trading Bot Dashboard Quick Start Help
========================================

This script will:
1. ✅ Check Python version compatibility
2. 📦 Install required dependencies (streamlit, plotly, pandas, numpy)
3. 🧪 Optionally create sample data for testing
4. 🚀 Launch the dashboard in your browser

Requirements:
- Python 3.8 or higher
- Internet connection (for package installation)

Files created/used:
- trading_dashboard.py - Main dashboard application
- enhanced_state_manager.py - Enhanced logging system
- dashboard_integration.py - Integration helpers
- trading_dashboard.db - SQLite database for data storage

Manual Installation:
If this script fails, you can install manually:

1. Install dependencies:
   pip install streamlit plotly pandas numpy

2. Run dashboard:
   streamlit run trading_dashboard.py

3. Open browser to: http://localhost:8501

Integration with Your Bot:
To connect your trading bot to the dashboard, see examples in:
- dashboard_integration.py

Troubleshooting:
- Permission errors: Try running with 'python' instead of './quick_start.py'
- Package conflicts: Consider using a virtual environment
- Port already in use: Streamlit will automatically find another port

For more help, check the documentation in trading_dashboard.py
""")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        show_help()
    else:
        main()
