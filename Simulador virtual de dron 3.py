import sys
import random
import time
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QGridLayout, QLabel, QPushButton, QTextEdit, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QTextCursor

# ==============================================================================
# LÓGICA ORIGINAL DE LA SIMULACIÓN (Mantenida intacta)
# ==============================================================================

MAX_OBJETIVOS = 10
FILAS = 10
COLS = 10
PESO_MAX_EMPAQUE = 3
BASE_X = 2
BASE_Y = 2

class Celda:
    def __init__(self):
        self.tipo = ' '       
        self.visitado = 0     
        self.prioridad = 0    
        self.nombre = ""      

class Dron:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.bateria = 0                
        self.cargaKg = 0                
        self.enRegreso = 0              
        self.motivoRegreso = 0          
        self.bloqueosConsecutivos = 0   
        self.objetivosAtendidos = 0     
        self.contadorPrecaucion = 0     

def inicializarGrid(grid):
    for i in range(FILAS):
        for j in range(COLS):
            grid[i][j].tipo = ' '
            grid[i][j].visitado = 0
            grid[i][j].prioridad = 0
            grid[i][j].nombre = ""
    grid[BASE_X][BASE_Y].tipo = 'B'
    grid[5][7].tipo = 'O'
    grid[5][7].prioridad = 1
    grid[5][7].nombre = "Hospital La Guaira"
    grid[7][3].tipo = 'O'
    grid[7][3].prioridad = 2
    grid[7][3].nombre = "Edificio colapsado"
    grid[4][5].tipo = 'X'
    grid[4][6].tipo = 'X'
    grid[6][4].tipo = 'X'
    grid[5][4].tipo = 'X'
    grid[4][5].tipo = 'X'
    grid[4][7].tipo = 'X'
    grid[8][6].tipo = '!'
    grid[5][5].tipo = '!'
    grid[2][8].tipo = '!'

def simularClima(viento, lluvia, alerta):
    viento += random.randint(0, 20) - 10   
    lluvia += random.randint(0, 10) - 5    
    if random.randint(0, 99) < 2:
        viento += 50 + random.randint(0, 10)   
        lluvia += 40 + random.randint(0, 10)   
    if viento < 0:
        viento = 0
    if lluvia < 0:
        lluvia = 0
    if viento > 60 or lluvia > 50:
        alerta = 2 
    elif (30 <= viento <= 60) or (20 <= lluvia <= 50):
        alerta = 1 
    else:
        alerta = 0 
    return viento, lluvia, alerta

