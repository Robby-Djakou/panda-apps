# Demonstration video from the application
[![Tic-Tac-Toe, Tower of Hanoi and checkers games with panda robot](https://img.youtube.com/vi/T34peibtNsY/maxresdefault.jpg)](https://youtu.be/T34peibtNsY)

# Master's thesis Robby Courbis Tatchou Djakou at the Furtwangen University of Applied Sciences

## Franka Emika Games
**Franka Emika Game** is a desktop application developed in the Python programming language with the aim of offering three games, namely Tic-Tac-Toe, Towers of Hanoi and Checkers. With this application, the user has the opportunity to play one of these 3 games against a robotic arm, namely the **Panda Robot**. With the help of a 2D camera, the panda robot can monitor the game environment and execute the game moves.

For a smooth execution of this application, both the software and hardware components need to be prepared.
#
## Hardware component
+ A 2D camera or webcam (the **Logitech c270** is recommended).
+ An extension cable
+ The Panda robot
+ A camera table mount

### Hardware component design

+ The camera must be attached to the camera table mount.
+ The camera must be fixed with the camera table bracket parallel to the table.
+ The camera must be mounted in the direction of the x-coordinate of the Panda Robot.
+ Before calibration, the camera must be mounted so that point A is at the top left of the camera image, as shown in the figure below. **(very important for performing the checkers game)**.
+ The camera must be connected to the extension cable.
+ The other part (USB) of the extension cable must be connected to the operating computer of the Panda.

In the following illustration you can see an example of a setup.


![panda_robot](image_readme/pandaroboterkoordinaten.png?raw=true "Panda Robot")

Now that the hardware components are assembled, we can take care of the software part.
#
## Software component
In this part, we considered the installation of the Franka Emika Games application on the Ubuntu operating system, since Ubuntu was installed on the Panda Robot's operating computer:

The following steps must be performed:
+ Download Microsoft Visual Studio Code with the filename extension ***.deb***, available at https://code.visualstudio.com/. During the download you will be asked in which folder and under which name the file should be saved. (for better understanding during the tutorial, the file with the following name ***vcode.deb*** is used).
+ A terminal must be open and you must navigate to the directory where the file is located. The command `cd` can be used for this. Microsoft Visual Studio Code is installed in the directory from the downloaded file with the command:
    ```
    sudo apt install ./vcode.deb
    ```
+ After Microsoft Visual Studio Code has been installed, Python must be installed. This is done with the command:
    ```
    sudo apt install python3
    ```
+ Python for Microsoft Visual Studio Code must also be installed. After opening Microsoft Visual Studio Code, you can enter **Python** under the menu item ***Extension*** and search. The version of Python with a ***blue tick*** and the verification message ***This publisher has verified ownership of microsoft.com*** can be selected and installed.

+ After the installation is complete, restart Microsoft Visual Studio Code.
+ Open a terminal and install ***python3.8-venv***. The aim is to create a Python virtual environment so that the required packages are installed there. To install this package, run the following command:
    ```
    sudo apt install python3.8-venv
    ```
+ The virtual environment allows packages or modules to be installed in an encapsulated environment that is independent of the base Python environment. This means that any changes made in the virtual environment will not affect the base environment. The creation of a virtual environment can be done with the following commands:

    + Creation of a folder in which the virtual environment is created:
        ```
        mkdir virtEnvironment
        ```
    + Creating the virtual environment:
        ```
        python3 -m venv virtEnvironment/
        ```
    + Activate the virtual environment:
        ```
        source virtEnvironment/bin/activate
        ```
    + To deactivate, give the command:
        ```
        deactivate
        ```
+ Virtual Studio Code allows the use of virtual environments, for which the following steps must be taken:
    + Start the search for option in Visual Studio Code with the keyboard shortcut: **STRG + Shift + P**
    + Type ***>python: select interpreter*** in the search box and press **ENTER**.
    + The option ***+ Enter interpreter path*** and click ***Search...***.
    + A window will appear and the goal is to select the file `python` under `virtEnvironment/bin/`.

+ After creating the virtual environment, the necessary packages to run the application must be installed. To do this, start a terminal and activate the previously created virtual environment via the terminal, then navigate to the application's folder (**Franka_Emika_Apps_Final_Version**) and execute the following commands:
    ```
    sudo apt-get update
    sudo apt-get install python3-tk
    sudo apt-get install python3-pip
    sudo apt-get install espeak 
    pip install pygame
    pip install -r ./yolov5/requirements.txt
    pip install tensorflow
    pip install frankx
    ```
+ After Microsoft Visual Code has been configured, the
folder of the application must be opened in Visual Studio Code. To do this, click ***File > Open Folder...***, a window will appear and the goal is to navigate to the application's folder. Once the folder is open, click ***Select Folder*** at the bottom.
+ Select and run the file `appFrankaEmikaGames.py` in Microsoft Visual Studio Code. (**Important**: First check the camera index in `config.py` to make sure it is correct).
+ After starting the application, first select the 'Calibrate Camera' button on the home page of the application and perform the calibration before starting a game. 
+ The 4 points on the table, as shown in the picture above, must be selected as follows: **A, B, C, D**
+ Other 4 points can also be selected, but for this, point A must be known to the Panda robot. You can set the new value of A in the `config.py`.
+ Now you can start a game and enjoy.
+ **Note:** For the game Tic-Tac-Toe, the game field must look like this:
![tic-tac-toe-gamefield](image_readme/Tic-Tac-Toe.jpeg?raw=true "Tic-Tac-Toe Gamefield")




