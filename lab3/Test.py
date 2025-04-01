import threading
import time
import ast
import random
import queue

process_lock = threading.Lock()

memory_queue = queue.Queue()

time_counter = 0  # Shared Variable Start global time at 1s
time_running = True
memory_used = 0
main_memory = []
command_index = 0
running_processes = []


vm_file = None
output_file = None

lookup_results = {}
sleep = 0
def random_sleep():
 
    return (random.randint(1, 1000))/1000
# We execute the following three methods once at the beginning of the run to configure the CPU

def read_processes_file(filename="processes.txt"): # We open the processes.txt file once, extract the information, and return it as a list
    global max_cores
    with open(filename, 'r') as file:
        lines = [line.strip().split() for line in file.readlines()]

    max_cores = int(lines[0][0]) # max_cores is the number of cores obviously, we need to know how many threads run at once 
    num_processes = int(lines[1][0])

    processes = []
    for i in range(2, 2 + num_processes): # We start at 2 since 0 is the number of cores, and 1 is the number of processes
        start_time, duration = map(int, lines[i])
        processes.append({"id": i - 2, "start": start_time, "duration": duration}) # Readable format for other methods

    return processes

def read_commands_file(filename="commands.txt"): # Same as processes.txt, we open once and make a list. This is easier to use than fileIO
    with open(filename, 'r') as file:
         # Reads line by line. Strip() removes any whitespace at the beginning and end, and split() makes a substring out of the string.
        lines = [line.strip().split() for line in file.readlines()]
        commands = []

    for line in lines:
        command_line = [int(value) if value.isdigit() else value for value in line]# Only if each char is a digit.
        commands.append(command_line)

    return commands # These contain the actual commands, the variable ID, and the variable

def read_memconfig_file(filename="memconfig.txt"):# Extract number of pages from memconfig.txt, this one is pretty simple
    with open(filename, 'r') as file:
        memory_space = file.read().strip()

    return int(memory_space)

def timer(): # Each time this runs in the timer thread, the time counter is incremented by a random time. This keeps an accurate parallel time running
    global time_counter
    while time_running:
        global sleep
        sleep = random_sleep()
        time.sleep(sleep)
        time_counter += sleep
        print(f"Time: {time_counter}s")

#the next 3 functions put memory commands in a queue that can be accessed by the memeory manager that is running in its own thread.
def store(variable, value): 
    memory_queue.put(("store", (variable, value)))

def release(variableId):
    memory_queue.put(("release", (variableId,)))

def lookup (variableId):
    memory_queue.put(("lookup", (variableId,)))

def lookup_memory(variableId, current_time):
    global main_memory, time_counter, memory_used, memory_space
    swap = False 
    # Search in main memory
    for i, (var, val, last_access) in enumerate(main_memory):
        if var == variableId:
            # Update last access time
            main_memory[i] = (var, val, time_counter)
            print(f"[LOOKUP] Found {variableId} in main memory. Value: {val}")
            return val, swap 

    # If not found in main memory, we need to page fault
    print(f"[LOOKUP] Page fault: {variableId} not found in main memory.")
    
    # Fetch from disk memory
    disk_memory = get_vm_contents()
    for i, (var, val, last_access) in enumerate(disk_memory):
        if var == variableId:
            # Move to main memory (if there's space)
            print(f"[LOOKUP] Page fault: {variableId} found in disk memory.")
            entry = disk_memory[i]
            remove_from_vm_file(entry)

            if memory_used < memory_space:
                # Space available in main memory
                main_memory.append((var, val, time_counter))
                memory_used += 1
                print(f"[LOOKUP] Moved {entry} to main memory.")
            else:
                # Evict LRU entry if memory is full
                main_memory.sort(key=lambda x: x[2])  # Sort by last access time (LRU eviction)
                evicted = main_memory.pop(0)
                memory_used -= 1
                swap = True
                file.write(f"Clock: {current_time + 0.005}, Memory Manager, Swap : Variable {entry[0]} with Variable {evicted[0]}\n")
                print(f"[LOOKUP] Swapping out {evicted} for {entry}")


                # Write evicted to disk
                append_vm_file(evicted)

                # Add the new entry to main memory
                main_memory.append((var, val, time_counter))

            return val, swap

    print(f"[LOOKUP] Variable {variableId} not found in memory or disk.")
    return -1

def memory_manager():
    while time_running:
        try:
            operation, args = memory_queue.get(timeout=1)
            if operation == "store":
                store_memory(*args)
            elif operation == "release":
                release_memory(*args)
            elif operation == "lookup":
                variableId = args
                result = lookup_memory(variableId)
                lookup_results[variableId] = result  # Store the result for later
        except queue.Empty:
            pass

