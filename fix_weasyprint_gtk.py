#!/usr/bin/env python
"""
WeasyPrint GTK Dependency Fixer for Windows
-------------------------------------------
This script helps resolve GTK dependency issues with WeasyPrint on Windows.
It will:
1. Check for existing GTK installations
2. Set up required environment variables
3. Test WeasyPrint functionality
4. Create helper batch files to use in the future
"""

import os
import sys
import platform
import subprocess
import winreg
import urllib.request
import zipfile
import tempfile
from pathlib import Path
import ctypes
import shutil

def is_admin():
    """Check if the script is running with admin privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def create_batch_file(gtk_path):
    """Create a batch file to set GTK environment variables."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    set_gtk_path = os.path.join(script_dir, 'set_gtk_env.bat')
    
    gtk_bin = os.path.join(gtk_path, "bin")
    
    with open(set_gtk_path, 'w') as f:
        f.write('@echo off\n')
        f.write('echo Setting GTK3 environment variables for WeasyPrint...\n')
        f.write(f'set PATH=%PATH%;{gtk_bin}\n')
        f.write(f'set GTK_BASEPATH={gtk_path}\n')
        f.write(f'set GTK_EXE_PREFIX={gtk_path}\n')
        f.write('echo.\n')
        f.write('echo Environment variables set for this session.\n')
        f.write('echo To make these changes permanent, run the set_gtk_permanent.bat as Administrator.\n')
        f.write('echo.\n')
        f.write('echo Testing WeasyPrint with current environment variables...\n')
        f.write('python -c "import sys; print(\\"Python version:\\", sys.version); import weasyprint; print(\\"WeasyPrint version:\\", weasyprint.__version__); print(\\"WeasyPrint dependencies OK\\")"\n')
        f.write('echo.\n')
        f.write('echo If no errors are shown above, WeasyPrint is working correctly!\n')
        f.write('pause\n')
    
    # Create permanent setter (requires admin)
    set_gtk_perm = os.path.join(script_dir, 'set_gtk_permanent.bat')
    with open(set_gtk_perm, 'w') as f:
        f.write('@echo off\n')
        f.write('echo Setting permanent GTK3 environment variables for WeasyPrint...\n')
        f.write(f'setx PATH "%PATH%;{gtk_bin}"\n')
        f.write(f'setx GTK_BASEPATH "{gtk_path}"\n')
        f.write(f'setx GTK_EXE_PREFIX "{gtk_path}"\n')
        f.write('echo.\n')
        f.write('echo Permanent environment variables set!\n')
        f.write('echo Please restart your computer for changes to take effect.\n')
        f.write('pause\n')
    
    return set_gtk_path, set_gtk_perm

