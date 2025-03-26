import threading
import time
import ast

process_lock = threading.Lock()

time_counter = 1  # Shared Variable Start global time at 1s
time_running = True
memory_used = 0
main_memory = []
command_index = 0
running_processes = []

vm_file = None
output_file = None



def timer(): # Each time this runs in the timer thread, the time counter is incremented by 1. This keeps an accurate parallel time running
    global time_counter 
    while time_running:
        time.sleep(1)
        time_counter += 1
        print(f"Time: {time_counter}s")

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

    return processes # It's a list of tuples of start time and duration

def read_commands_file(filename="commands.txt"):  # Same as processes.txt, we open once and make a list. This is easier to use than fileIO
    with open(filename, 'r') as file:
        # Reads line by line. Strip() removes any whitespace at the beginning and end, and split() makes a substring out of the string.
        lines = [line.strip().split() for line in file.readlines()]
        commands = []

    for line in lines:
        command_line = [int(value) if value.isdigit() else value for value in line] # Only if each char is a digit.
        commands.append(command_line)

    return commands # These contain the actual commands, the variable ID, and the variable

def read_memconfig_file(filename="memconfig.txt"): # Extract number of pages from memconfig.txt, this one is pretty simple
    with open(filename, 'r') as file:
       memory_space = file.read().strip()

    return int(memory_space)


def store(variable, value): # Store a variable in memory, in pages of main memory or in disk memory if full.
    global memory_used, main_memory, memory_space, time_counter

    entry = (variable, value, time_counter)  # Third entry is last access time, for lookup

    if memory_used < memory_space: # We want ideally to keep it local
        main_memory.append(entry)
        memory_used += 1
        print(f"[STORE] Stored {entry} in main memory.")
    else:
        append_vm_file(entry)

        append_vm_file(entry)
        print(f"[STORE] Stored {entry} in disk (memory full). Saved to vm.txt.")


    return


def release(variableId): # Remove from memory
    global main_memory, memory_used

    disk_memory = get_vm_contents()
    for i, (var, val, access_time) in enumerate(main_memory):  # Try removing from main memory
        if var == variableId:
            removed = main_memory.pop(i)
            memory_used -= 1  # Free up space in main memory
            print(f"[RELEASE] Removed {removed} from main memory.")
            return True


    for i, (var, val, access_time) in enumerate(disk_memory):  # Try removing from disk memory
        if var == variableId:
            removed = disk_memory[i]

            remove_from_vm_file(removed)
            print(f"[RELEASE] Removed {removed} from disk memory.")
            return True

    print(f"[RELEASE] Variable {variableId} not found in memory.")
    return False


def lookup(variableId): # Find a variable in memory. If page fault occurs, take it out of the disk and move into main memory. if there's no space, move the least recently used memory into the disk memory
    global main_memory, time_counter, memory_used, memory_space

    # Search in main memory
    for i, (var, val, last_access) in enumerate(main_memory):
        if var == variableId:
            main_memory[i] = (var, val, time_counter)  # Update last access
            print(f"[LOOKUP] Found {variableId} in main memory. Value: {val}")
            return val

    # Search in disk memory (page fault)
    disk_memory = get_vm_contents()
    for i, (var, val, last_access) in enumerate(disk_memory):
        if var == variableId:
            print(f"[LOOKUP] Page fault: {variableId} found in disk.")

            # Remove from disk
            entry = disk_memory[i]

            remove_from_vm_file(entry)

            # If space in main memory, move in
            if memory_used < memory_space:
                main_memory.append((var, val, time_counter))
                memory_used += 1
                print(f"[LOOKUP] Moved {entry} to main memory.")
            else:
                # LRU Replacement (Least Recently Used)
                main_memory.sort(key=lambda x: x[2])  # Sort by last access time
                evicted = main_memory.pop(0)
                memory_used -= 1
                print(f"[LOOKUP] Swapping out {evicted} for {entry}")

                # Add evicted to disk
                append_vm_file(evicted)

                # Add new entry to main memory
                main_memory.append((var, val, time_counter))

            return val

    # Not found anywhere
    print(f"[LOOKUP] Variable {variableId} not found.")
    return -1




