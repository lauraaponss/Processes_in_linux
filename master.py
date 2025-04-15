import os
import sys
import signal
import time
import select
from sensor import Sensor

class Master:
    """
    Master class that manages multiple robots in a room, coordinates their movements,
    and keeps track of discovered treasures and room state.
    """
    def __init__(self, room_file, robots_file):
        # Store file paths
        self.room_file = room_file
        self.robots_file = robots_file

        # Initialize sensor and get room information
        self.sensor = Sensor(room_file)
        self.dimensions = self.sensor.dimensions()
        self.n_treasures = self.sensor.n_treasures()
        self.treasures_found = 0
        self.robots = {}  # {robot_id: {"pid": pid, "position": [row, col], "pipe_read": pipe_read, "pipe_write": pipe_write}}
        self.room_info = []  # Store what we know about the room
        self.discovered_treasures = set()  # Store positions of discovered treasures
        self.initialize_room_info()
        self.initialize_robots()

    def initialize_room_info(self):
        """
        Initializes the room grid and identifies treasure positions and obstacles.
        Room is represented as a 2D grid where:
        - '?' represents unexplored areas
        - 'X' represents obstacles
        - 'R' represents robots
        - 'T' represents discovered treasures
        - 'RT' represents a robot on a treasure
        - '-' represents explored empty space
        """
        rows, cols = self.dimensions
        self.room_info = [['?' for _ in range(cols)] for _ in range(rows)] # INitialize room with unexplored cells
        # Check obstacles only during initialization
        for i in range(rows):
            for j in range(cols):
                if self.sensor.with_obstacle(i, j):
                    self.room_info[i][j] = 'X'

    def initialize_robots(self):
        """
        Creates robot processes and sets up communication pipes.
        Each robot is a separate process that communicates with the master through pipes.
        """
        # Read robot positions from file
        with open(self.robots_file, 'r') as f:
            robot_positions = f.readlines()
        
        # Create a process for each robot
        for i, pos in enumerate(robot_positions, 1):
            pos = pos.strip().replace('(', '').replace(')', '').split(',')
            row, col = int(pos[0]), int(pos[1])
            
            # Check if position is valid
            if self.sensor.with_obstacle(row, col):
                print(f"Invalid initial position for robot at ({row}, {col})", file=sys.stderr)
                sys.exit(1)
            
            # Check if position is already occupied by another robot
            for robot in self.robots.values():
                if robot["position"] == [row, col]:
                    print(f"Invalid initial position for robot at ({row}, {col}): position already occupied", file=sys.stderr)
                    sys.exit(1)

            # Create pipes for communication
            pipe_parent_read, pipe_child_write = os.pipe()
            pipe_child_read, pipe_parent_write = os.pipe()
            
            pid = os.fork() # Fork a new process for the robot
            if pid == 0:  # Child process
                os.close(pipe_parent_read)
                os.close(pipe_parent_write)
                # Redirect stdin/stdout to pipes
                os.dup2(pipe_child_read, sys.stdin.fileno())
                os.dup2(pipe_child_write, sys.stdout.fileno())
                os.execvp('python3', ['python3', 'robot.py', str(i), '-pos', str(row), str(col), '-f', self.room_file])
            else:  # Parent process
                os.close(pipe_child_read)
                os.close(pipe_child_write)
                # Store robot information
                self.robots[i] = {
                    "pid": pid,
                    "position": [row, col],
                    "pipe_read": os.fdopen(pipe_parent_read, 'r'),
                    "pipe_write": os.fdopen(pipe_parent_write, 'w')
                }
                
                # Check if initial position has a treasure
                if (row, col) in self.treasure_positions:
                    self.room_info[row][col] = 'RT'
                    self.discovered_treasures.add((row, col))
                    self.treasures_found += 1
                    print(f"Treasure found by robot {i}!")
                else:
                    self.room_info[row][col] = 'R'
                    
                print(f"Robot {i} PID: {pid} Position: ({row}, {col})")

    def print_room(self):
        print("Our information about the room so far:")
        for row in self.room_info:
            print(' '.join(row))

    def send_command(self, robot_id, command):
        """
        Sends a command to a robot and waits for its response.
        Handles communication errors and timeouts.
        """
        try:
            # Check if robot is still alive
            try:
                os.kill(self.robots[robot_id]["pid"], 0)
            except ProcessLookupError:
                print(f"Robot {robot_id} is no longer running", file=sys.stderr)
                return "Error"

            # Write command
            self.robots[robot_id]["pipe_write"].write(f"{command}\n")
            self.robots[robot_id]["pipe_write"].flush()
            
            # Read response with timeout
            rlist, _, _ = select.select([self.robots[robot_id]["pipe_read"]], [], [], 2.0)
            if not rlist:
                print(f"Timeout waiting for response from robot {robot_id}", file=sys.stderr)
                return "Error"
            
            response = self.robots[robot_id]["pipe_read"].readline().strip()
            
            if "Treasure" in response:
                self.treasures_found += 1
                row, col = self.robots[robot_id]["position"]
                self.room_info[row][col] = 'T'
                print(f"Treasure found by robot {robot_id}!")
                if self.treasures_found == self.n_treasures:
                    self.exit_program()
            
            return response

        except (IOError, BrokenPipeError) as e:
            print(f"Communication error with robot {robot_id}: {e}", file=sys.stderr)
            try:
                # Try to terminate the robot if it's still running
                os.kill(self.robots[robot_id]["pid"], signal.SIGTERM)
            except ProcessLookupError:
                pass
            return "Error"

    def initialize_room_info(self):
        rows, cols = self.dimensions
        self.room_info = [['?' for _ in range(cols)] for _ in range(rows)]
        self.treasure_positions = set()  # Store treasure positions
        
        # Check obstacles and treasures during initialization
        for i in range(rows):
            for j in range(cols):
                if self.sensor.with_obstacle(i, j):
                    self.room_info[i][j] = 'X'
                elif self.sensor.with_treasure(i, j):
                    self.treasure_positions.add((i, j))

    def move_robot(self, robot_id, direction):
        """
        Handles robot movement, including collision detection and treasure discovery.
        Updates room state after movement.
        """
        # Calculate new position
        old_row, old_col = self.robots[robot_id]["position"]
        new_row, new_col = old_row, old_col
        
        if direction == "up":
            new_row -= 1
        elif direction == "down":
            new_row += 1
        elif direction == "left":
            new_col -= 1
        elif direction == "right":
            new_col += 1

        # Check for collisions with other robots
        for other_id, other_robot in self.robots.items():
            if other_id != robot_id and other_robot["position"] == [new_row, new_col]:
                print(f"Collision between robot {robot_id} and {other_id}")
                return False

        # Send move command and handle response
        response = self.send_command(robot_id, f"mv {direction}")
        print(f"Robot {robot_id} status: {response}")
        
        if "OK" in response:
            # Handle old position
            old_pos_has_robot = False
            for rid, robot in self.robots.items():
                if rid != robot_id and robot["position"] == [old_row, old_col]:
                    old_pos_has_robot = True
                    break
            
            if not old_pos_has_robot:
                # If old position had a treasure, mark as T, otherwise -
                if (old_row, old_col) in self.treasure_positions:
                    self.room_info[old_row][old_col] = 'T'
                else:
                    self.room_info[old_row][old_col] = '-'
            
            # Update new position - if it has a treasure, mark as RT, otherwise R
            if (new_row, new_col) in self.treasure_positions:
                self.room_info[new_row][new_col] = 'RT'
                if (new_row, new_col) not in self.discovered_treasures:
                    self.treasures_found += 1
                    self.discovered_treasures.add((new_row, new_col))
                    print(f"Treasure found by robot {robot_id}!")
                    if self.treasures_found == self.n_treasures:
                        print("All treasures found!")
                        self.exit_program()
            else:
                self.room_info[new_row][new_col] = 'R'
                
            self.robots[robot_id]["position"] = [new_row, new_col]
            return True

        
        if "OK" in response:
            self.room_info[old_row][old_col] = '-'
            self.room_info[new_row][new_col] = 'R'
            self.robots[robot_id]["position"] = [new_row, new_col]
            return True
        return False

    def handle_command(self, command):
        """
        Processes user commands and delegates to appropriate handler methods.
        Supports commands: mv, print, bat, pos, suspend, resume, exit
        """
        parts = command.strip().split()
        if not parts:
            return
        
        # Handle different commands
        if parts[0] == "mv": # MOvement command
            if len(parts) != 3:
                print("Invalid move command", file=sys.stderr)
                return
            
            robot_id, direction = parts[1], parts[2]
            if robot_id == "all":
                for rid in sorted(self.robots.keys()):
                    self.move_robot(rid, direction)
                # Print room after all robots have moved
                print("\nRoom state after movement:")
                self.print_room()
            else:
                try:
                    rid = int(robot_id)
                    self.move_robot(rid, direction)
                    # Print room after the robot has moved
                    print("\nRoom state after movement:")
                    self.print_room()
                except ValueError:
                    print("Invalid robot id", file=sys.stderr)

        elif parts[0] == "print": #Room display command
            self.print_room()

        elif parts[0] == "bat": #Battery command
            if len(parts) != 2:
                print("Invalid battery command", file=sys.stderr)
                return
            
            robot_id = parts[1]
            if robot_id == "all":
                for rid in self.robots:
                    response = self.send_command(rid, "bat")
                    print(f"Robot {rid} pid: {self.robots[rid]['pid']} status:{response}")
            else:
                try:
                    rid = int(robot_id)
                    response = self.send_command(rid, "bat")
                    print(f"Robot {rid} pid: {self.robots[rid]['pid']} status:{response}")
                except ValueError:
                    print("Invalid robot id", file=sys.stderr)

        elif parts[0] == "pos": # Position command
            if len(parts) != 2:
                print("Invalid position command", file=sys.stderr)
                return
            
            robot_id = parts[1]
            if robot_id == "all":
                for rid in self.robots:
                    response = self.send_command(rid, "pos")
                    print(f"Robot {rid} pid: {self.robots[rid]['pid']} status:{response}")
            else:
                try:
                    rid = int(robot_id)
                    response = self.send_command(rid, "pos")
                    print(f"Robot {rid} pid: {self.robots[rid]['pid']} status:{response}")
                except ValueError:
                    print("Invalid robot id", file=sys.stderr)

        elif parts[0] == "suspend": # Suspend robot command
            if len(parts) != 2:
                print("Invalid suspend command", file=sys.stderr)
                return
            
            robot_id = parts[1]
            if robot_id == "all":
                for rid in self.robots:
                    os.kill(self.robots[rid]["pid"], signal.SIGINT)
            else:
                try:
                    rid = int(robot_id)
                    os.kill(self.robots[rid]["pid"], signal.SIGINT)
                except ValueError:
                    print("Invalid robot id", file=sys.stderr)

        elif parts[0] == "resume": # Resume command
            if len(parts) != 2:
                print("Invalid resume command", file=sys.stderr)
                return
            
            robot_id = parts[1]
            if robot_id == "all":
                for rid in self.robots:
                    os.kill(self.robots[rid]["pid"], signal.SIGQUIT)
            else:
                try:
                    rid = int(robot_id)
                    os.kill(self.robots[rid]["pid"], signal.SIGQUIT)
                except ValueError:
                    print("Invalid robot id", file=sys.stderr)

        elif parts[0] == "exit":
            self.exit_program()

    def exit_program(self):
        """
        Handles program termination:
        - Gets final status from all robots
        - Closes pipes
        - Waits for robot processes to finish
        - Displays final room state
        """
        for rid in self.robots:
            try:
                # Get position
                pos_response = self.send_command(rid, "pos")
                # Get battery
                bat_response = self.send_command(rid, "bat")
                print(f"Robot {rid} pid: {self.robots[rid]['pid']} last message:")
                print(f"{pos_response}")
                print(f"{bat_response}")
            except:
                print(f"Failed to get final message from robot {rid}")
        
        # Close all pipes safely
        for robot in self.robots.values():
            try:
                robot["pipe_read"].close()
            except:
                pass
            try:
                robot["pipe_write"].close()
            except:
                pass
        
        # Wait for all robots to finish and get their exit status
        for rid in self.robots:
            try:
                _, status = os.waitpid(self.robots[rid]["pid"], 0)
                print(f"Robot {self.robots[rid]['pid']} finished with status {os.WEXITSTATUS(status)}")
            except:
                print(f"Could not get exit status for robot {rid}")
        
        print("\nFinal room state:")
        self.print_room()
        sys.exit(0)

    def handle_signal(self, signum, frame):
        if signum == signal.SIGINT:
            print("\nReceived SIGINT, exiting...")
            self.exit_program()
        elif signum == signal.SIGQUIT:
            print("\nReplenishing batteries")
            for rid in self.robots:
                os.kill(self.robots[rid]["pid"], signal.SIGUSR1)
        elif signum == signal.SIGTSTP:
            for rid in self.robots:
                os.kill(self.robots[rid]["pid"], signal.SIGTSTP)

def parse_arguments():
    """Parses command line arguments for room and robot configuration files"""
    args = sys.argv[1:]
    room_file = None
    robots_file = None
    
    i = 0
    while i < len(args):
        if args[i] == '-room' and i + 1 < len(args):
            room_file = args[i + 1]
            i += 2
        elif args[i] == '-robots' and i + 1 < len(args):
            robots_file = args[i + 1]
            i += 2
        else:
            print(f"Unknown argument: {args[i]}", file=sys.stderr)
            sys.exit(1)
    
    if not room_file or not robots_file:
        print("Missing required arguments", file=sys.stderr)
        sys.exit(1)
    
    return room_file, robots_file

def main():
    """
    Main program function:
    - Initializes master
    - Sets up signal handlers
    - Runs command processing loop
    """
    room_file, robots_file = parse_arguments()
    master = Master(room_file, robots_file)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, master.handle_signal)
    signal.signal(signal.SIGQUIT, master.handle_signal)
    signal.signal(signal.SIGTSTP, master.handle_signal)
    
    master.print_room()
    
    while True:
        try:
            command = input("Command: ")
            master.handle_command(command)
        except EOFError:
            break

if __name__ == "__main__":
    main()
