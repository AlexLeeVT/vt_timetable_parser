# VT Timetable Parser
The VT timetable is difficult to parse on its own. It provides no search functionalities or API to interact with on a database level.
This python application is currently built to provide software access to my specific needs, but is well commented and has flexibility and readability as a core design principle. 
Make sure python 3.13.5+ is installed, otherwise there is no guarantee the program will execute nominally.<br><br>

The output of running ```main.py``` is a csv file containing all courses located in the National Capital Region and Blacksburg campuses sorted by the course number, **not CRN**.

# How to use
1. Install required libraries
```
pip install -r requirements.txt
```
2. Run the program
```
python main.py
```
