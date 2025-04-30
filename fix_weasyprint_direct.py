"""
Direct GTK Fix for WeasyPrint
----------------------------
This script downloads the necessary GTK libraries directly into the Python dll directory
to ensure WeasyPrint can find them without environment variable configuration.
"""
import os
import sys
import tempfile
import urllib.request
import zipfile
import shutil
import glob
import ctypes
from pathlib import Path
import subprocess

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def message(text):
    """Print a formatted message"""
    print(f"\n{'='*80}\n{text}\n{'='*80}")

def copy_dlls_to_python(gtk_bin_path, python_dll_path):
    """Copy required GTK DLLs to Python DLL directory"""
    required_dlls = [
        "libgobject-2.0-0.dll",
        "libglib-2.0-0.dll",
        "libgio-2.0-0.dll",
        "libpango-1.0-0.dll",
        "libpangocairo-1.0-0.dll",
        "libcairo-2.dll",
        "libcairo-gobject-2.dll",
        "libharfbuzz-0.dll",
        "libfontconfig-1.dll",
        "libfreetype-6.dll",
        "libpng16-16.dll",
        "zlib1.dll",
        "libintl-8.dll",
        "libpixman-1-0.dll",
        "libffi-7.dll",
        "libiconv-2.dll"
    ]
    
    # Create backup directory
    backup_dir = os.path.join(os.path.dirname(python_dll_path), "dll_backup")
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    success_count = 0
    for dll in required_dlls:
        src = os.path.join(gtk_bin_path, dll)
        dst = os.path.join(python_dll_path, dll)
        
        if os.path.exists(src):
            # Backup existing DLL if it exists
            if os.path.exists(dst):
                backup = os.path.join(backup_dir, dll)
                try:
                    shutil.copy2(dst, backup)
                    print(f"Backed up existing {dll} to {backup_dir}")
                except Exception as e:
                    print(f"Warning: Could not back up {dll}: {e}")
            
            # Copy the new DLL
            try:
                shutil.copy2(src, dst)
                print(f"✅ Installed {dll} to Python directory")
                success_count += 1
            except Exception as e:
                print(f"❌ Failed to copy {dll}: {e}")
        else:
            print(f"❌ Missing {dll} in GTK directory")
    
    return success_count

def download_gtk_bin():
    """Download GTK binaries"""
    temp_dir = tempfile.gettempdir()
    
    # Try multiple sources for GTK with updated URLs
    gtk_urls = [
        "https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases/download/2023-01-04/gtk3-runtime-3.24.36-2023-01-04-ts-win64.exe",
        "https://github.com/daphne-eu/daphne/releases/download/2023/gtk-bundle-daphne-win64.zip"
    ]
    
    # Try downloading portable ZIP first
    for i, url in enumerate(gtk_urls):
        try:
            print(f"Downloading GTK from {url}...")
            zip_path = os.path.join(temp_dir, f"gtk_temp_{i}.zip")
            
            # If the URL ends with .exe, we need to handle it differently
            if url.endswith('.exe'):
                print("Downloading installer (this might take a while)...")
                installer_path = os.path.join(temp_dir, "gtk_installer.exe")
                urllib.request.urlretrieve(url, installer_path)
                
                # Extract files from the installer using 7-Zip if available, otherwise skip
                try:
                    # Check if 7-Zip is installed
                    seven_zip_path = r"C:\Program Files\7-Zip\7z.exe"
                    if not os.path.exists(seven_zip_path):
                        seven_zip_path = r"C:\Program Files (x86)\7-Zip\7z.exe"
                    
                    if os.path.exists(seven_zip_path):
                        extract_path = os.path.join(temp_dir, "gtk_from_installer")
                        if os.path.exists(extract_path):
                            shutil.rmtree(extract_path)
                        os.makedirs(extract_path)
                        
                        print("Extracting files from installer using 7-Zip...")
                        subprocess.run([seven_zip_path, "x", installer_path, f"-o{extract_path}", "-y"], 
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                        
                        # Look for bin directory with the required DLLs
                        for root, dirs, files in os.walk(extract_path):
                            if "bin" in dirs:
                                bin_dir = os.path.join(root, "bin")
                                if os.path.exists(os.path.join(bin_dir, "libgobject-2.0-0.dll")):
                                    return bin_dir
                    else:
                        print("7-Zip not found, cannot extract from installer")
                except Exception as e:
                    print(f"Failed to extract from installer: {e}")
            else:
                # Regular ZIP file
                urllib.request.urlretrieve(url, zip_path)
                
                extract_path = os.path.join(temp_dir, f"gtk_temp_{i}")
                if os.path.exists(extract_path):
                    shutil.rmtree(extract_path)
                
                os.makedirs(extract_path)
                
                print("Extracting GTK files...")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)
                
                # Look for the bin directory
                for root, dirs, files in os.walk(extract_path):
                    if "bin" in dirs:
                        bin_path = os.path.join(root, "bin")
                        # Check if this contains the needed DLLs
                        if os.path.exists(os.path.join(bin_path, "libgobject-2.0-0.dll")):
                            return bin_path
                    elif os.path.basename(root) == "bin" and any(f.startswith("libgobject") for f in files):
                        # Return the bin directory if it contains libgobject
                        return root
        except Exception as e:
            print(f"Download or extraction failed: {e}")
    
    # Last resort - download directly from MSYS2
    try:
        # Create a custom GTK directory with only the necessary DLLs
        custom_gtk_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gtk_lib")
        custom_gtk_bin = os.path.join(custom_gtk_dir, "bin")
        os.makedirs(custom_gtk_bin, exist_ok=True)
        
        # List of DLLs to download directly from MSYS2
        msys2_base_url = "https://repo.msys2.org/mingw/mingw64/"
        dll_packages = [
            "mingw-w64-x86_64-glib2-2.74.6-1-any.pkg.tar.zst",
            "mingw-w64-x86_64-pango-1.50.14-1-any.pkg.tar.zst",
            "mingw-w64-x86_64-cairo-1.17.8-2-any.pkg.tar.zst",
            "mingw-w64-x86_64-harfbuzz-7.1.0-1-any.pkg.tar.zst"
        ]
        
        dll_paths = []
        for package in dll_packages:
            try:
                url = msys2_base_url + package
                package_path = os.path.join(temp_dir, package)
                print(f"Downloading {package}...")
                
                # Skip if we don't have zstandard decompression
                if package.endswith('.zst'):
                    try:
                        import zstandard
                    except ImportError:
                        print("zstandard module not available, skipping .zst files")
                        continue
                
                urllib.request.urlretrieve(url, package_path)
                # You would need to extract these .pkg.tar.zst files here
                # This requires additional libraries not included in this script
                print(f"Downloaded {package}, but extraction not implemented")
            except Exception as e:
                print(f"Failed to download {package}: {e}")
        
        # If we found any DLLs, return the bin directory
        if os.path.exists(os.path.join(custom_gtk_bin, "libgobject-2.0-0.dll")):
            return custom_gtk_bin
    except Exception as e:
        print(f"MSYS2 download approach failed: {e}")
    
    # Manual download instructions as a last resort
    print("\n==================================================================")
    print("MANUAL DOWNLOAD INSTRUCTIONS:")
    print("==================================================================")
    print("1. Download the GTK3 Runtime for Windows from:")
    print("   https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases")
    print("2. Run the installer and note the installation directory")
    print("3. Run this script again and it will detect the installation")
    print("==================================================================")
    
    return None