def store_memory(variable, value):# Store a variable in memory, in pages of main memory or in disk memory if full.
    global memory_used, main_memory, memory_space, time_counter

    entry = (variable, value, time_counter) # Third entry is last access time, for lookup

    if memory_used < memory_space: # We want ideally to keep it local
        main_memory.append(entry)
        memory_used += 1
        print(f"[STORE] Stored {entry} in main memory.")

    else:
        append_vm_file(entry)
        print(f"[STORE] Stored {entry} in disk (memory full). Saved to vm.txt.")

def release_memory(variableId): # Remove from memory
    global main_memory, memory_used
    disk_memory = get_vm_contents()
    for i, (var, val, access_time) in enumerate(main_memory):  # Try removing from main memory
        if var == variableId:
            main_memory.pop(i)
            memory_used -= 1  # Free up space in main memory
            return True 
        
    for i, (var, val, access_time) in enumerate(disk_memory): # Try removing from disk memory
        if var == variableId:
            remove_from_vm_file(disk_memory[i])
            return True
        
    return True 

def append_vm_file(new_entry):
    with open("vm.txt", "r+") as vm_file:
        vm_file.seek(0)
        contents = vm_file.read().strip()
        disk_memory = ast.literal_eval(contents) if contents else []
        disk_memory.append(new_entry)
        vm_file.seek(0)
        vm_file.write(str(disk_memory))
        vm_file.truncate()

def remove_from_vm_file(entry):
    with open("vm.txt", "r+") as vm_file:
        vm_file.seek(0)
        contents = vm_file.read().strip()
        disk_memory = ast.literal_eval(contents) if contents else []
        try:
            disk_memory.remove(entry)
        except ValueError:
            print(f"[ERROR] {entry} not found in vm.txt.")
            return
        vm_file.seek(0)
        vm_file.write(str(disk_memory))
        vm_file.truncate()

def get_vm_contents():
    with open("vm.txt", "r") as vm_file:
        vm_file.seek(0)
        contents = vm_file.read().strip()
    return ast.literal_eval(contents) if contents else []

def fifo_scheduler(processes, file):
    global running_processes
    waiting_queue = processes[:]
    while waiting_queue:
        for proc in waiting_queue[:]:
            if proc["start"] <= time_counter and len(running_processes) < max_cores:
                thread = threading.Thread(target=run_process, args=(proc, file))
                running_processes.append(proc["id"])
                thread.start()
                proc["thread"] = thread
                waiting_queue.remove(proc)
        time.sleep(0.1)
    for proc in processes:
        proc["thread"].join()

def run_process(proc, file):
    global running_processes, time_counter, command_index, sleep
    
    with process_lock:
        file.write(f"Clock: {proc['start']}, Process {proc['id']}: Started.\n")
        print(f"Clock: {proc['start']}, Process {proc['id']}: Started.")
        duration = proc["duration"]
    while True: 
        
        current_time = time_counter
        if current_time >= proc["duration"] + proc["start"]:
            break

        while time_counter == current_time:
            time.sleep(0.01)
        with process_lock:
            if command_index < len(commands):
                command = commands[command_index % len(commands)]
                command_index += 1
                if command[0].lower() == "store":
                    _, var_id, value = command
                    store(var_id, value)
                    file.write(f"Clock: {current_time}, Process {proc['id']}, Store: Variable {var_id}, Value: {value}\n")
                elif command[0].lower() == "release":
                    _, var_id = command
                    release(var_id)
                    file.write(f"Clock: {current_time}, Process {proc['id']}, Release: Variable {var_id}\n")
                elif command[0].lower() == "lookup":
                    _, var_id = command
                    val, swap = lookup_memory(var_id, current_time)
                    if swap == False:
                        file.write(f"Clock: {current_time}, Process {proc['id']}, Lookup: Variable {var_id}, Result: {val}\n")
                    elif swap == True:  
                        file.write(f"Clock: {current_time + 0.010}, Process {proc['id']}, Lookup: Variable {var_id}, Result: {val}\n")
                    
                else:
                    print(f"Unknown command: {command}")

            print(f"Clock: {time_counter}, Process {proc['id']} duration remaining: {proc['duration']}")
            current_time = time_counter
    with process_lock:
        finish = proc["start"] + duration
        file.write(f"Clock: {finish}, Process {proc['id']}: Finished.\n")
        print(f"Clock: {finish}, Process {proc['id']}: Finished.")
        running_processes.remove(proc["id"])

if __name__ == "__main__":
    commands = read_commands_file()
    processes = read_processes_file()
    memory_space = read_memconfig_file()
    with open("vm.txt", "w") as file:
        pass
    with open("output.txt", "w") as file:
        timer_thread = threading.Thread(target=timer)
        scheduler_thread = threading.Thread(target=fifo_scheduler, args=(processes, file))
        memory_thread = threading.Thread(target=memory_manager)
        timer_thread.start()
        memory_thread.start()
        scheduler_thread.start()
        scheduler_thread.join()
        time_running = False
        timer_thread.join()
        memory_thread.join()