def costoPorCelda(d, viento, lluvia, alerta):
    costo = 2 + (d.cargaKg // 2)
    costo += viento // 20   
    costo += lluvia // 15   
    if alerta == 1:
        costo += 3
    elif alerta == 2:
        costo += 6
    if costo < 1:
        costo = 1
    return costo

def cargarEmpaque(d, kg):
    if kg <= 0:
        print("Error: el peso del empaque debe ser mayor que cero.")
        return 0
    elif kg > PESO_MAX_EMPAQUE:
        print(f"Error: el peso del empaque ({kg} kg) excede el maximo permitido ({PESO_MAX_EMPAQUE} kg).")
        return 0
    d.cargaKg = kg
    return 1

def evaluarReplicaCortanteBasal(turno, enZonaRiesgo):
    a0 = 0.35       
    s = 1.25        
    r = 3.5         
    i_factor = 1.0  
    coeSismico = (a0 * s) / (r * i_factor)
    peso_base_estructura = 1500.00 
    w = peso_base_estructura
    cortante_basal_v = coeSismico * w
    factor_aleatorio = random.random() * 0.15
    indice_peligro = cortante_basal_v + factor_aleatorio
    probabilidad = 0.002 + 0.002 * float(turno)
    if enZonaRiesgo:
        probabilidad += 0.02
    probabilidad += indice_peligro / 50000.0 
    if probabilidad > 0.08:
        probabilidad = 0.08
    rnd = random.random()
    if rnd < probabilidad:
        return 1
    else:
        return 0

def siguientePaso(grid, psactualx, psactualy, destinox, destinoy):
    distanciaPasos = []
    for i in range(FILAS):
        fila = []
        for j in range(COLS):
            fila.append(-1)
        distanciaPasos.append(fila)
    colax = [0] * (FILAS * COLS)
    colay = [0] * (FILAS * COLS)
    cabeza = 0
    cola = 0
    explorax = [-1, 1, 0, 0]
    explorary = [0, 0, -1, 1]

    if psactualx == destinox and psactualy == destinoy:
        return 0, -1, -1

    distanciaPasos[destinox][destinoy] = 0
    colax[cola] = destinox
    colay[cola] = destinoy
    cola += 1

    while cabeza < cola:
        cx = colax[cabeza]
        cy = colay[cabeza]
        cabeza += 1
        for k in range(4):
            ax = cx + explorax[k]
            ay = cy + explorary[k]
            if ax < 0 or ax >= FILAS or ay < 0 or ay >= COLS:
                continue
            if grid[ax][ay].tipo == 'X':
                continue
            if distanciaPasos[ax][ay] != -1:
                continue
            distanciaPasos[ax][ay] = distanciaPasos[cx][cy] + 1
            colax[cola] = ax
            colay[cola] = ay
            cola += 1

    if distanciaPasos[psactualx][psactualy] == -1:
        return 0, -1, -1 

    mejorX = -1
    mejorY = -1
    mejor = 9999
    
    for k in range(4):
        ax = psactualx + explorax[k]
        ay = psactualy + explorary[k]
        if ax < 0 or ax >= FILAS or ay < 0 or ay >= COLS:
            continue
        if grid[ax][ay].tipo == 'X':
            continue
        if distanciaPasos[ax][ay] != -1 and distanciaPasos[ax][ay] < mejor:
            mejor = distanciaPasos[ax][ay]
            mejorX = ax
            mejorY = ay

    if mejorX == -1:
        return 0, -1, -1
    return 1, mejorX, mejorY

def obtenerObjetivos(grid, maximo):
    objetivos = []
    for i in range(FILAS):
        for j in range(COLS):
            if grid[i][j].tipo == 'O' and len(objetivos) < maximo:
                objetivos.append(grid[i][j])
    n = len(objetivos)
    for i in range(1, n):
        actual = objetivos[i]
        j = i - 1
        while j >= 0 and objetivos[j].prioridad > actual.prioridad:
            objetivos[j + 1] = objetivos[j]
            j -= 1
        objetivos[j + 1] = actual
    return objetivos

def filaDeCelda(grid, celda):
    for i in range(FILAS):
        for j in range(COLS):
            if grid[i][j] is celda:
                return i
    return -1

def columnaDeCelda(grid, celda):
    for i in range(FILAS):
        for j in range(COLS):
            if grid[i][j] is celda:
                return j
    return -1

def distanciaRuta(grid, desdeX, desdeY, hastaX, hastaY):
    distancia = []
    for i in range(FILAS):
        fila = []
        for j in range(COLS):
            fila.append(-1)
        distancia.append(fila)
    colax = [0] * (FILAS * COLS)
    colay = [0] * (FILAS * COLS)
    cabeza = 0
    cola = 0
    explorax = [-1, 1, 0, 0]
    explorary = [0, 0, -1, 1]

    if desdeX == hastaX and desdeY == hastaY:
        return 0

    distancia[desdeX][desdeY] = 0
    colax[cola] = desdeX
    colay[cola] = desdeY
    cola += 1

    while cabeza < cola:
        cx = colax[cabeza]
        cy = colay[cabeza]
        cabeza += 1
        for k in range(4):
            ax = cx + explorax[k]
            ay = cy + explorary[k]
            if ax < 0 or ax >= FILAS or ay < 0 or ay >= COLS:
                continue
            if grid[ax][ay].tipo == 'X':
                continue
            if distancia[ax][ay] != -1:
                continue
            distancia[ax][ay] = distancia[cx][cy] + 1
            if ax == hastaX and ay == hastaY:
                return distancia[ax][ay]
            colax[cola] = ax
            colay[cola] = ay
            cola += 1
    return -1

def moverDron(grid, objetivos, numObjetivos, d, viento, lluvia, alerta, turno, finJuego, causaAborto):
    destinoX = d.x
    destinoY = d.y
    if d.enRegreso == 1:
        destinoX = BASE_X
        destinoY = BASE_Y
    else:
        mejorPrioridad = 999
        encontrado = 0
        targetX = -1
        targetY = -1
        for k in range(numObjetivos):
            if objetivos[k].visitado == 0 and objetivos[k].prioridad < mejorPrioridad:
                mejorPrioridad = objetivos[k].prioridad
                targetX = filaDeCelda(grid, objetivos[k])
                targetY = columnaDeCelda(grid, objetivos[k])
                encontrado = 1
        if encontrado:
            distIda = distanciaRuta(grid, d.x, d.y, targetX, targetY)
            distVuelta = distanciaRuta(grid, targetX, targetY, BASE_X, BASE_Y)
            costoIda = 2 + (d.cargaKg // 2) + viento // 20 + lluvia // 15
            costoVuelta = 2 + viento // 20 + lluvia // 15
            if distIda < 0:
                distIda = FILAS * COLS
            if distVuelta < 0:
                distVuelta = FILAS * COLS
            bateriaRequerida = distIda * costoIda + distVuelta * costoVuelta + 5
            if d.bateria < bateriaRequerida:
                distBase = distanciaRuta(grid, d.x, d.y, BASE_X, BASE_Y)
                costo = costoPorCelda(d, viento, lluvia, alerta)
                if distBase < 0:
                    distBase = FILAS * COLS
                bateriaRegreso = distBase * costo
                if d.bateria < bateriaRegreso:
                    print("Bateria insuficiente para regresar. Aterrizaje de emergencia.")
                    finJuego = 2
                    causaAborto = 2
                    d.enRegreso = 2
                    return finJuego, causaAborto
                print("Bateria insuficiente para completar el objetivo y regresar. Regresando a base.")
                d.enRegreso = 1
                d.motivoRegreso = 5
                causaAborto = 2
                destinoX = BASE_X
                destinoY = BASE_Y
            else:
                destinoX = targetX
                destinoY = targetY
        else:
            d.enRegreso = 1
            d.motivoRegreso = 1
            destinoX = BASE_X
            destinoY = BASE_Y

    avanzarEsteTurno = 1
    if alerta == 1:
        d.contadorPrecaucion += 1
        if (d.contadorPrecaucion % 2) == 0:
            avanzarEsteTurno = 0
    else:
        d.contadorPrecaucion = 0
    seMovio = 0
    if avanzarEsteTurno:
        sx = d.x
        sy = d.y
        enDestino = (sx == destinoX and sy == destinoY)
        if not enDestino:
            prefX = sx
            prefY = sy
            if sx != destinoX:
                prefX = sx + (1 if destinoX > sx else -1)
            elif sy != destinoY:
                prefY = sy + (1 if destinoY > sy else -1)
            prefBloqueada = (prefX < 0 or prefX >= FILAS or prefY < 0 or prefY >= COLS or grid[prefX][prefY].tipo == 'X')
            success, nx, ny = siguientePaso(grid, sx, sy, destinoX, destinoY)
            if success:
                if prefBloqueada:
                    print("Obstaculo detectado. Cambio de direccion.")
                d.x = nx
                d.y = ny
                d.bloqueosConsecutivos = 0
                seMovio = 1
            else:
                d.bloqueosConsecutivos += 1
                print(f"Dron bloqueado. (intento {d.bloqueosConsecutivos}/3)")
                if d.bloqueosConsecutivos >= 3:
                    d.bloqueosConsecutivos = 0
                    if d.x == BASE_X and d.y == BASE_Y:
                        print("Dron bloqueado en base. Mision finalizada.")
                        finJuego = 1
                        causaAborto = 4
                    else:
                        success_base, bx, by = siguientePaso(grid, d.x, d.y, BASE_X, BASE_Y)
                        if success_base:
                            print("Dron bloqueado tras 3 intentos. Regresando a base.")
                            d.enRegreso = 1
                            d.motivoRegreso = 4
                            causaAborto = 4
                        else:
                            print("Dron bloqueado y sin ruta a base. Aterrizaje de emergencia.")
                            finJuego = 2
                            causaAborto = 4
                            d.enRegreso = 2
                    return finJuego, causaAborto
        else:
            d.bloqueosConsecutivos = 0
    else:
        print("Precaucion climatica. Avance reducido.")

    consumo = costoPorCelda(d, viento, lluvia, alerta)
    d.bateria -= consumo
    if d.bateria < 0:
        d.bateria = 0
    if seMovio:
        print(f"Dron avanza. Bat: {d.bateria}%")

    if finJuego == 0 and not (d.x == BASE_X and d.y == BASE_Y):
        enZonaRiesgo = (grid[d.x][d.y].tipo == '!')
        enColapso = (grid[d.x][d.y].tipo == 'O' and grid[d.x][d.y].visitado == 0)
        if enZonaRiesgo:
            print("Dron en zona de riesgo. Evaluando replica...")
        if evaluarReplicaCortanteBasal(turno, enZonaRiesgo):
            if enColapso:
                print("REPLICA! Aterrizaje de emergencia. Mision abortada.")
                finJuego = 2
                causaAborto = 3
                d.enRegreso = 2
                return finJuego, causaAborto
            else:
                distBase = distanciaRuta(grid, d.x, d.y, BASE_X, BASE_Y)
                costoBase = costoPorCelda(d, viento, lluvia, alerta)
                if distBase < 0:
                    distBase = FILAS * COLS
                if d.bateria >= distBase * costoBase:
                    print("REPLICA! Regresando a base por seguridad.")
                    d.enRegreso = 1
                    d.motivoRegreso = 2
                    causaAborto = 3
                else:
                    print("REPLICA! Sin bateria para regresar. Aterrizaje de emergencia. Mision abortada.")
                    finJuego = 2
                    causaAborto = 3
                    d.enRegreso = 2
                    return finJuego, causaAborto

    if finJuego == 0 and d.enRegreso == 0 and grid[d.x][d.y].tipo == 'O' and grid[d.x][d.y].visitado == 0:
        grid[d.x][d.y].visitado = 1
        d.objetivosAtendidos += 1
        d.cargaKg = 0 
        print(f"Objetivo alcanzado: {grid[d.x][d.y].nombre}. Carga entregada.")
        quedan = 0
        for k in range(numObjetivos):
            if objetivos[k].visitado == 0:
                quedan = 1
        if not quedan:
            print("Todos los objetivos atendidos. Mision cumplida.")
        distBase = distanciaRuta(grid, d.x, d.y, BASE_X, BASE_Y)
        costoBase = costoPorCelda(d, viento, lluvia, alerta)
        if distBase < 0:
            distBase = FILAS * COLS
        if d.bateria < distBase * costoBase:
            print("Bateria insuficiente para regresar. Aterrizaje de emergencia.")
            finJuego = 2
            causaAborto = 2
            d.enRegreso = 2
            return finJuego, causaAborto
        d.enRegreso = 1
        d.motivoRegreso = 1
        print(f"Regresando a base. Bat: {d.bateria}%")
        
    return finJuego, causaAborto

# ==============================================================================
# CLASE PARA REDIRIGIR LA CONSOLA AL PANEL DE TEXTO (Para no borrar tus prints)
# ==============================================================================
class EmittingStream(QObject):
    textWritten = pyqtSignal(str)
    def write(self, text):
        self.textWritten.emit(str(text))
    def flush(self): 
        pass

# ==============================================================================
# INTERFAZ GRÁFICA PYQT5 (Modo Oscuro con Neón)
# ==============================================================================
class DronGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simulación Dron - Modo Oscuro Neón")
        self.resize(1000, 650)
        
        # Redirigir consola a la GUI
        sys.stdout = EmittingStream(textWritten=self.normalOutputWritten)
        
        self.init_variables()
        self.init_ui()
        self.actualizar_vista_grid()
        self.ejecutar_inicio_mision()
        
    def init_variables(self):
        random.seed(int(time.time()))
        self.grid = []
        for i in range(FILAS):
            fila = []
            for j in range(COLS):
                fila.append(Celda())
            self.grid.append(fila)
            
        self.wing = Dron()
        self.viento = 15
        self.lluvia = 5
        self.alerta = 0

        if random.randint(0, 99) < 10:
            self.viento = 51 + random.randint(0, 19)
            self.lluvia = 41 + random.randint(0, 14)
            
        if self.viento > 60 or self.lluvia > 50:
            self.alerta = 2
        elif (30 <= self.viento <= 60) or (20 <= self.lluvia <= 50):
            self.alerta = 1
        else:
            self.alerta = 0
            
        self.turno = 0
        self.finJuego = 0
        self.causaAborto = 0

        self.wing.x = BASE_X
        self.wing.y = BASE_Y
        self.wing.bateria = 100
        self.wing.cargaKg = 0
        
        cargarEmpaque(self.wing, PESO_MAX_EMPAQUE)
        inicializarGrid(self.grid)
        self.objetivos = obtenerObjetivos(self.grid, MAX_OBJETIVOS)
        self.numObjetivos = len(self.objetivos)
        
    def init_ui(self):
        # Estilos Modo Oscuro / Neón
        self.setStyleSheet("""
            QWidget { background-color: #121212; color: #FFFFFF; font-family: 'Consolas', monospace; }
            QPushButton { 
                background-color: #1E1E1E; border: 2px solid #00FFFF; border-radius: 8px; 
                padding: 10px; color: #00FFFF; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background-color: #00FFFF; color: #000000; }
            QPushButton:disabled { border: 2px solid #555555; color: #555555; background-color: #121212; }
            QTextEdit { background-color: #0D0D0D; border: 1px solid #333333; color: #00FF00; }
            QLabel { font-size: 14px; }
        """)
        
        main_layout = QHBoxLayout()
        
        # Panel izquierdo (Grid Visual)
        grid_frame = QFrame()
        self.grid_layout = QGridLayout(grid_frame)
        self.grid_layout.setSpacing(2)
        
        self.labels_grid = []
        for i in range(FILAS):
            fila_labels = []
            for j in range(COLS):
                lbl = QLabel()
                lbl.setFixedSize(50, 50)
                lbl.setAlignment(Qt.AlignCenter)
                lbl.setFont(QFont("Consolas", 14, QFont.Bold))
                self.grid_layout.addWidget(lbl, i, j)
                fila_labels.append(lbl)
            self.labels_grid.append(fila_labels)
            
        main_layout.addWidget(grid_frame)
        
        # Panel derecho (Controles y Consola)
        right_panel = QVBoxLayout()
        
        self.lbl_stats = QLabel("Turno: 0 | Bat: 100% | Viento: 0 | Lluvia: 0 | Estado: En base")
        self.lbl_stats.setStyleSheet("color: #FF00FF; font-size: 16px; font-weight: bold;")
        right_panel.addWidget(self.lbl_stats)
        
        self.consola = QTextEdit()
        self.consola.setReadOnly(True)
        right_panel.addWidget(self.consola)
        
        self.btn_siguiente = QPushButton("Siguiente Turno (Paso a Paso)")
        self.btn_siguiente.clicked.connect(self.avanzar_turno)
        right_panel.addWidget(self.btn_siguiente)
        
        main_layout.addLayout(right_panel)
        main_layout.setStretch(0, 1)
        main_layout.setStretch(1, 1)
        self.setLayout(main_layout)

    def actualizar_vista_grid(self):
        # Mapeo de estilos neón para cada tipo de celda
        estilos = {
            'B': "background-color: #002244; border: 2px solid #0088FF; color: #0088FF;", # Neón Azul
            'O': "background-color: #003300; border: 2px solid #00FF00; color: #00FF00;", # Neón Verde
            'X': "background-color: #330000; border: 2px solid #FF0000; color: #FF0000;", # Neón Rojo
            '!': "background-color: #332200; border: 2px solid #FFAA00; color: #FFAA00;", # Neón Naranja
            ' ': "background-color: #1A1A1A; border: 1px solid #333333; color: #1A1A1A;"  # Vacio Oscuro
        }
        estilo_dron = "background-color: #004444; border: 3px solid #00FFFF; color: #00FFFF; font-weight: bold;" # Neón Cyan
        
        for i in range(FILAS):
            for j in range(COLS):
                tipo = self.grid[i][j].tipo
                
                if i == self.wing.x and j == self.wing.y:
                    self.labels_grid[i][j].setText("D")
                    self.labels_grid[i][j].setStyleSheet(estilo_dron)
                else:
                    self.labels_grid[i][j].setText(tipo if tipo != ' ' else "")
                    self.labels_grid[i][j].setStyleSheet(estilos[tipo])

    def ejecutar_inicio_mision(self):
        print("==========================================================")
        print(f"Mision: Entregar {PESO_MAX_EMPAQUE} kg de insumos medicos en La Guaira")
        alertaInicial = "PELIGRO" if (self.alerta == 2) else "PRECAUCION" if (self.alerta == 1) else "NORMAL"
        print(f"Clima inicial: Viento {self.viento} km/h | Lluvia {self.lluvia} mm/h | Alerta: {alertaInicial}")
        
        print("Objetivos:", end="")
        for k in range(self.numObjetivos):
            if k > 0: print(" |", end="")
            print(f" {self.objetivos[k].nombre} (prioridad {self.objetivos[k].prioridad})", end="")
        print("\n==========================================================")

        if self.viento > 50 or self.lluvia > 40:
            print("Despegue denegado por clima adverso.")
            self.btn_siguiente.setEnabled(False)
            return
            
        print("Iniciando mision...")
        self.actualizar_stats()

    # ESTE ES EL EQUIVALENTE AL BUCLE WHILE ORIGINAL, CADA CLIC DA UN PASO
    def avanzar_turno(self):
        if self.finJuego != 0:
            return
            
        self.turno += 1
        print(f"\n--- TURNO {self.turno} ---")

        self.viento, self.lluvia, self.alerta = simularClima(self.viento, self.lluvia, self.alerta)

        nombreAlerta = "NORMAL"
        if self.alerta == 1: nombreAlerta = "PRECAUCION"
        if self.alerta == 2: nombreAlerta = "PELIGRO"

        if self.alerta == 2 and self.wing.enRegreso == 0:
            print(f"ALERTA CLIMA PELIGRO! Viento {self.viento} km/h, Lluvia {self.lluvia} mm/h. Regreso forzado.")
            self.wing.enRegreso = 1
            self.wing.motivoRegreso = 3
            self.causaAborto = 1

        self.finJuego, self.causaAborto = moverDron(
            self.grid, self.objetivos, self.numObjetivos, self.wing, 
            self.viento, self.lluvia, self.alerta, self.turno, self.finJuego, self.causaAborto
        )
        
        self.actualizar_vista_grid()
        self.actualizar_stats()
        
        estado = ""
        if self.wing.enRegreso == 2: estado = "Aterrizado"
        elif self.wing.enRegreso == 1: estado = "Regresando"
        elif self.wing.x == BASE_X and self.wing.y == BASE_Y: estado = "En base"
        else: estado = "Volando"

        print(f"[Turno {self.turno}] Dron ({self.wing.x},{self.wing.y}) Bat:{self.wing.bateria}% | Viento:{self.viento} Lluvia:{self.lluvia} | {nombreAlerta} | {estado}")

        if self.finJuego == 0 and self.wing.bateria < 10 and not (self.wing.x == BASE_X and self.wing.y == BASE_Y):
            print("BATERIA CRITICA! Aterrizaje de emergencia.")
            self.finJuego = 2
            self.causaAborto = 2
            self.wing.enRegreso = 2

        if self.finJuego == 0 and self.wing.x == BASE_X and self.wing.y == BASE_Y and self.wing.enRegreso == 1:
            if self.wing.motivoRegreso == 1:
                self.wing.bateria = 100
                objetivosPendientes = 0
                targetX = -1
                targetY = -1
                mejorPrioridad = 999
                
                for a in range(self.numObjetivos):
                    if self.objetivos[a].visitado == 0 and self.objetivos[a].prioridad < mejorPrioridad:
                        mejorPrioridad = self.objetivos[a].prioridad
                        objetivosPendientes = 1
                        targetX = filaDeCelda(self.grid, self.objetivos[a])
                        targetY = columnaDeCelda(self.grid, self.objetivos[a])

                if objetivosPendientes:
                    distIda = distanciaRuta(self.grid, BASE_X, BASE_Y, targetX, targetY)
                    distVuelta = distanciaRuta(self.grid, targetX, targetY, BASE_X, BASE_Y)
                    costoIda = 2 + (PESO_MAX_EMPAQUE // 2) + self.viento // 20 + self.lluvia // 15
                    costoVuelta = 2 + self.viento // 20 + self.lluvia // 15
                    
                    if distIda < 0: distIda = FILAS * COLS
                    if distVuelta < 0: distVuelta = FILAS * COLS
                    costoEstimado = distIda * costoIda + distVuelta * costoVuelta + 5

                    if self.viento > 50 or self.lluvia > 40:
                        print("Dron en base. Despegue para el siguiente objetivo denegado por clima adverso.")
                        self.finJuego = 1
                        self.causaAborto = 1
                    elif self.wing.bateria < costoEstimado:
                        print(f"Dron en base con {self.wing.bateria}% de bateria. Bateria insuficiente para el siguiente envio.")
                        self.finJuego = 1
                        self.causaAborto = 2
                    elif not cargarEmpaque(self.wing, PESO_MAX_EMPAQUE):
                        self.finJuego = 1
                        self.causaAborto = 2
                    else:
                        print(f"Dron en base. Bateria suficiente ({self.wing.bateria}%). Tomando nuevo empaque ({PESO_MAX_EMPAQUE} kg) y saliendo...")
                        self.wing.enRegreso = 0
                        self.wing.motivoRegreso = 0
                else:
                    self.finJuego = 1
                    self.causaAborto = 0
                    print(f"Dron en base. Mision finalizada. Turnos: {self.turno}")
            else:
                self.finJuego = 1
                if self.wing.motivoRegreso == 5:
                    print(f"Dron en base con {self.wing.bateria}% de bateria. Mision finalizada por bateria insuficiente.")
                else:
                    print(f"Dron en base. Mision finalizada por seguridad. Turnos: {self.turno}")

        if self.finJuego != 0:
            self.btn_siguiente.setEnabled(False)
            self.btn_siguiente.setText("Misión Finalizada")
            self.imprimir_resumen()

    def actualizar_stats(self):
        nombreAlerta = "NORMAL"
        if self.alerta == 1: nombreAlerta = "PRECAUCION"
        if self.alerta == 2: nombreAlerta = "PELIGRO"
        
        estado = "Volando"
        if self.wing.enRegreso == 2: estado = "Aterrizado"
        elif self.wing.enRegreso == 1: estado = "Regresando"
        elif self.wing.x == BASE_X and self.wing.y == BASE_Y: estado = "En base"
            
        texto = f"Turno: {self.turno} | Bat: {self.wing.bateria}% | Viento: {self.viento} | Lluvia: {self.lluvia} | {nombreAlerta} | {estado}"
        self.lbl_stats.setText(texto)
        
    def imprimir_resumen(self):
        print("\n==========================================================")
        print("RESUMEN FINAL DE LA MISION")
        print("==========================================================")
        if self.numObjetivos > 0 and self.wing.objetivosAtendidos >= self.numObjetivos:
            estadoFinal = "MISION CUMPLIDA"
        elif self.wing.objetivosAtendidos > 0:
            estadoFinal = "MISION PARCIAL"
        else:
            estadoFinal = "MISION ABORTADA"
        print(f"Estado: {estadoFinal}")
        print(f"Objetivos atendidos: {self.wing.objetivosAtendidos}/{self.numObjetivos}")
        if self.wing.objetivosAtendidos > 0:
            print(f"Carga entregada: SI ({self.wing.objetivosAtendidos * PESO_MAX_EMPAQUE} kg)")
        else:
            print("Carga entregada: NO")
        if self.wing.objetivosAtendidos < self.numObjetivos:
            print("Causa: ", end="")
            if self.causaAborto == 1: print(f"Clima peligroso (viento {self.viento} km/h, lluvia {self.lluvia} mm/h)")
            elif self.causaAborto == 2: print("Bateria insuficiente o critica")
            elif self.causaAborto == 3: print("Actividad sismica / replica")
            elif self.causaAborto == 4: print("Dron bloqueado por escombros")
            else: print("No completada")
        print(f"Turnos totales: {self.turno}")
        print(f"Bateria restante: {self.wing.bateria}%")
        print("==========================================================")

    def normalOutputWritten(self, text):
        # Mueve el cursor al final e inserta el texto para el autoscroll
        cursor = self.consola.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.consola.setTextCursor(cursor)
        self.consola.ensureCursorVisible()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DronGUI()
    window.show()
    sys.exit(app.exec_())