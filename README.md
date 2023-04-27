# Masterarbeit Robby Courbis Tatchou Djakou MOS Hochschule Furtwangen

## Franka Emika Games
**Franka Emika Game** ist eine Desktop-Anwendung, die in Python-Programmiersprache entwickelt wurde, mit dem Ziel drei Spiele, und zwar Tic-Tac-Toe, Türme von Hanoi und Dame anzubieten. Mit dieser Anwendung hat der Benutzer die Möglichkeit eine dieser 3 Spiele gegen eines Armroboters, und zwar den **Panda-Roboter** zu spielen. Durch den Einsatz einer 2D-Kamera hat der Panda-Roboter die Möglichkeit die Spielumgebung zu überwachen und die Züge durchzuführen.

Für eine reibungslose Ausführung dieser Anwendung müssen sowohl Softwarekomponente als auch Hardwarekomponente vorbereitet werden. 
#
## Hardwarekomponente
+ Eine 2D-Kamera oder Webcam (zu empfehlen ist **Logitech c270**)
+ Ein Verlängerungskabel mit folgenden Ports (USB zu A-Buchse)
+ Der Panda-Roboter
+ Eine Kamera-Tischhalterung

### Aufbau der Hardwarekomponente

+ Die Kamera muss an der Kamera-Tischhalterung befestigt werden.
+ Die Kamera muss über die Kamera-Tischhalterung parallel zu dem Tisch festmontiert werden.
+ Die Kamera muss in der Richtung der x-Koordinate des Panda-Roboters montiert werden. 
+ Bevor die Kalibrierung durchgeführt wird, muss die Kamera montiert werden, sodass der Punkt A wie in der unteren Abbildung angezeigt wird, oben recht in der Kameraaufnahme sich befinden muss. **(sehr wichtig für die Durchführung des Damespiels)**
+ Die Kamera muss über A-Buchse mit dem Verlängerungskabel verbunden werden.
+ Der andere Teil (USB) des Verlängerungskabels muss am Bedienrechner des Pandas angebunden werden. 

Ein Beispiel eines Aufbaus können sie auf der folgenden Abbildung sehen.


![panda_roboter](image_readme/pandaroboterkoordinaten.png?raw=true "Panda Roboter")

Nachdem die Hardwarekomponente montiert sind, kümmern wir uns jetzt um den Softwareteil.
#
## Softwarekomponente
In diesem Teil wurde die Installation von der Anwendung Franka Emika Games auf Ubuntu-Betriebssystem berücksichtigt, da Ubuntu auf dem Bedienrechner des Panda-Roboters installiert wurde:

Folgende Schritte müssen durchgeführt werden:
+ das Herunterladen von Microsoft Visual Studio Code mit der Dateinamenserweiterung ***.deb*** unter https://code.visualstudio.com/. Während des Herunterladens wird gefragt, in welchem Ordner und unter welchem Namen die Datei gespeichert werden muss. (für ein besseres Verständnis während der Anleitung wird die Datei mit folgenden Namen ***vcode.deb*** verwendet).
+ Ein Terminal muss geöffnet werden und Sie müssen in Verzeichnis, in dem die Datei liegt, navigieren. Dafür kann der Befehl `cd` eingesetzt werden. Die Installation von Microsoft Visual Studio Code erfolgt in dem Verzeichnis von der heruntergeladenen Datei  unter dem Befehl:
    ```
    sudo apt install ./vcode.deb
    ```
+ Nachdem Microsoft visual studio code installiert wurde, muss Python installiert werden. Das erfolgt mit dem Befehl:
    ```
    sudo apt install python3
    ```
+ Außerdem muss Python für Microsoft Visual Studio Code installiert werden. Nachdem Microsoft Visual Studio Code geöffnet wurde, im Menüpunkt ***Erweiterung***, können Sie **Python** eingeben  und suchen. Die Version von Python mit einem ***blauen Häkchen***  und die Verifizierungsnachricht ***Dieser Herausgeber hat den Besitz von microsoft.com überprüft*** können Sie wählen und auf  ***install*** anklicken.