def create_test_script():
    """Create a test script for WeasyPrint"""
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_weasyprint.py")
    
    with open(script_path, "w") as f:
        f.write("""import sys
import os

print("Python version:", sys.version)
print("Python executable:", sys.executable)
print("DLL path:", os.path.join(os.path.dirname(sys.executable), 'DLLs'))

try:
    import weasyprint
    print("\\nWeasyPrint version:", weasyprint.__version__)
    print("✅ WeasyPrint imported successfully!")
    
    # Create a simple HTML to PDF test
    html = '<html><body><h1>WeasyPrint Test</h1><p>This is a test document.</p></body></html>'
    test_pdf = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'weasyprint_test.pdf')
    
    print("\\nTrying to generate a test PDF...")
    doc = weasyprint.HTML(string=html)
    doc.write_pdf(test_pdf)
    print(f"✅ PDF created successfully at: {test_pdf}")
    
except Exception as e:
    print("❌ Error:", e)
    
input("\\nPress Enter to exit...")
""")
    
    return script_path

def main():
    if not is_admin() and sys.platform == "win32":
        print("NOTE: This fix requires administrator privileges for best results.")
        print("Please consider running this script as administrator.")
    
    message("WeasyPrint Direct GTK Fix")
    
    # Find Python DLLs directory
    python_dir = os.path.dirname(sys.executable)
    python_dll_dir = os.path.join(python_dir, "DLLs")
    
    if not os.path.exists(python_dll_dir):
        python_dll_dir = python_dir  # Fallback to Python directory itself
    
    print(f"Python DLLs directory: {python_dll_dir}")
    
    # First check for existing GTK installation
    potential_gtk_paths = [
        os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'GTK3-Runtime Win64', 'bin'),
        os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), 'GTK3-Runtime Win64', 'bin'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gtk3-runtime', 'bin'),
    ]
    
    gtk_bin = None
    for path in potential_gtk_paths:
        if os.path.exists(path) and os.path.exists(os.path.join(path, "libgobject-2.0-0.dll")):
            gtk_bin = path
            print(f"Found GTK binaries at: {gtk_bin}")
            break
    
    if not gtk_bin:
        print("No GTK installation found. Downloading GTK binaries...")
        gtk_bin = download_gtk_bin()
    
    if not gtk_bin:
        message("Failed to find or download GTK binaries. Please install GTK manually.")
        return 1
    
    # Copy DLLs to Python directory
    message(f"Copying GTK DLLs from {gtk_bin} to {python_dll_dir}")
    success_count = copy_dlls_to_python(gtk_bin, python_dll_dir)
    
    if success_count > 0:
        message(f"Successfully installed {success_count} GTK DLLs to Python")
        
        # Create a test script
        test_script = create_test_script()
        print(f"Created test script at: {test_script}")
        print("Run this script to verify that WeasyPrint now works correctly.")
        
        # Ask if the user wants to run the test now
        try:
            result = input("\nDo you want to run the test now? (y/n): ").strip().lower()
            if result == 'y':
                print("\nRunning test script...")
                try:
                    subprocess.run([sys.executable, test_script], check=True)
                except subprocess.CalledProcessError:
                    pass
                
        except Exception as e:
            print(f"Error running test: {e}")
    else:
        message("Failed to install any GTK DLLs. Please try running this script as administrator.")
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)