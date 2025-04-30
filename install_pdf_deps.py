import os
import sys
import subprocess
import urllib.request
import tempfile
import platform
import shutil
import zipfile
import time

def main():
    """Install dependencies required for PDF generation (wkhtmltopdf and/or GTK+ for WeasyPrint)."""
    print("=========================")
    print("PDF Dependencies Installer")
    print("=========================\n")
    
    # Get system information
    system = platform.system()
    is_64bits = sys.maxsize > 2**32
    
    # Check which PDF libraries are available or can be installed
    try:
        import pdfkit
        print("✅ PDFKit module is installed")
        pdfkit_available = True
    except ImportError:
        print("❌ PDFKit module is not installed")
        print("   Installing PDFKit...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pdfkit"])
            print("✅ PDFKit installed successfully")
            pdfkit_available = True
        except subprocess.CalledProcessError:
            print("❌ Failed to install PDFKit")
            pdfkit_available = False
    
    try:
        import weasyprint
        print("✅ WeasyPrint module is installed")
        weasyprint_available = True
    except ImportError:
        print("❌ WeasyPrint module is not installed")
        print("   Installing WeasyPrint...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "weasyprint"])
            print("✅ WeasyPrint installed successfully")
            weasyprint_available = True
        except subprocess.CalledProcessError:
            print("❌ Failed to install WeasyPrint")
            weasyprint_available = False
    
    # Now install system dependencies based on platform
    if system == "Windows":
        # On Windows, install both wkhtmltopdf and GTK+ for WeasyPrint
        result1 = install_wkhtmltopdf_windows(is_64bits)
        result2 = install_gtk_windows(is_64bits)
        print("\nVerifying installations:")
        verify_installations(system)
        return max(result1, result2)  # Return error if any installation failed
    elif system == "Linux":
        result = install_pdf_deps_linux()
        print("\nVerifying installations:")
        verify_installations(system)
        return result
    elif system == "Darwin":  # macOS
        result = install_pdf_deps_macos()
        print("\nVerifying installations:")
        verify_installations(system)
        return result
    else:
        print(f"Unsupported platform: {system}")
        print("Please install wkhtmltopdf and GTK+ manually")
        return 1

def verify_installations(system):
    """Verify that the PDF dependencies are properly installed."""
    # Check wkhtmltopdf
    try:
        result = subprocess.run(['wkhtmltopdf', '--version'], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE, 
                              text=True)
        print(f"✅ wkhtmltopdf is installed: {result.stdout.strip()}")
    except FileNotFoundError:
        print("❌ wkhtmltopdf is not found in PATH")
    
    # For Windows, check GTK DLLs existence
    if system == "Windows":
        gtk_path = os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'GTK3-Runtime Win64')
        if not os.path.exists(gtk_path):
            gtk_path = os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), 'GTK3-Runtime Win64')
        
        if os.path.exists(gtk_path):
            print(f"✅ GTK3 is installed at: {gtk_path}")
            # Check if PATH contains GTK bin directory
            gtk_bin = os.path.join(gtk_path, 'bin')
            if gtk_bin.lower() in os.environ.get('PATH', '').lower():
                print("✅ GTK3 bin directory is in PATH")
            else:
                print("❌ GTK3 bin directory is NOT in PATH")
                print(f"   Add this to your PATH: {gtk_bin}")
        else:
            print("❌ GTK3 installation not found")

def install_wkhtmltopdf_windows(is_64bits):
    """Install wkhtmltopdf on Windows."""
    print("\n[1/2] Installing wkhtmltopdf for Windows...")
    
    # URLs for the installer
    if is_64bits:
        url = "https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox-0.12.6-1.msvc2015-win64.exe"
    else:
        url = "https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox-0.12.6-1.msvc2015-win32.exe"
    
    # Download the installer to a temporary file
    temp_dir = tempfile.gettempdir()
    installer_path = os.path.join(temp_dir, "wkhtmltopdf_installer.exe")
    
    try:
        print(f"Downloading from {url}...")
        urllib.request.urlretrieve(url, installer_path)
        print("Download complete")
        
        # Run the installer silently
        print("Running the installer (this may take a few minutes)...")
        subprocess.run([installer_path, "/S"], check=True)
        print("wkhtmltopdf installed successfully!")
        
        # Add wkhtmltopdf to PATH
        print("Adding wkhtmltopdf to PATH...")
        if is_64bits:
            install_path = r"C:\Program Files\wkhtmltopdf\bin"
        else:
            install_path = r"C:\Program Files (x86)\wkhtmltopdf\bin"
            
        # Check if the path exists
        if os.path.exists(install_path):
            # Add to system PATH temporarily for this session
            os.environ["PATH"] += os.pathsep + install_path
            print(f"wkhtmltopdf added to PATH: {install_path}")
        else:
            print(f"Warning: Installation directory {install_path} not found.")
            print("You may need to add wkhtmltopdf to your system PATH manually.")
        
    except Exception as e:
        print(f"Error installing wkhtmltopdf: {e}")
        print("\nPlease install wkhtmltopdf manually from: https://wkhtmltopdf.org/downloads.html")
        return 1
    
    return 0

