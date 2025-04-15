import sensor
import sys
import signal
import time
import os

class Robot:
    """
    Class that represents a robot that can move in a room, detect treasures,
    and manage its battery level.
    """
    def __init__(self, id, position, battery, room_file):
        # Robot's identifier number
        self.id = id
        # Current position as [row, col]
        self.position = position
        # Battery level (decreases by 5 for movement and 1 per second)
        self.battery = battery
        # Initialize sensor with room configuration
        self.sensor = sensor.Sensor(room_file)
        # Flag to indicate if robot is suspended
        self.suspended = False
        # Print PID to stderr for debugging/tracking
        print(f"PID: {os.getpid()}", file=sys.stderr)

    def move(self, direction):
        """
        Attempts to move the robot in the specified direction.
        Returns 'OK' if successful, 'KO' if movement is not possible.
        """
        # Check if robot is suspended or has insufficient battery
        if self.suspended:
            print("KO")
            return
        if self.battery < 5:
            print("KO")
            return

        # Calculate new position and try to move
        new_position = self.calculate_new_position(direction)
        if self.valid_move(new_position):
            self.position = new_position
            self.battery_decrease(5)  # Moving costs 5 battery units
            print("OK")
        else:
            print("KO")

    def calculate_new_position(self, direction):
        """
        Calculates the new position based on the current position and direction.
        """
        row, col = self.position
        if direction == "up":
            return [row - 1, col]
        elif direction == "down":
            return [row + 1, col]
        elif direction == "left":
            return [row, col - 1]
        elif direction == "right":
            return [row, col + 1]
        else:
            return self.position

    def valid_move(self, new_position):
        """
        Checks if the new position is valid:
        - Within room boundaries
        - Not containing an obstacle
        """
        row, col = new_position
        if row < 0 or col < 0:  # Check lower bounds
            return False
        max_row, max_col = self.sensor.dimensions()
        if row >= max_row or col >= max_col:  # Check upper bounds
            return False
        return not self.sensor.with_obstacle(row, col)  # Check for obstacles

    def print_battery(self):
        """Prints current battery level"""
        if self.suspended:
            print(f"Robot {self.id} is stopped")
        else:
            print(f"Battery: {self.battery}")

    def print_position(self):
        """Prints current position"""
        if self.suspended:
            print(f"Robot {self.id} is stopped")
        else:
            row, col = self.position
            print(f"Position: {row} {col}")

    def print_id(self):
        """Prints robot ID, position, and battery level"""
        print(f"id: {self.id} P: ({self.position[0]},{self.position[1]}) Bat: {self.battery}", file=sys.stderr)
        
    def check_treasure(self):
        """
        Checks if current position contains a treasure.
        Returns True if treasure found, False otherwise.
        """
        if self.suspended:
            print(f"Robot {self.id} is stopped")
            return False
        row, col = self.position
        if self.sensor.with_treasure(row, col):
            print(f"Treasure at {row} {col}")
            return True
        else:
            print(f"Water at {row} {col}")
            return False

    def battery_decrease(self, number):
        if not self.suspended:
            self.battery = max(0, self.battery - number)

    def battery_decrease(self, number):
        """
        Decreases battery by specified amount if robot is not suspended.
        Battery cannot go below 0.
        """
        if not self.suspended:
            self.battery = max(0, self.battery - number)

# Global signal handler for the robot
def signal_handler(signum, frame):
    """
    Handles different signals:
    SIGQUIT - Resume robot
    SIGINT - Suspend robot
    SIGTSTP - Print robot status
    SIGUSR1 - Replenish battery
    SIGALRM - Decrease battery every second
    """
    global robot
    if signum == signal.SIGQUIT:
        robot.suspended = False  # Resume robot
    elif signum == signal.SIGINT:
        robot.suspended = True   # Suspend robot
    elif signum == signal.SIGTSTP:
        signal.signal(signal.SIGTSTP, signal.SIG_IGN)  # Ignore default behavior
        robot.print_id()
        signal.signal(signal.SIGTSTP, signal_handler)  # Restore our handler
    elif signum == signal.SIGUSR1:
        robot.battery = 100     # Replenish battery
    elif signum == signal.SIGALRM:
        robot.battery_decrease(1)  # Decrease battery by 1
        signal.alarm(1)           # Set next alarm

def main():
    """
    Main function that:
    1. Processes command line arguments
    2. Initializes robot
    3. Sets up signal handlers
    4. Runs main command processing loop
    """
    global robot
    
    # Check for minimum arguments
    if len(sys.argv) < 2:
        print("Missing arguments", file=sys.stderr)
        sys.exit(1)

    # Parse command line arguments
    args = sys.argv[1:]
    robot_id = int(args[0])
    position = [0, 0]  # Default position
    battery = 100      # Default battery
    room_file = None

    # Process optional arguments
    i = 1
    while i < len(args):
        if args[i] == '-pos' and i + 2 < len(args):
            position = [int(args[i + 1]), int(args[i + 2])]
            i += 3
        elif args[i] == '-b' and i + 1 < len(args):
            battery = int(args[i + 1])
            i += 2
        elif args[i] == '-f' and i + 1 < len(args):
            room_file = args[i + 1]
            i += 2
        else:
            i += 1

    # Check for required room file
    if not room_file:
        print("Missing room file", file=sys.stderr)
        sys.exit(1)

    # Initialize robot instance
    robot = Robot(robot_id, position, battery, room_file)

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)    # Ctrl+C
    signal.signal(signal.SIGQUIT, signal_handler)   # Ctrl+\
    signal.signal(signal.SIGTSTP, signal_handler)   # Ctrl+Z
    signal.signal(signal.SIGUSR1, signal_handler)   # User-defined signal 1
    signal.signal(signal.SIGALRM, signal_handler)   # Alarm signal
    signal.alarm(1)  # Start battery decrease timer

    # Main command processing loop
    while True:
        try:
            command = input().strip()
            if not command:
                continue

            # Process commands
            parts = command.split()
            if parts[0] == "mv" and len(parts) == 2:
                robot.move(parts[1])
            elif command == "bat":
                robot.print_battery()
            elif command == "pos":
                robot.print_position()
            elif command == "tr":
                robot.check_treasure()
            elif command == "exit":
                robot.print_position()
                robot.print_battery()
                sys.exit(0)
            else:
                print("Invalid command", file=sys.stderr)
            
            sys.stdout.flush()  # Ensure output is sent immediately
            
        except EOFError:
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
