import http.server
import socketserver
import threading
import webbrowser

def open_webapp(directory='reports', file_path='index.html', port=8000, quiet=False):
    """Starts a web server and opens the specified file in the browser."""

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)

        def log_message(self, format, *args):
            if not quiet:  # Only log if not in quiet mode
                super().log_message(format, *args)

    with socketserver.TCPServer(("", port), QuietHandler) as httpd:
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        webbrowser.open(f'http://localhost:{port}/{file_path}')
        input("Press Enter to stop the server...")
        httpd.shutdown()

if __name__ == "__main__":
    open_webapp(quiet=True)  # Start in quiet mode by default