def fifo_scheduler(processes, file): # This scheduler is an adaptation of Assignment 2. It takes the list of processes and iterates across it, assigning the next one up to a thread on any free core. 
    global running_processes # Tracks processes that have been assigned to a thread
    waiting_queue = processes[:] # Remember we get processes from read_processes_file 

    while waiting_queue:
        for proc in waiting_queue[:]:
            if proc["start"] <= time_counter and len(running_processes) < max_cores: # max_cores works here to limit the number of threads 
                thread = threading.Thread(target=run_process, args=(proc, file)) # Assign a process to a thread 
                running_processes.append(proc["id"])
                thread.start()
                proc["thread"] = thread
                waiting_queue.remove(proc)

        time.sleep(0.1)  # This worked to keep the loop from going too fast in past assignments

    # Wait for all running threads to finish
    for proc in processes:
        proc["thread"].join()




def run_process(proc, file): # This is gonna be assigned to a thread. It will execute any of the three processes, store(), release(), or lookup()
    global running_processes, time_counter, command_index

    with process_lock:
        file.write(f"Clock: {time_counter}, Process {proc['id']}: Started.\n")
        print(f"Clock: {time_counter}, Process {proc['id']}: Started.")

    # Simulate command execution
    while proc["duration"] > 0:
        current_time = time_counter
        while time_counter == current_time:
            time.sleep(0.01)

        with process_lock:
            # Pick next command
            command = commands[command_index % len(commands)]
            command_index += 1

            if command[0].lower() == "store":
                _, var_id, value = command
                store(var_id, value)
                file.write(f"Clock: {time_counter}, Process {proc['id']}, Store: Variable {var_id}, Value: {value}\n")

            elif command[0].lower() == "release":
                _, var_id = command
                release(var_id)
                file.write(f"Clock: {time_counter}, Process {proc['id']}, Release: Variable {var_id}\n")

            elif command[0].lower() == "lookup":
                _, var_id = command
                val = lookup(var_id)
                file.write(f"Clock: {time_counter}, Process {proc['id']}, Lookup: Variable {var_id}, Result: {val}\n")

            else:
                print(f"Unknown command: {command}")
            
        
        proc["duration"] -= 1  # Simulate one second of work
        

    with process_lock:
        file.write(f"Clock: {time_counter}, Process {proc['id']}: Finished.\n")
        print(f"Clock: {time_counter}, Process {proc['id']}: Finished.")
        running_processes.remove(proc["id"])

def append_vm_file(new_entry):
    # Append a new entry to vm.txt.
    with open("vm.txt", "r+") as vm_file: # r+ is read and write
        vm_file.seek(0)
        contents = vm_file.read().strip()
        disk_memory = ast.literal_eval(contents) if contents else []

        disk_memory.append(new_entry)

        # Overwrite file with updated list
        vm_file.seek(0)
        vm_file.write(str(disk_memory))
        vm_file.truncate()

def remove_from_vm_file(entry):
    # Remove an entry from vm.txt.
    with open("vm.txt", "r+") as vm_file:
        vm_file.seek(0)
        contents = vm_file.read().strip()
        disk_memory = ast.literal_eval(contents) if contents else []

        try:
            disk_memory.remove(entry)
        except ValueError:
            print(f"[ERROR] {entry} not found in vm.txt.")
            return

        # Overwrite file with updated list
        vm_file.seek(0)
        vm_file.write(str(disk_memory))
        vm_file.truncate()

def get_vm_contents():
    # Read and return the list of entries in vm.txt.
    with open("vm.txt", "r") as vm_file:
        vm_file.seek(0)
        contents = vm_file.read().strip()

    return ast.literal_eval(contents) if contents else []


if __name__ == "__main__":
    virtual_memory = []
    commands = read_commands_file()
    processes = read_processes_file()
    memory_space = read_memconfig_file()

    with open("output.txt", 'w') as file:

        timer_thread = threading.Thread(target=timer)
        scheduler_thread = threading.Thread(target=fifo_scheduler, args=(processes, file))

        timer_thread.start()
        scheduler_thread.start()
        scheduler_thread.join() 
        time_running = False # Make timer stop
        timer_thread.join()
     