def install_gtk_windows(is_64bits):
    """Install GTK+ on Windows for WeasyPrint."""
    print("\n[2/2] Installing GTK3 for WeasyPrint...")
    
    # We'll use the GTK3 installer from MSYS2
    gtk_url = "https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases/download/2022-01-04/gtk3-runtime-3.24.31-2022-01-04-ts-win64.exe"
    
    # Download the installer to a temporary file
    temp_dir = tempfile.gettempdir()
    installer_path = os.path.join(temp_dir, "gtk3_installer.exe")
    
    try:
        print(f"Downloading GTK3 from {gtk_url}...")
        urllib.request.urlretrieve(gtk_url, installer_path)
        print("Download complete")
        
        # Run the installer silently
        print("Running the GTK installer (this may take a few minutes)...")
        # Use /S for silent installation and /D for destination directory
        program_files = os.environ.get('PROGRAMFILES', 'C:\\Program Files')
        
        # Run the installer
        subprocess.run([installer_path, "/S"], check=True)
        
        # Typical installation path
        gtk_path = os.path.join(program_files, 'GTK3-Runtime Win64')
        if not os.path.exists(gtk_path):
            # Try Program Files (x86) as fallback
            gtk_path = os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), 'GTK3-Runtime Win64')
        
        if os.path.exists(gtk_path):
            # Update PATH for current session
            gtk_bin = os.path.join(gtk_path, "bin")
            os.environ["PATH"] = os.pathsep.join([os.environ["PATH"], gtk_bin])
            
            # Set GTK environment variables (important for WeasyPrint)
            os.environ["GTK_BASEPATH"] = gtk_path
            os.environ["GTK_EXE_PREFIX"] = gtk_path
            
            print(f"✅ GTK3 installed successfully at: {gtk_path}")
            print(f"✅ GTK3 bin directory added to PATH: {gtk_bin}")
            print(f"✅ GTK environment variables set")
            
            # Create a more comprehensive batch file for users to set GTK environment variables
            set_gtk_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'set_gtk_path.bat')
            with open(set_gtk_path, 'w') as f:
                f.write(f'@echo off\n')
                f.write(f'echo Setting GTK3 environment variables for WeasyPrint...\n')
                f.write(f'setx PATH "%PATH%;{gtk_bin}"\n')
                f.write(f'setx GTK_BASEPATH "{gtk_path}"\n')
                f.write(f'setx GTK_EXE_PREFIX "{gtk_path}"\n')
                f.write(f'echo GTK3 path added to system PATH: {gtk_bin}\n')
                f.write(f'echo GTK3 environment variables set systemwide\n')
                f.write(f'echo.\n')
                f.write(f'echo IMPORTANT: Please restart your computer for changes to take effect\n')
                f.write(f'pause\n')
            
            print(f"\nCreated batch file at {set_gtk_path}")
            print(f"IMPORTANT: Run this batch file AS ADMINISTRATOR to set GTK environment variables permanently")
            
            # Create a test script to verify WeasyPrint works with GTK
            test_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_weasyprint.py')
            with open(test_script_path, 'w') as f:
                f.write('import sys\n')
                f.write('print("Python version:", sys.version)\n')
                f.write('try:\n')
                f.write('    import weasyprint\n')
                f.write('    print("WeasyPrint version:", weasyprint.__version__)\n')
                f.write('    print("WeasyPrint dependencies OK")\n')
                f.write('except ImportError as e:\n')
                f.write('    print("Failed to import WeasyPrint:", e)\n')
                f.write('except Exception as e:\n')
                f.write('    print("WeasyPrint error:", e)\n')
            
            print(f"Created test script at {test_script_path}")
            print(f"After running the batch file and restarting, run this test script to verify WeasyPrint works")
            
            # Inform the user that they definitely need to restart
            print("\n⚠️  IMPORTANT: You MUST restart your system for GTK to be properly recognized by WeasyPrint")
            print("    After restart, run the set_gtk_path.bat file AS ADMINISTRATOR.")
        else:
            print(f"❌ Warning: GTK3 installation directory not found.")
            print("GTK3 installation may have failed or installed to a different location.")
            
            # Try to manually download and extract a portable GTK
            print("\nAttempting alternative GTK installation method...")
            portable_gtk_url = "https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases/download/2022-01-04/gtk3-runtime-3.24.31-2022-01-04-ts-win64.zip"
            portable_zip = os.path.join(temp_dir, "gtk3_portable.zip")
            
            try:
                print(f"Downloading portable GTK3 from {portable_gtk_url}...")
                urllib.request.urlretrieve(portable_gtk_url, portable_zip)
                
                # Create GTK directory in the app folder
                app_dir = os.path.dirname(os.path.abspath(__file__))
                gtk_portable_path = os.path.join(app_dir, "gtk3-runtime")
                os.makedirs(gtk_portable_path, exist_ok=True)
                
                print(f"Extracting to {gtk_portable_path}...")
                with zipfile.ZipFile(portable_zip, 'r') as zip_ref:
                    zip_ref.extractall(gtk_portable_path)
                
                # Set environment variables to point to portable GTK
                gtk_bin = os.path.join(gtk_portable_path, "bin")
                os.environ["PATH"] = os.pathsep.join([os.environ["PATH"], gtk_bin])
                os.environ["GTK_BASEPATH"] = gtk_portable_path
                os.environ["GTK_EXE_PREFIX"] = gtk_portable_path
                
                print(f"✅ Portable GTK3 extracted to: {gtk_portable_path}")
                print(f"✅ GTK3 bin directory added to PATH: {gtk_bin}")
                
                # Create a batch file for the portable GTK
                set_gtk_path = os.path.join(app_dir, 'set_portable_gtk_path.bat')
                with open(set_gtk_path, 'w') as f:
                    f.write(f'@echo off\n')
                    f.write(f'echo Setting portable GTK3 environment variables for WeasyPrint...\n')
                    f.write(f'set PATH=%PATH%;{gtk_bin}\n')
                    f.write(f'set GTK_BASEPATH={gtk_portable_path}\n')
                    f.write(f'set GTK_EXE_PREFIX={gtk_portable_path}\n')
                    f.write(f'echo Portable GTK3 path added: {gtk_bin}\n')
                    f.write(f'echo.\n')
                    f.write(f'echo Testing WeasyPrint...\n')
                    f.write(f'python {os.path.join(app_dir, "test_weasyprint.py")}\n')
                    f.write(f'pause\n')
                
                print(f"\nCreated portable GTK batch file at {set_gtk_path}")
                print("Run this batch file before using WeasyPrint")
                return 0
            except Exception as e:
                print(f"Error with alternative installation: {e}")
                return 1
    except Exception as e:
        print(f"Error installing GTK3: {e}")
        print("\nYou can manually install GTK3 from:")
        print("https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases")
        return 1
    
    return 0

