import threading
import time

# Lock for process synchronization
process_lock = threading.Lock()

###### FUNCTION TO READ INPUT ######
def read_input_file(filename="input.txt"):
    """ Reads input and structures it into a flattened list of lists. """

    with open(filename, 'r') as file:
        lines = [line.strip().split() for line in file.readlines()]  

    quantum = int(lines[0][0])  # Extract the quantum time (first line)
    processes = []  # Flattened list like [['A', 1, 5], ['A', 4, 3], ['B', 5, 6]] 
    unique_users = set()  # Track unique users

    i = 1  # Start processing from the second line (index 1)
    while i < len(lines):
        if len(lines[i]) == 2:  # Detect user line (username + num of processes)
            username, num_processes = lines[i][0], int(lines[i][1])  
            unique_users.add(username)  

            # Read and store next `num_processes` lines directly
            for _ in range(num_processes):
                i += 1  # Move to next line
                ready_time, burst_time = map(int, lines[i])  # Convert arrival/burst times
                processes.append([username, ready_time, burst_time])  # (User, Ready, Burst)
            
        i += 1  # Move to next user

    num_active_users = len(unique_users)  # Count unique users
    return num_active_users, quantum, processes  # Return active user count, quantum, process list


###### FUNCTION TO SIMULATE PROCESS EXECUTION ######
def run_process(user, process_id, execution_time, process):
    """ Simulates the execution of a process, updating burst time. """
    with process_lock:
        print(f"Time {time_counter}s, User {user}, Process {process_id}, Started, Remaining Burst: {process[2]}")
        print(f"Time {time_counter}s, User {user}, Process {process_id}, Resumed, Remaining Burst: {process[2]}")

    time.sleep(execution_time)  # Simulate execution delay

    with process_lock:  # Update process burst safely
        process[2] -= execution_time  # Reduce burst time
        if process[2] <= 0:
            process[2] = 0  # Ensure it doesn’t go negative
            print(f"Time {time_counter + execution_time}s, User {user}, Process {process_id}, Finished, Remaining Burst: {process[2]}")
        else:
            print(f"Time {time_counter + execution_time}s, User {user}, Process {process_id}, Paused, Remaining Burst: {process[2]}")


###### FUNCTION FOR FAIR-SHARE ROUND ROBIN SCHEDULING ######
def fair_share_scheduler(num_active_users, quantum, processes):
    """ Implements Fair-Share Round Robin Scheduling with strict quantum enforcement. """

    global time_counter
    time_counter = 1  # **Clock starts at 1s**

    print("\n--- Initial Scheduler Variables ---")
    print(f"Number of Active Users: {num_active_users}")
    print(f"Quantum Time: {quantum}")
    print(f"Processes: {processes}")
    print("\n--- Starting Scheduler ---\n")

    while processes:  # Run until all processes are completed
        active_users = list(set(p[0] for p in processes))  # Get unique users
        num_active_users = len(active_users)  # Update active users count

        if num_active_users == 0:
            break  # Stop if no active users are left

        user_share = quantum // num_active_users  # Divide quantum among users

        executed_any = False  # Track if a process was executed

        for user in active_users:
            user_processes = [p for p in processes if p[0] == user and p[1] <= time_counter]  # Get user’s ready processes
            num_user_processes = len(user_processes)

            if num_user_processes == 0:
                continue  # Skip if no processes are ready

            process_share = user_share // num_user_processes  # Divide user’s share among processes

            remaining_quantum = user_share  # Available quantum for this user

            for process in user_processes:  # Iterate through all user processes
                if process[2] == 0:
                    continue  # Skip completed processes

                # **Determine execution time: If no other processes exist, run full quantum**
                execution_time = min(process[2], remaining_quantum)
                
                print(f"Time {time_counter}s: Scheduling process {process} for {execution_time}s execution.")

                # Start process in a thread and update burst time
                process_thread = threading.Thread(target=run_process, args=(process[0], processes.index(process), execution_time, process))
                process_thread.start()
                process_thread.join()

                time_counter += execution_time  # Advance time based on execution
                remaining_quantum -= execution_time  # Reduce available quantum
                executed_any = True  # Mark that at least one process was executed

                if process[2] == 0:
                    print(f"Process {process} fully completed and removed.")

                if remaining_quantum <= 0:
                    break  # Stop scheduling when quantum expires

            # Remove completed processes
            processes = [p for p in processes if p[2] > 0]

        if not executed_any:  # If no process ran, advance time
            print(f"Time {time_counter}s: No processes ready. Advancing time.")
            time_counter += 1
            time.sleep(1)

    print("\n--- Scheduler Stopped ---")


###### MAIN EXECUTION ######
if __name__ == "__main__":
    # Read and organize input from the file
    num_active_users, quantum, processes = read_input_file()

    # Run Fair-Share Round Robin Scheduler
    fair_share_scheduler(num_active_users, quantum, processes)
