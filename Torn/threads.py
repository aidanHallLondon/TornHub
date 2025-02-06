import http.server
import socketserver
import threading
import webbrowser
import time
import signal
import sys

httpd = None
server_thread = None

def start_httpd_server(directory='reports', file_path='index.html', port=8000, quiet=True):
    global httpd, server_thread

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)

        def log_message(self, format, *args):
            if not quiet:
                super().log_message(format, *args)

    if httpd is None:
        httpd = socketserver.TCPServer(("", port), QuietHandler)
        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()
        webbrowser.open(f'http://localhost:{port}/{file_path}')
        print("Server started.")
    else:
        print("Server is already running.")

def stop_hhtpd_server():
    global httpd, server_thread
    if httpd:
        httpd.shutdown()
        httpd.server_close()
        if server_thread: # added check in case it has not been instantiated.
          server_thread.join()
        httpd = None
        server_thread = None
        print("Server stopped.")
    else:
        print("Server is not running.")



class BackgroundTask:
    def __init__(self, task_function, *args, **kwargs):
        """
        Initializes the BackgroundTask.

        Args:
            task_function: The function to be executed in the background.
            *args: Positional arguments to pass to task_function.
            **kwargs: Keyword arguments to pass to task_function.
        """
        self.task_function = task_function
        self.args = args
        self.kwargs = kwargs
        self.shutdown_event = threading.Event()
        self.thread = None  # Initialize the thread attribute

    def _run_task(self):
        """
        Wrapper function that runs the task and handles the shutdown event.
        """
        while not self.shutdown_event.is_set():
            try:
                self.task_function(*self.args, **self.kwargs)
            except Exception as e:
                print(f"Error in background task: {e}")
                #  Consider adding a retry mechanism here, or logging the error.
                break  # Or, you might choose to continue, depending on the task
            if not self.shutdown_event.is_set():  # Check again before sleeping
                time.sleep(1)  #  Short sleep to avoid busy-waiting.

        print("Background task stopped.")


    def start(self):
        """Starts the background task in a separate thread."""
        if self.thread is not None and self.thread.is_alive():
            print("Background task is already running.")
            return

        self.shutdown_event.clear()  # Make sure the event is cleared
        self.thread = threading.Thread(target=self._run_task)
        self.thread.daemon = True  # Allow main program to exit even if thread is running
        self.thread.start()
        print("Background task started.")

    def stop(self):
        """Signals the background task to stop."""
        if self.thread is not None and self.thread.is_alive():
            print("Stopping background task...")
            self.shutdown_event.set()  # Signal the thread to stop
            self.thread.join()  # Wait for the thread to finish
            self.thread = None #reset the thread.
            print("Background task stopped.")
        else:
            print("Background task is not running.")


def combined_signal_handler(background_task_instance, sig, frame):
    """Handles Ctrl+C (SIGINT) and SIGTERM for both server and background task."""
    print('You pressed Ctrl+C! Shutting down...')
    if background_task_instance:
        background_task_instance.stop()
    stop_hhtpd_server()
    sys.exit(0)

def run_background_threads_and_exit(func,conn,cursor):
    background_task = BackgroundTask(func,conn,cursor)
    signal.signal(signal.SIGINT, lambda sig, frame: combined_signal_handler(background_task, sig, frame))
    signal.signal(signal.SIGTERM, lambda sig, frame: combined_signal_handler(background_task, sig, frame))
    # Start the HTTP server and background task
    start_httpd_server(quiet=True)
    background_task.start()
    try:
        print('''\n\n\n\n=====================================''')
        input("Press Enter at any time to stop the server and background task...\n\n")
    except KeyboardInterrupt:
        pass # Already handled by signal handler
    finally:
        background_task.stop()
        stop_hhtpd_server()
        time.sleep(2)
        print('\n\nDONE')

# --- Example Usage ---

# if __name__ == "__main__":

#     def my_background_task(message, interval):
#         """Example task - replace with your API calling function."""
#         print(f"Task running: {message} every {interval} seconds")
#         time.sleep(interval)

#     # Create an instance of BackgroundTask.  Do this *before* setting up
#     # the signal handler, so the handler can access it.
#     background_task = BackgroundTask(my_background_task, message="Hello from the background!", interval=3)


#     # Set up signal handling, passing the background_task instance
#     signal.signal(signal.SIGINT, lambda sig, frame: combined_signal_handler(background_task, sig, frame))
#     signal.signal(signal.SIGTERM, lambda sig, frame: combined_signal_handler(background_task, sig, frame))
#     # Start the HTTP server
#     start_httpd_server(quiet=True)

#     # Start the background task
#     background_task.start()


#     try:
#         input("Press Enter to stop the server and background task...\n")
#     except KeyboardInterrupt:
#         pass # Already handled by signal handler
#     finally:
#         background_task.stop()
#         stop_hhtpd_server()
#         time.sleep(2)