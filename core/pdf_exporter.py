import os
import subprocess
import sys

def print_pdf(html_path, pdf_path):
    """
    Uses Google Chrome Headless to generate a PDF from the HTML file.
    Only supported on macOS if Chrome is installed in the default Applications folder.
    """
    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    
    if not os.path.exists(chrome_path):
        print(f"Warning: Chrome not found at {chrome_path}")
        print("PDF export is currently only supported automatically on macOS with Google Chrome installed.")
        return False
        
    print("Generating PDF via Chrome Headless...")
    
    # We must use file:// absolute paths for Chrome to read local HTML
    abs_html_path = f"file://{os.path.abspath(html_path)}"
    abs_pdf_path = os.path.abspath(pdf_path)
    
    try:
        # We pipe stderr to DEVNULL to silence Chrome's internal CoreVideo errors on Mac
        subprocess.run([
            chrome_path,
            "--headless",
            "--disable-gpu",
            "--no-margins", # Prevent Chrome from injecting its own margins
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