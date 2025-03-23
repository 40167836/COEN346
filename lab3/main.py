import threading
import time

process_lock = threading.Lock()
#time_lock = threading.Lock()  # manage time thread

time_counter = 1  # Shared Variable Start global time at 1s
time_running = True


def timer():
    global time_counter 
    while time_running:
        time.sleep(1)
        time_counter += 1
        print(f"Time: {time_counter}s")
        

def read_input_file(filename="input.txt"):
    with open(filename, 'r') as file:
        #reads line by line. Strip() removes any whitespace at the beginning and end, and split() makes a substring out of the string.
        lines = [line.strip().split() for line in file.readlines()] 

    quantum = int(lines[0][0])  # first line is the quantum
    processes = []
    user_process_counts = {}

    i = 1
    while i < len(lines):
        if len(lines[i]) == 2:
            username, num_processes = lines[i][0], int(lines[i][1])

            if username not in user_process_counts:
                user_process_counts[username] = 0 #this will be the process id
            
            for _ in range(num_processes): #runs through n lines (which will be process lines) associated with n processes belonging to user
                i += 1
                ready_time, burst_time = map(int, lines[i])
                
                process_id = user_process_counts[username] #process id assignment
                processes.append([username, ready_time, burst_time, process_id])
                
                user_process_counts[username] += 1 #process id increment

        i += 1  #we incremented I in the processes loop above. once that stops running we increment again to the next user.

    return quantum, processes



def fair_share_scheduler(quantum, processes, file):
    global time_counter

    while processes:
        active_users = list(set(p[0] for p in processes if p[1] <= time_counter)) #all users with active processes
        num_active_users = len(active_users)

        if num_active_users == 0: #stop if no users
            break

        user_share = quantum // num_active_users
        executed_any = False #manages process has-executed logic

        userThreads = []
        for user in active_users:
            #each user will have their own thread for scheduling
            user_thread = threading.Thread(target=process_select, args=(user, processes, user_share, time_counter, file))
            userThreads.append(user_thread)
            user_thread.start()

        for user_thread in userThreads:
            user_thread.join()  #ensure all user threads are finished before continuing

        processes = [p for p in processes if p[2] > 0] #if a process has finished, take it out of the list



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

def run_process(user, process_id, execution_time, process, file):
    global time_counter, process_started
    if execution_time > 0:
        with process_lock:
            if (user, process_id) not in process_started:
                file.write(f"Time {time_counter}, User {user}, Process {process_id}, Started\n")
                process_started[(user, process_id)] = True  # Mark process as started
            else:
                file.write(f"Time {time_counter}, User {user}, Process {process_id}, Resumed\n")

             # Wait for each second of execution
        for _ in range(execution_time):
            # Wait until time_counter increases (simulate real-time execution)
            current_time = time_counter
            while time_counter == current_time:
                time.sleep(0.01)  # Light sleep to avoid CPU hogging

            # Decrease burst time one second at a time
            with process_lock:
                process[2] -= 1
                if process[2] <= 0:
                    process[2] = 0
                    file.write(f"Time {time_counter}, User {user}, Process {process_id}, Finished\n")
                    return  # Done
                
        # If not finished, log pause
        with process_lock:
            file.write(f"Time {time_counter}, User {user}, Process {process_id}, Paused\n")




if __name__ == "__main__":

    quantum, processes = read_input_file()
    with open("output.txt", 'w') as file:

        scheduler_thread = threading.Thread(target=fair_share_scheduler, args=(quantum,processes,file))
        timer_thread = threading.Thread(target=timer)

        timer_thread.start()
        scheduler_thread.start()
        scheduler_thread.join() 
        time_running = False # Make timer stop
        timer_thread.join()
     
