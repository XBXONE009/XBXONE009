import sys
import random
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QTextEdit, QFrame, QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QTextCursor

# ==============================================================================
# LÓGICA DE LA SIMULACIÓN (Base libre de bloqueos y riesgos, control manual)
# ==============================================================================

MAX_OBJETIVOS = 10
FILAS = 10
COLS = 10
PESO_MAX_EMPAQUE = 3
BASE_X = 0
BASE_Y = 0


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

    # Base en la esquina superior izquierda (nunca tapada)
    grid[BASE_X][BASE_Y].tipo = 'B'

    # Objetivos
    grid[5][7].tipo = 'O'
    grid[5][7].prioridad = 1
    grid[5][7].nombre = "Hospital La Guaira"

    grid[7][3].tipo = 'O'
    grid[7][3].prioridad = 2
    grid[7][3].nombre = "Edificio colapsado"

    # Celdas de base y salidas directas protegidas para nunca tapar la base
    protegidas_base = {(BASE_X, BASE_Y), (BASE_X + 1, BASE_Y), (BASE_X, BASE_Y + 1)}

    # Obstáculos ('X') aleatorios directos sin tapar la base
    num_obstaculos = 14
    colocados_x = 0
    while colocados_x < num_obstaculos:
        rx = random.randint(0, FILAS - 1)
        ry = random.randint(0, COLS - 1)
        if (rx, ry) in protegidas_base:
            continue
        if grid[rx][ry].tipo == ' ':
            grid[rx][ry].tipo = 'X'
            colocados_x += 1

    # Zonas de riesgo ('!') aleatorias directas sin tapar la base
    num_riesgos = 12
    colocados_riesgo = 0
    while colocados_riesgo < num_riesgos:
        rx = random.randint(0, FILAS - 1)
        ry = random.randint(0, COLS - 1)
        if (rx, ry) in protegidas_base:
            continue
        if grid[rx][ry].tipo == ' ':
            grid[rx][ry].tipo = '!'
            colocados_riesgo += 1


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


def moverDron(grid, objetivos, numObjetivos, d, viento, lluvia, alerta, turno, finJuego, causaAborto, comandoManual):
    deltas_manuales = {
        "move up": (-1, 0),
        "move down": (1, 0),
        "move left": (0, -1),
        "move right": (0, 1),
    }

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
        dx, dy = deltas_manuales[comandoManual]
        nx, ny = sx + dx, sy + dy
        fuera_limites = (nx < 0 or nx >= FILAS or ny < 0 or ny >= COLS)
        es_obstaculo = (not fuera_limites and grid[nx][ny].tipo == 'X')

        if not fuera_limites and not es_obstaculo:
            d.x = nx
            d.y = ny
            d.bloqueosConsecutivos = 0
            seMovio = 1
            print(f"Comando '{comandoManual}' ejecutado -> ({d.x}, {d.y}).")
        else:
            d.bloqueosConsecutivos += 1
            motivo = "fuera del mapa" if fuera_limites else "escombro 'X'"
            print(f"Movimiento '{comandoManual}' bloqueado ({motivo}). (intento {d.bloqueosConsecutivos}/3)")
            if d.bloqueosConsecutivos >= 3:
                d.bloqueosConsecutivos = 0
                if d.x == BASE_X and d.y == BASE_Y:
                    print("Dron bloqueado en base. Mision finalizada.")
                    finJuego = 1
                    causaAborto = 4
                else:
                    print("3 movimientos bloqueados consecutivos. Regresando a base.")
                    d.enRegreso = 1
                    d.motivoRegreso = 4
                    causaAborto = 4
                return finJuego, causaAborto
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
        if enZonaRiesgo:
            print("Dron en zona de riesgo. Evaluando replica...")
        if evaluarReplicaCortanteBasal(turno, enZonaRiesgo):
            print("REPLICA DETECTADA! Mantente alerta y continua con precaucion.")

    if finJuego == 0 and grid[d.x][d.y].tipo == 'O' and grid[d.x][d.y].visitado == 0:
        grid[d.x][d.y].visitado = 1
        d.objetivosAtendidos += 1
        d.cargaKg = 0
        print(f"Objetivo alcanzado: {grid[d.x][d.y].nombre}. Carga entregada.")
        quedan = 0
        for k in range(numObjetivos):
            if objetivos[k].visitado == 0:
                quedan = 1
        if not quedan:
            print("Todos los objetivos atendidos! Ahora dirigete a la base (0, 0) para completar la mision.")
            d.enRegreso = 1
            d.motivoRegreso = 1
        else:
            print("Aun quedan objetivos pendientes. Continua hacia el siguiente objetivo.")

    return finJuego, causaAborto


