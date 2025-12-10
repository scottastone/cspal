import PyInstaller.__main__
import os
import shutil

if __name__ == "__main__":
    script_name = "cspal.py"
    exe_name = "cspal"
    
    # Clean up previous build directories
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    if os.path.exists(f'{exe_name}.spec'):
        os.remove(f'{exe_name}.spec')

    print(f"Building {script_name} into a single executable...")
    
    PyInstaller.__main__.run([
        script_name,
        '--onefile',          # Create a single executable file
        '--name', exe_name,   # Name of the executable
        '--clean',            # Clean PyInstaller cache and temporary files
        '--noconfirm',        # Overwrite output directory without asking
        '--log-level', 'WARN' # Set log level
    ])

    print(f"\nBuild complete. Executable can be found in the 'dist' directory: {os.path.abspath('dist')}")
    print(f"To run: .\\dist\\{exe_name}.exe")

    # Remove the build and spec files after building
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists(f'{exe_name}.spec'):
        os.remove(f'{exe_name}.spec')
