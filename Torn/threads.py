import http.server
import socketserver
import threading
import webbrowser
import time
import signal
import sys
import queue
import select  # For non-blocking input


httpd=None

# EXAMPLE

#  Close the database and run the background thread in leiue of exiting
#  Pass a function to be called on a regular heartbeat beased on interval
#
#     conn.commit()
#     conn.close()
#     run_background_threads_and_exit(
#         main_thread_func = main_thread_update,
#         interval=BACKGROUND_UPDATE_DUTY_CYCLE_SECONDS,
#     )
#     # END OF THIS CODE
#  
#  Example main thread update function
#
# def main_thread_update():
#     last_update = get_last_updateDB_delta()
#     if (
#         last_update is None
#         or last_update > BACKGROUND_UPDATE_UPDATEDB_DUTY_CYCLE_SECONDS
#     ):
#         print("\n")
#         conn = sqlite3.connect(DB_CONNECTPATH, detect_types=sqlite3.PARSE_DECLTYPES)
#         cursor = conn.cursor()
#         updateDB(conn, cursor)
#         generate_reporting(conn, cursor)
#         conn.commit()
#         conn.close()
#         print("\nMain thread: Update complete. Press ENTER to exit.")



def run_background_threads_and_exit( *args, **kwargs):  # Add *args, **kwargs here
    update_queue = queue.Queue()  # Create the queue
    background_task = BackgroundTask(_background_thread_task, update_queue, *args, **kwargs)  # Pass args and kwargs
    signal.signal(signal.SIGINT, lambda sig, frame: combined_signal_handler(background_task, sig, frame))
    signal.signal(signal.SIGTERM, lambda sig, frame: combined_signal_handler(background_task, sig, frame))
    # Start the HTTP server and background task
    start_httpd_server(quiet=True)
    background_task.start()

    try:
        print('''\n\n\n\n=====================================''')
        print("Press Enter at any time to stop the server and background task...\n")
        while True:
          # Check the update queue
          try:
              update_task = update_queue.get_nowait()  # Non-blocking get
              update_task()  # Execute the update function
          except queue.Empty:
              pass

          i, o, e = select.select([sys.stdin], [], [], 0.1)
          if i:  # If there's input on stdin
            user_input = sys.stdin.readline().strip()
            if user_input == "":  # Enter key pressed
                break
          time.sleep(0.1)
    except KeyboardInterrupt:
        pass # Already handled by signal handler
    finally:
        print('background_task.stop')
        background_task.stop()
        print('stop_hhtpd_server')
        stop_hhtpd_server()
        time.sleep(2)
        print('\n\nDONE')

def _background_thread_task(update_queue, main_thread_func, interval):
    print(f"♡",end="",flush=True)
    update_queue.put(main_thread_func)  # Put function on the queue
    time.sleep(interval)





class BackgroundTask:
    def __init__(self, task_function, update_queue, *args, **kwargs):
        """
        Initializes the BackgroundTask.

        Args:
            task_function: The function to be executed in the background.
            update_queue: Queue for communication with the main thread.
            *args: Positional arguments to pass to task_function.
            **kwargs: Keyword arguments to pass to task_function.
        """
        self.task_function = task_function
        self.update_queue = update_queue
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
                # Pass the update_queue AND the original args/kwargs
                self.task_function(self.update_queue, *self.args, **self.kwargs)
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

def combined_signal_handler(background_task_instance, sig, frame):
    """Handles Ctrl+C (SIGINT) and SIGTERM for both server and background task."""
    print('You pressed Ctrl+C! Shutting down...')
    if background_task_instance:
        background_task_instance.stop()
    stop_hhtpd_server()
    sys.exit(0)

