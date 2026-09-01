import os
import subprocess
import sys
import shutil

def find_chrome():
    """Find Google Chrome executable across platforms."""
    # Check if chrome is in PATH
    for name in ['google-chrome', 'google-chrome-stable', 'chrome', 'chromium', 'chromium-browser']:
        path = shutil.which(name)
        if path:
            return path

    # Platform-specific default locations
    if sys.platform == 'win32':
        # Windows: check common install locations
        program_files = [
            os.environ.get('PROGRAMFILES', 'C:\\Program Files'),
            os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'),
            os.environ.get('LOCALAPPDATA', ''),
        ]
        for base in program_files:
            if not base:
                continue
            for subdir in ['Google/Chrome/Application', 'Chromium/Application']:
                candidate = os.path.join(base, subdir, 'chrome.exe')
                if os.path.isfile(candidate):
                    return candidate
    elif sys.platform == 'darwin':
        # macOS
        candidate = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
        if os.path.isfile(candidate):
            return candidate
    else:
        # Linux: try common paths
        for candidate in [
            '/usr/bin/google-chrome',
            '/usr/bin/google-chrome-stable',
            '/usr/bin/chromium',
            '/usr/bin/chromium-browser',
            '/snap/bin/chromium',
        ]:
            if os.path.isfile(candidate):
                return candidate

    return None


def print_pdf(html_path, pdf_path):
    """
    Uses Google Chrome Headless to generate a PDF from the HTML file.
    """
    chrome_path = find_chrome()

    if not chrome_path:
        print("Warning: Google Chrome not found.")
        print("PDF export requires Google Chrome or Chromium to be installed.")
        return False

    print(f"Generating PDF via Chrome Headless ({chrome_path})...")

    # We must use file:// absolute paths for Chrome to read local HTML
    abs_html_path = f"file://{os.path.abspath(html_path)}"
    abs_pdf_path = os.path.abspath(pdf_path)

    try:
        subprocess.run([
            chrome_path,
            "--headless",
            "--disable-gpu",
            "--no-margins",  # Prevent Chrome from injecting its own margins
            f"--print-to-pdf={abs_pdf_path}",
            abs_html_path
        ], check=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

        print(f"Success! Generated PDF at {abs_pdf_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error generating PDF: Chrome headless failed with code {e.returncode}")
        return False
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        return False