import threading
import time

process_lock = threading.Lock()

time_counter = 1  # Shared Variable Start global time at 1s
time_running = True
memory_used = 0
main_memory = []
disk_memory = []
command_index = 0
running_processes = []


def timer():
    global time_counter 
    while time_running:
        time.sleep(1)
        time_counter += 1
        print(f"Time: {time_counter}s")




def read_processes_file(filename="processes.txt"):
    global max_cores
    with open(filename, 'r') as file:
        lines = [line.strip().split() for line in file.readlines()]

    max_cores = int(lines[0][0])
    num_processes = int(lines[1][0])

    processes = []
    for i in range(2, 2 + num_processes):
        start_time, duration = map(int, lines[i])
        processes.append({"id": i - 2, "start": start_time, "duration": duration})

    return processes

def read_commands_file(filename="commands.txt"):
    with open(filename, 'r') as file:
        #reads line by line. Strip() removes any whitespace at the beginning and end, and split() makes a substring out of the string.
        lines = [line.strip().split() for line in file.readlines()]
        commands = []

    for line in lines:
        command_line = [int(value) if value.isdigit() else value for value in line]
        commands.append(command_line)  # Appends a list with converted values

    return commands

def read_memconfig_file(filename="memconfig.txt"):
    with open(filename, 'r') as file:
       memory_space = file.read().strip()

    return int(memory_space)




def store(variable, value):
    global memory_used, main_memory, disk_memory, memory_space, time_counter

    entry = (variable, value, time_counter)  # Add Last Access Time (for lookup later)

    if memory_used < memory_space:
        main_memory.append(entry)
        memory_used += 1
        print(f"[STORE] Stored {entry} in main memory.")
    else:
        disk_memory.append(entry)
        with open("vm.txt", 'w') as vm_file:
             vm_file.write(str(disk_memory))
        print(f"[STORE] Stored {entry} in disk (memory full). Saved to vm.txt.")


    return


def release(variableId):
    global main_memory, disk_memory, memory_used

    # Try removing from main memory
    for i, (var, val, access_time) in enumerate(main_memory):
        if var == variableId:
            removed = main_memory.pop(i)
            memory_used -= 1  # Free up space in main memory
            print(f"[RELEASE] Removed {removed} from main memory.")
            return True

    # Try removing from disk memory
    for i, (var, val, access_time) in enumerate(disk_memory):
        if var == variableId:
            removed = disk_memory.pop(i)
            with open("vm.txt", 'w') as vm_file:
                vm_file.write(str(disk_memory))  # Save updated disk
            print(f"[RELEASE] Removed {removed} from disk memory.")
            return True

    print(f"[RELEASE] Variable {variableId} not found in memory.")
    return False


def lookup(variableId):
    global main_memory, disk_memory, time_counter, memory_used, memory_space

    # Search in main memory
    for i, (var, val, last_access) in enumerate(main_memory):
        if var == variableId:
            main_memory[i] = (var, val, time_counter)  # Update last access
            print(f"[LOOKUP] Found {variableId} in main memory. Value: {val}")
            return val

    # Search in disk memory (page fault)
    for i, (var, val, last_access) in enumerate(disk_memory):
        if var == variableId:
            print(f"[LOOKUP] Page fault: {variableId} found in disk.")

            # Remove from disk
            entry = disk_memory.pop(i)
            with open("vm.txt", 'w') as vm_file:
                vm_file.write(str(disk_memory))

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
                disk_memory.append(evicted)
                with open("vm.txt", 'w') as vm_file:
                    vm_file.write(str(disk_memory))

                # Add new entry to main memory
                main_memory.append((var, val, time_counter))

            return val

    # Not found anywhere
    print(f"[LOOKUP] Variable {variableId} not found.")
    return -1




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

        time.sleep(0.1)  # Avoid tight loop

    # Wait for all running threads to finish
    for proc in processes:
        proc["thread"].join()




def run_process(proc, file):
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





def read_disk_memory():
    with open("vm.txt", 'r') as file:
        disk_memory_string = file.read().strip()
        return eval(disk_memory_string)

def read_main_memory():
    global virtual_memory
    return virtual_memory


if __name__ == "__main__":
    virtual_memory = []
    commands = read_commands_file()
    processes = read_processes_file("processes.txt")
    memory_space = read_memconfig_file()

    with open("output.txt", 'w') as file:

        timer_thread = threading.Thread(target=timer)
        scheduler_thread = threading.Thread(target=fifo_scheduler, args=(processes, file))

        timer_thread.start()
        scheduler_thread.start()
        scheduler_thread.join() 
        time_running = False # Make timer stop
        timer_thread.join()
     