def install_pdf_deps_linux():
    """Install PDF generation dependencies on Linux."""
    print("Detecting Linux distribution...")
    
    # Try to detect the Linux distribution
    if os.path.exists("/etc/debian_version"):
        # Debian/Ubuntu
        print("Detected Debian/Ubuntu")
        
        # Install WeasyPrint dependencies
        try:
            print("Installing dependencies for WeasyPrint and wkhtmltopdf...")
            cmd = "sudo apt-get update && sudo apt-get install -y wkhtmltopdf python3-dev python3-pip python3-cffi python3-brotli libpango1.0-dev libharfbuzz-dev libffi-dev libcairo2-dev libpangocairo-1.0-0"
            subprocess.run(cmd, shell=True, check=True)
            print("Dependencies installed successfully")
        except Exception as e:
            print(f"Error installing dependencies: {e}")
            return 1
        
    elif os.path.exists("/etc/redhat-release"):
        # RHEL/CentOS/Fedora
        print("Detected RHEL/CentOS/Fedora")
        try:
            print("Installing dependencies for WeasyPrint and wkhtmltopdf...")
            cmd = "sudo yum install -y wkhtmltopdf pango-devel cairo-devel harfbuzz-devel python3-devel python3-pip"
            subprocess.run(cmd, shell=True, check=True)
            print("Dependencies installed successfully")
        except Exception as e:
            print(f"Error installing dependencies: {e}")
            return 1
    else:
        print("Unable to detect Linux distribution")
        print("Please install wkhtmltopdf and WeasyPrint dependencies manually")
        return 1
    
    return 0

def install_pdf_deps_macos():
    """Install PDF generation dependencies on macOS."""
    print("Installing PDF dependencies for macOS...")
    
    # Check if Homebrew is installed
    try:
        subprocess.run(["brew", "--version"], check=True, stdout=subprocess.PIPE)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("Homebrew not found. Please install Homebrew first:")
        print("  /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)\"")
        return 1
    
    # Install dependencies
    try:
        print("Installing wkhtmltopdf via Homebrew...")
        subprocess.run(["brew", "install", "wkhtmltopdf"], check=True)
        print("wkhtmltopdf installed successfully")
        
        print("Installing dependencies for WeasyPrint...")
        subprocess.run(["brew", "install", "pango", "cairo", "libffi", "harfbuzz"], check=True)
        print("WeasyPrint dependencies installed successfully")
    except Exception as e:
        print(f"Error installing dependencies: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInstallation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)