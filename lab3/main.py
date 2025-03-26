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
    global time_counter, commands, command_index, memory_used, main_memory, disk_memory

    if memory_used < memory_space: 
        main_memory.append(variable)
        main_memory.append(value) 
        command_index += 2
        memory_used += 1
    else:
        disk_memory.append(commands[command_index+1])
        disk_memory.append(commands[command_index+2]) 
        command_index += 2
    time_counter += 1
    time.sleep(1)
    return 

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



def process_select(user, processes, user_share, time_counter, file):
    processThreads = []  #threads for processes of the current user
    #process selection logic
    user_processes = [p for p in processes if p[0] == user and p[1] <= time_counter]
    num_user_processes = len(user_processes)

    if num_user_processes == 0:
        return #no processes

    process_share = user_share // num_user_processes  #divide user’s share among processes
    remaining_quantum = process_share

    for process in user_processes:
        if process[2] == 0:
            continue

        execution_time = min(process[2], remaining_quantum)

        process_thread = threading.Thread(target=run_process, args=(process[0], process[3], execution_time, process, file))
        processThreads.append(process_thread)
        process_thread.start()

    for thread in processThreads:
        thread.join()

process_started = {}  #tracks started processes

def run_process(proc, file):
    global running_processes, time_counter
    with process_lock:
        file.write(f"Clock: {time_counter}, Process {proc['id']}: Started.\n")
        print(f"Clock: {time_counter}, Process {proc['id']}: Started.")

    for _ in range(proc["duration"]):
        current_time = time_counter
        while time_counter == current_time:
            time.sleep(0.01)

    with process_lock:
        file.write(f"Clock: {time_counter}, Process {proc['id']}: Finished.\n")
        print(f"Clock: {time_counter}, Process {proc['id']}: Finished.")
        running_processes.remove(proc["id"])

def release(variableId):
    virtual_memory = read_main_memory()
    disk_memory = read_disk_memory()
    
    for index, (id, ) in enumerate(virtual_memory):
        if id == variableId:
            removed_tuple = virtual_memory.pop(index)  # Remove the matching tuple
            return index, removed_tuple
        else:
            for index, (id, ) in enumerate(disk_memory):
                if id == variableId:
                    removed_tuple = disk_memory.pop(index)  # Remove the matching tuple
                    return index, removed_tuple
    return None

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
     