def download_gtk_portable():
    """Download and set up portable GTK."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    gtk_portable_path = os.path.join(script_dir, "gtk3-runtime")
    
    if os.path.exists(gtk_portable_path):
        print(f"Portable GTK already exists at: {gtk_portable_path}")
        return gtk_portable_path

    # GTK URLs - try multiple sources
    gtk_urls = [
        "https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases/download/2022-01-04/gtk3-runtime-3.24.31-2022-01-04-ts-win64.zip",
        "https://download.gnome.org/binaries/win64/gtk+/3.24/gtk+-bundle_3.24.24_win64.zip"
    ]
    
    temp_dir = tempfile.gettempdir()
    zip_path = os.path.join(temp_dir, "gtk3_portable.zip")
    
    # Try each URL until one works
    download_success = False
    for url in gtk_urls:
        try:
            print(f"Downloading GTK from: {url}")
            urllib.request.urlretrieve(url, zip_path)
            download_success = True
            print("Download complete!")
            break
        except Exception as e:
            print(f"Failed to download from {url}: {e}")
    
    if not download_success:
        print("Failed to download GTK. Please check your internet connection.")
        return None
    
    # Extract the ZIP
    print(f"Extracting GTK to: {gtk_portable_path}")
    os.makedirs(gtk_portable_path, exist_ok=True)
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(gtk_portable_path)
        print("Extraction complete!")
        return gtk_portable_path
    except Exception as e:
        print(f"Failed to extract GTK: {e}")
        return None

def find_gtk_installation():
    """Find GTK installation on Windows."""
    possible_paths = [
        os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'GTK3-Runtime Win64'),
        os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), 'GTK3-Runtime Win64'),
        os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'gtk-runtime'),
        os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), 'gtk-runtime'),
        r"C:\msys64\mingw64",  # MSYS2 GTK path
    ]
    
    # Check registry for GTK installation
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\GTK\3.0") as key:
            path = winreg.QueryValueEx(key, "Path")[0]
            if path and os.path.exists(path):
                possible_paths.insert(0, path)
    except:
        pass  # Registry key not found, continue with default paths
    
    # Look for the directory containing libgobject-2.0-0.dll
    for path in possible_paths:
        if os.path.exists(path):
            dll_path = os.path.join(path, 'bin', 'libgobject-2.0-0.dll')
            if os.path.exists(dll_path):
                return path
    
    return None

def test_weasyprint_with_gtk(gtk_path):
    """Test if WeasyPrint works with the given GTK path."""
    # Set environment variables for this process
    env = os.environ.copy()
    env['GTK_BASEPATH'] = gtk_path
    env['GTK_EXE_PREFIX'] = gtk_path
    env['PATH'] = env.get('PATH', '') + os.pathsep + os.path.join(gtk_path, 'bin')
    
    try:
        result = subprocess.run(
            [sys.executable, '-c', 'import weasyprint; print("WeasyPrint works!")'],
            env=env, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        if "WeasyPrint works!" in result.stdout:
            return True, "GTK dependencies OK"
        else:
            return False, f"Output: {result.stdout}\nError: {result.stderr}"
    except Exception as e:
        return False, str(e)

def main():
    """Main function to fix WeasyPrint GTK dependencies."""
    # Check if running on Windows
    if platform.system() != "Windows":
        print("This script is for Windows only.")
        return 1
    
    print("WeasyPrint GTK Dependency Fixer for Windows")
    print("==========================================\n")
    
    # Check if WeasyPrint is installed
    try:
        import weasyprint
        print(f"✅ WeasyPrint is installed (version: {weasyprint.__version__})")
    except ImportError:
        print("❌ WeasyPrint is not installed.")
        print("   Installing WeasyPrint...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "weasyprint"])
            print("✅ WeasyPrint installed successfully.")
            import weasyprint
        except subprocess.CalledProcessError:
            print("❌ Failed to install WeasyPrint. Please install it manually.")
            return 1
    
    # Find GTK installation
    print("\nLooking for GTK installation...")
    gtk_path = find_gtk_installation()
    
    if gtk_path:
        print(f"✅ Found GTK installation at: {gtk_path}")
        
        # Test if WeasyPrint works with this GTK installation
        print("Testing WeasyPrint with found GTK...")
        success, message = test_weasyprint_with_gtk(gtk_path)
        
        if success:
            print(f"✅ WeasyPrint works with GTK at {gtk_path}!")
            set_gtk_path, set_gtk_perm = create_batch_file(gtk_path)
            print(f"\nCreated batch files:")
            print(f"- {set_gtk_path} (Set environment variables for current session)")
            print(f"- {set_gtk_perm} (Set permanent environment variables, requires admin)")
            print("\nRun the batch files to set up the environment for WeasyPrint.")
            return 0
        else:
            print(f"❌ WeasyPrint test failed with found GTK: {message}")
    else:
        print("❌ No GTK installation found.")
    
    # Download and set up portable GTK
    print("\nSetting up portable GTK...")
    portable_gtk_path = download_gtk_portable()
    
    if portable_gtk_path:
        print(f"✅ Portable GTK set up at: {portable_gtk_path}")
        
        # Test if WeasyPrint works with portable GTK
        print("Testing WeasyPrint with portable GTK...")
        success, message = test_weasyprint_with_gtk(portable_gtk_path)
        
        if success:
            print(f"✅ WeasyPrint works with portable GTK at {portable_gtk_path}!")
            set_gtk_path, set_gtk_perm = create_batch_file(portable_gtk_path)
            print(f"\nCreated batch files:")
            print(f"- {set_gtk_path} (Set environment variables for current session)")
            print(f"- {set_gtk_perm} (Set permanent environment variables, requires admin)")
            print("\nRun the batch files to set up the environment for WeasyPrint.")
            return 0
        else:
            print(f"❌ WeasyPrint test failed with portable GTK: {message}")
    else:
        print("❌ Failed to set up portable GTK.")
    
    # If all else fails
    print("\n==================================================================")
    print("TROUBLESHOOTING ADVICE:")
    print("==================================================================")
    print("1. Install GTK3 manually from:")
    print("   https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases")
    print("2. After installation, restart your computer")
    print("3. Run this script again to test and configure")
    print("4. If still not working, consult the WeasyPrint documentation:")
    print("   https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation")
    print("==================================================================")
    
    return 1

if __name__ == "__main__":
    # Suggest running as admin if possible
    if not is_admin():
        print("NOTE: For best results, run this script as Administrator.")
        print("      Some operations may fail without admin privileges.\n")
    
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)