# Processes_in_linux
Python code creating processes and subprocesses
# Robot Treasure Hunt Simulation

A multi-process simulation of robots navigating a room to find treasures while managing battery life and avoiding obstacles.

## Overview

This project implements a treasure-hunting simulation where multiple robot processes navigate through a room to discover treasures. The system uses Python's process management capabilities to create a multi-process application where each robot operates independently but is coordinated by a master process.

## Components

### `robot.py`

Implements an autonomous robot that can:
- Move in four directions (up, down, left, right)
- Detect treasures at its current position
- Manage and monitor battery levels
- Respond to various signals to suspend, resume, or replenish battery

The robot's battery decreases by:
- 5 units for each movement
- 1 unit per second (implemented with SIGALRM)

Each robot runs as a separate process and communicates with the master through pipes.

### `master.py`

Coordinates multiple robots within the room:
- Initializes robot processes with specific starting positions
- Sends commands to robots and interprets their responses
- Maintains a map of explored areas, obstacles, and discovered treasures
- Handles user commands to control robots (move, check battery, etc.)
- Manages inter-robot collision detection
- Tracks progress toward finding all treasures

### `sensor.py`

Provides an interface to the room configuration:
- Loads room layout from a configuration file
- Tracks dimensions, obstacles, and treasure positions
- Provides methods to check for obstacles or treasures at specific positions

## File Formats

### Room Configuration (`room.txt`)
```
6 10
3 (0,0) (1,2) (3,4)
2 (1,1) (2,3)
```
- First line: `<rows> <columns>` (dimensions of the room)
- Second line: `<number_of_obstacles> (<row>,<col>) (<row>,<col>) ...` (obstacle positions)
- Third line: `<number_of_treasures> (<row>,<col>) (<row>,<col>) ...` (treasure positions)

### Robot Configuration (`robots.txt`)
```
(2,3)
(1,4)
(1,5)
```
- Each line represents the starting position of a robot: `(<row>,<col>)`

## Command Line Usage

### Running the Master Process
```
python master.py -room room.txt -robots robots.txt
```

### Running a Robot Independently (normally done by the master)
```
python robot.py <robot_id> -pos <row> <col> -b <battery_level> -f <room_file>
```

## Commands

Once the simulation is running, you can control it using these commands:

### Movement
- `mv <robot_id> <direction>`: Move a robot (directions: up, down, left, right)
- `mv all <direction>`: Move all robots in the specified direction

### Status
- `print`: Display the current state of the room
- `bat <robot_id>`: Check battery level of a specific robot
- `bat all`: Check battery levels of all robots
- `pos <robot_id>`: Check position of a specific robot
- `pos all`: Check positions of all robots

### Control
- `suspend <robot_id>`: Suspend operation of a specific robot
- `suspend all`: Suspend all robots
- `resume <robot_id>`: Resume operation of a specific robot
- `resume all`: Resume all robots
- `exit`: Terminate the simulation

## Signal Handling

### Master Process
- `SIGINT` (Ctrl+C): Exit the program gracefully
- `SIGQUIT` (Ctrl+\): Replenish battery for all robots
- `SIGTSTP` (Ctrl+Z): Print status of all robots

### Robot Process
- `SIGINT`: Suspend robot
- `SIGQUIT`: Resume robot
- `SIGTSTP`: Print robot status
- `SIGUSR1`: Replenish battery to 100
- `SIGALRM`: Decrease battery by 1 (triggered every second)

## Room Representation

The master maintains a 2D grid representation of the room:
- `?`: Unexplored area
- `X`: Obstacle
- `R`: Robot
- `T`: Discovered treasure
- `RT`: Robot on a treasure
- `-`: Explored empty space

## Implementation Details

- The system uses fork() to create separate processes for each robot
- Inter-process communication is achieved through pipes
- Signal handling is used for various control operations
- The master uses select() for non-blocking I/O when communicating with robots

## Example Session

```
$ python master.py -room room.txt -robots robots.txt
Robot 1 PID: 12345 Position: (2, 3)
Robot 2 PID: 12346 Position: (1, 4)
Robot 3 PID: 12347 Position: (1, 5)

Our information about the room so far:
? ? ? ? ? ? ? ? ? ?
? ? X ? R R ? ? ? ?
? ? ? R ? ? ? ? ? ?
? ? ? ? X ? ? ? ? ?
? ? ? ? ? ? ? ? ? ?
? ? ? ? ? ? ? ? ? ?

Command: mv 1 up
Robot 1 status: OK

Room state after movement:
? ? ? ? ? ? ? ? ? ?
? ? X R R R ? ? ? ?
? ? ? - ? ? ? ? ? ?
? ? ? ? X ? ? ? ? ?
? ? ? ? ? ? ? ? ? ?
? ? ? ? ? ? ? ? ? ?

Command: bat all
Robot 1 pid: 12345 status:Battery: 95
Robot 2 pid: 12346 status:Battery: 100
Robot 3 pid: 12347 status:Battery: 100

Command: mv all left
Robot 1 status: OK
Robot 2 status: OK
Robot 3 status: OK

Room state after movement:
? ? ? ? ? ? ? ? ? ?
? ? R R R ? ? ? ? ?
? ? ? - ? ? ? ? ? ?
? ? ? ? X ? ? ? ? ?
? ? ? ? ? ? ? ? ? ?
? ? ? ? ? ? ? ? ? ?

Command: exit
Robot 1 pid: 12345 last message:
Position: 1 2
Battery: 89
Robot 2 pid: 12346 last message:
Position: 1 3
Battery: 94
Robot 3 pid: 12347 last message:
Position: 1 4
Battery: 94
Robot 12345 finished with status A
Robot 12346 finished with status 0
Robot 12347 finished with status 0

Final room state:
? ? ? ? ? ? ? ? ? ?
? ? R R R ? ? ? ? ?
? ? ? - ? ? ? ? ? ?
? ? ? ? X ? ? ? ? ?
? ? ? ? ? ? ? ? ? ?
? ? ? ? ? ? ? ? ? ?
```

## Requirements

- Python 3.x
- Unix-like operating system (Linux, macOS) for fork() and signal handling
