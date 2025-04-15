# Implementation of a class named Sensor that receives the following arguments:
# filename - the name of the file that contains the room information.
# The room is a grid of squares.
# Within the file, the first line contains the dimensions of the room.
# The second line contains the number of obstacles and their positions.
# The third line contains the number of treasures and their positions
# Example:
# 3 4
# 2 (1,1) (2,2) 
# 1 (0, 1)
# The room has 3 rows and 4 columns
# There are 2 obstacles in positions (1,1) and (2,2)
# There is 1 treasure in position (0,1)
#
# The class Sensor exposes the following methods:
# print_room() - prints the room
# with_obstacle(row, column) - returns True if the cell contains an obstacle, False otherwise
# with_treasure(row, column) - returns True if the cell contains a treasure, False otherwise
# n_treasures() - returns the number of treasures in the room
# dimensions() - returns the dimensions of the room
import sensor

class Sensor:
    def __init__(self, filename):
        self._filename = filename
        self._room = []
        self._rows = -1
        self._columns = -1
        self._num_obstacles = -1
        self._obstacles = []
        self._num_treasures = -1
        self._treasures = []
        self._read_room()

    # This method is internal of the class and called by the constructor
    # It should not be called within your code.
    def _read_room(self):
        with open(self._filename, 'r') as file:
            lines = file.readlines()
            dimensions = lines[0].split()
            self._rows = int(dimensions[0])
            self._columns = int(dimensions[1])
            self._room = []
            for i in range(self._rows):
                self._room.append([])
                for j in range(self._columns):
                    self._room[i].append('-')
                    obstacles = lines[1].split()
                    self._num_obstacles = int(obstacles[0])
            for i in range(1, len(obstacles)):
                obstacle = obstacles[i].replace('(', '').replace(')', '').split(',')
                row = int(obstacle[0])
                column = int(obstacle[1])
                self._room[row][column] = 'X'
                self._obstacles.append((row, column))
                treasures = lines[2].split()
                self._num_treasures = int(treasures[0])
            for i in range(1, len(treasures)):
                treasure = treasures[i].replace('(', '').replace(')', '').split(',')
                row = int(treasure[0])
                column = int(treasure[1])
                self._room[row][column] = 'T'
                self._treasures.append((row, column))

    def print_room(self):
        for row in self._room:
            for cell in row:
                print(cell, end=' ')
            print()
                
    # Only to be used by the master
    def n_treasures(self):
        return self._num_treasures
    # Only to be used by the master
    def dimensions(self):
        return (self._rows, self._columns)
    
    # Can be used by the master at its initialization.
    # Can be used by a robot at any given time
    def with_obstacle(self, row, column):
        if row < 0 or row >= self._rows:
            return True
        if column < 0 or column >= self._columns:
            return True
        if self._room[row][column] == 'X':
            return True
        return False

    # Can be used by the master at its initialization.
    # Can be used by a robot at any given time
    
    def with_treasure(self, row, column):
        if row < 0 or row >= self._rows:
            return False
        if column < 0 or column >= self._columns:
            return False
        if self._room[row][column] == 'T':
            return True
        return False

