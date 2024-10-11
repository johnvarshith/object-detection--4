from flask import Flask, request, jsonify, render_template
import subprocess
import threading
import psutil
import logging

app = Flask(__name__)
processes = {}  # Dictionary to keep track of running processes
lock = threading.Lock()  # Lock to ensure thread safety

# Set up logging for better monitoring
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@app.route('/')
def index():
    return render_template('index1.html')

@app.route('/run-command', methods=['POST'])
def run_command():
    data = request.get_json()
    command = data.get('command')
    process_id = data.get('process_id')

    # Terminate existing process if process_id is provided
    if process_id:
        with lock:
            process_info = processes.get(process_id)
            if process_info:
                try:
                    proc = psutil.Process(int(process_info['pid']))
                    for child in proc.children(recursive=True):
                        child.kill()  # Kill child processes
                    proc.kill()  # Kill main process
                    processes.pop(process_id, None)
                    logging.info(f"Process {process_id} terminated successfully.")
                    return jsonify({'status': 'terminated', 'process_id': process_id})
                except psutil.NoSuchProcess:
                    processes.pop(process_id, None)
                    logging.warning(f"Process {process_id} not found, might have already terminated.")
                    return jsonify({'error': 'Process not found'})

    try:
        # Start a new process
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        process_id = str(process.pid)  # Use the process ID as a unique identifier
        with lock:
            processes[process_id] = {'pid': process_id}

        logging.info(f"Started new process with ID {process_id} running command: {command}")

        def stream_output():
            # Wait for the process to finish and capture stdout and stderr
            stdout, stderr = process.communicate()
            result = stdout + stderr
            with lock:
                processes.pop(process_id, None)
            logging.info(f"Process {process_id} completed. Output: {result}")

            # Optionally, you could store the result or send it to the frontend
            # Here, I just log it. You could add a websocket or polling mechanism for real-time updates.

        # Start a new thread to handle process output
        thread = threading.Thread(target=stream_output)
        thread.start()

        return jsonify({'process_id': process_id, 'status': 'running'})

    except Exception as e:
        logging.error(f"Failed to run command. Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Bind the app to 0.0.0.0 to make it accessible on the network
    app.run(host='0.0.0.0', port=5000, debug=True)