+ Nachdem die Installation fertig ist, starten Sie Microsoft Visual Studio Code neu. 
+ Öffnen sie einen Terminal und installieren Sie ***python3.8-venv***. Das Ziel ist eine virtuelle Umgebung von Python zu erzeugen, damit die benötigen  Paketen für die Ausführung der Anwendung dort installiert wird. Um dieses Paket zu installieren, muss folgender Befehl ausgeführt werden:
    ```
    sudo apt install python3.8-venv
    ```
+ Die virtuelle Umgebung ermöglicht die Installation von Paketen oder Modulen in einer gekapselten Umgebung, unabhängig von der Basis-Umgebung von Python. Das bedeutet alle Änderungen, die in der virtuellen Umgebung durchgeführt werden, haben keinen Einfluss auf die Basis-Umgebung. Das Erzeugen einer virtuellen Umgebung kann unter folgenden Befehlen erfolgen:

    + Erstellung eines Ordners, in dem die virtuelle Umgebung angelegt wird:
        ```
        mkdir virtUmgebung
        ```
    + Anlegen von der virtuellen Umgebung:
        ```
        python3 -m venv virtUmgebung/
        ```
    + Aktivierung von der virtuellen Umgebung:
        ```
        source virtUmgebung/bin/activate
        ```
    + Für die Deaktivierung erfolgt den Befehl:
        ```
        deactivate
        ```
+ Virtual Studio Code ermöglicht den Einsatz von der virtuellen Umgebungen, dafür muss folgende Schritte durchgeführt werden:
    + Starten der Suche von Option in Visual Studio Code mit dem Tastaturkürzel: **STRG + Umschalt-Taste + P**
    + In dem Suchfeld ***>python: interpreter auswählen*** schreiben und **ENTER** drücken.
    + Die Option ***+ Interpreterpfad eingeben*** und auf ***Suchen...*** anklicken.
    + Es wird ein Fenster angezeigt und das Ziel ist die Datei `python` unter `virtUmgebung/bin/` auszuwählen.

+ Nach der Erstellung der virtuellen Umgebung müssen die benötigten Pakete für die Ausführung der Anwendung installiert werden. Dafür muss ein Terminal gestartet werden und die früher erstellte virtuelle Umgebung muss über den Terminal aktiviert werden, dann zu Ordner der Anwendung (**Franka_Emika_Apps_Final_Version**) von der Anwendung navigieren und folgende Befehle ausführen:
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
+ Nachdem Microsoft Visual Code konfiguriert wurde, muss der
Ordner von der Anwendung in Visual Studio Code geöffnet werden. Dafür muss auf ***Datei > Ordner öffnen...*** angeklickt werden, ein Fenster wird angezeigt und das Ziel ist bis zu Ordner der Anwendung zu navigieren. Wenn der Ordner geöffnet wird, dann unten auf ***Ordner auswählen*** anklicken.
+ Die Datei `appFrankaEmikaGames.py` in Microsoft Visual Studio Code auswählen und ausführen. (**wichig**: Prüfen Sie erstmal den Kameraindex in der `config.py` ob es richtig ist)
+ Nach der Ausführung der Anwendung, erstmal der Knopf `Calibrate Camera` in der Startseite der Anwendung wählen und die Kalibrierung durchführen, bevor ein Spiel gestartet wird. 
+ Die 4 Punkten auf dem Tisch wie in der oberen Abbildung müssen wie folgt ausgewählt werden: **A, B, C, D**
+ andere 4 Punkten können auch gewählt werden, aber dafür muss der Punkt A von dem Panda-Roboter bekannt sein. Sie können den neuen Wert von A in der `config.py` einstellen.
+ Jetzt können Sie ein Spiel starten und genießen.
+ **Anmerkung:** Für das Spiel Tic-Tac-Toe muss das Spielfeld wie folgt aussehen:
![tic-tac-toe-spielfeld](image_readme/Tic-Tac-Toe.jpeg?raw=true "Tic-Tac-Toe Spielfeld")