# ==============================================================================
# CLASE PARA REDIRIGIR LA CONSOLA AL PANEL DE TEXTO
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
    COMANDOS_VALIDOS = {"move up", "move down", "move left", "move right"}

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simulación Dron - Modo Oscuro Neón")
        self.resize(1040, 680)

        sys.stdout = EmittingStream(textWritten=self.normalOutputWritten)

        self.init_variables()
        self.init_ui()
        self.actualizar_vista_grid()
        self.ejecutar_inicio_mision()

    def init_variables(self):
        random.seed(int(time.time()))
        self.grid = [[Celda() for _ in range(COLS)] for _ in range(FILAS)]

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
        self.setStyleSheet("""
            QWidget { background-color: #121212; color: #FFFFFF; font-family: 'Consolas', monospace; }
            QPushButton {
                background-color: #1E1E1E; border: 2px solid #00FFFF; border-radius: 8px;
                padding: 10px; color: #00FFFF; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background-color: #00FFFF; color: #000000; }
            QPushButton:disabled { border: 2px solid #555555; color: #555555; background-color: #121212; }
            QLineEdit {
                background-color: #1A1A1A; border: 2px solid #FF00FF; border-radius: 6px;
                padding: 8px; color: #FFFFFF; font-size: 14px;
            }
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
        self.lbl_stats.setStyleSheet("color: #FF00FF; font-size: 15px; font-weight: bold;")
        right_panel.addWidget(self.lbl_stats)

        self.consola = QTextEdit()
        self.consola.setReadOnly(True)
        right_panel.addWidget(self.consola)

        # Entrada de comando manual: move up / move down / move left / move right
        cmd_layout = QHBoxLayout()
        self.input_comando = QLineEdit()
        self.input_comando.setPlaceholderText("Escribe: move up, move down, move left, move right")
        self.input_comando.returnPressed.connect(self.procesar_comando_manual)
        cmd_layout.addWidget(self.input_comando)

        self.btn_enviar_cmd = QPushButton("Enviar")
        self.btn_enviar_cmd.clicked.connect(self.procesar_comando_manual)
        cmd_layout.addWidget(self.btn_enviar_cmd)
        right_panel.addLayout(cmd_layout)

        main_layout.addLayout(right_panel)
        main_layout.setStretch(0, 1)
        main_layout.setStretch(1, 1)
        self.setLayout(main_layout)

    def actualizar_vista_grid(self):
        estilos = {
            'B': "background-color: #002244; border: 2px solid #0088FF; color: #0088FF;",
            'O': "background-color: #003300; border: 2px solid #00FF00; color: #00FF00;",
            'X': "background-color: #330000; border: 2px solid #FF0000; color: #FF0000;",
            '!': "background-color: #332200; border: 2px solid #FFAA00; color: #FFAA00;",
            ' ': "background-color: #1A1A1A; border: 1px solid #333333; color: #1A1A1A;"
        }
        estilo_dron = "background-color: #004444; border: 3px solid #00FFFF; color: #00FFFF; font-weight: bold;"

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
        print(f"Base del dron ubicada en ({BASE_X}, {BASE_Y})")
        alertaInicial = "PELIGRO" if (self.alerta == 2) else "PRECAUCION" if (self.alerta == 1) else "NORMAL"
        print(f"Clima inicial: Viento {self.viento} km/h | Lluvia {self.lluvia} mm/h | Alerta: {alertaInicial}")

        print("Objetivos:", end="")
        for k in range(self.numObjetivos):
            if k > 0:
                print(" |", end="")
            print(f" {self.objetivos[k].nombre} (prioridad {self.objetivos[k].prioridad})", end="")
        print("\nComandos disponibles: move up, move down, move left, move right")
        print("==========================================================")

        if self.viento > 50 or self.lluvia > 40:
            print("Despegue denegado por clima adverso.")
            self.btn_enviar_cmd.setEnabled(False)
            self.input_comando.setEnabled(False)
            return

        print("Iniciando mision...")
        self.actualizar_stats()

    def procesar_comando_manual(self):
        if self.finJuego != 0:
            return
        cmd = " ".join(self.input_comando.text().strip().lower().split())
        self.input_comando.clear()
        if cmd not in self.COMANDOS_VALIDOS:
            print(f"Comando no reconocido: '{cmd}'. Usa: move up, move down, move left, move right.")
            return
        self.avanzar_turno(cmd)

    def avanzar_turno(self, comandoManual):
        if self.finJuego != 0:
            return

        self.turno += 1
        print(f"\n--- TURNO {self.turno} ---")

        self.viento, self.lluvia, self.alerta = simularClima(self.viento, self.lluvia, self.alerta)

        nombreAlerta = "NORMAL"
        if self.alerta == 1:
            nombreAlerta = "PRECAUCION"
        if self.alerta == 2:
            nombreAlerta = "PELIGRO"

        self.finJuego, self.causaAborto = moverDron(
            self.grid, self.objetivos, self.numObjetivos, self.wing,
            self.viento, self.lluvia, self.alerta, self.turno,
            self.finJuego, self.causaAborto, comandoManual
        )

        self.actualizar_vista_grid()
        self.actualizar_stats()

        estado = ""
        if self.wing.enRegreso == 2:
            estado = "Aterrizado"
        elif self.wing.enRegreso == 1:
            estado = "Regresando"
        elif self.wing.x == BASE_X and self.wing.y == BASE_Y:
            estado = "En base"
        else:
            estado = "Volando"

        print(f"[Turno {self.turno}] Dron ({self.wing.x},{self.wing.y}) Bat:{self.wing.bateria}% | Viento:{self.viento} Lluvia:{self.lluvia} | {nombreAlerta} | {estado}")

        if self.finJuego == 0 and self.wing.bateria < 10 and not (self.wing.x == BASE_X and self.wing.y == BASE_Y):
            print("BATERIA CRITICA! Aterrizaje de emergencia.")
            self.finJuego = 2
            self.causaAborto = 2
            self.wing.enRegreso = 2

        if self.finJuego == 0 and self.wing.x == BASE_X and self.wing.y == BASE_Y:
            objetivosPendientes = any(obj.visitado == 0 for obj in self.objetivos)
            if not objetivosPendientes and self.wing.objetivosAtendidos >= self.numObjetivos:
                self.finJuego = 1
                self.causaAborto = 0
                print(f"Dron regreso a base tras completar todos los objetivos! Mision finalizada. Turnos: {self.turno}")
            elif objetivosPendientes:
                self.wing.bateria = 100
                cargarEmpaque(self.wing, PESO_MAX_EMPAQUE)
                print("Dron en base. Bateria recargada al 100% y carga lista para el siguiente objetivo.")

        if self.finJuego != 0:
            self.btn_enviar_cmd.setEnabled(False)
            self.input_comando.setEnabled(False)
            self.imprimir_resumen()

    def actualizar_stats(self):
        nombreAlerta = "NORMAL"
        if self.alerta == 1:
            nombreAlerta = "PRECAUCION"
        if self.alerta == 2:
            nombreAlerta = "PELIGRO"

        estado = "Volando"
        if self.wing.enRegreso == 2:
            estado = "Aterrizado"
        elif self.wing.enRegreso == 1:
            estado = "Regresando"
        elif self.wing.x == BASE_X and self.wing.y == BASE_Y:
            estado = "En base"

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
            if self.causaAborto == 1:
                print(f"Clima peligroso (viento {self.viento} km/h, lluvia {self.lluvia} mm/h)")
            elif self.causaAborto == 2:
                print("Bateria insuficiente o critica")
            elif self.causaAborto == 3:
                print("Actividad sismica / replica")
            elif self.causaAborto == 4:
                print("Dron bloqueado por escombros")
            else:
                print("No completada")
        print(f"Turnos totales: {self.turno}")
        print(f"Bateria restante: {self.wing.bateria}%")
        print("==========================================================")

    def normalOutputWritten(self, text):
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
