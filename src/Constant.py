ROWS = 120
COLS = 120
CELL_SIZE = 40
FPS = 60
BANNER_HEIGHT = 100
EPSILON = 1e-1
HEADLESS_SPEEDUP = 30
ELEVATION_ZONE_PLAT_SIZE = 40
ELEVATON_MAX_VALUE = 16
ELEVATON_MIN_VALUE = 0
K_ELEVATION_H = 1.25
K_ELEVATION_D = 0.75
VIEW_ELEVATION = True
UNIT_RADIUS = 0.3


RED = (255, 60, 60)
BLUE = (60, 60, 255)
DARK = (30, 30, 30)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
GOLD = (210, 180, 60)
DARK_GRAY = (50, 50, 50)
PAUSE_OVERLAY_COLOR = (0, 0, 0, 120)


# BattleTournament' Scenarios
DEFAULT_SCENARIOS = [
   
    {"Crossbowman":20, "Pikeman":0,"Knight":0,"startLine":50,"startCol":40,"armyDistance":10,"unitPerCol":10},
    {"Crossbowman":0, "Pikeman":20,"Knight":0,"startLine":50,"startCol":40,"armyDistance":10,"unitPerCol":10},
    {"Crossbowman":0, "Pikeman":0,"Knight":20,"startLine":50,"startCol":40,"armyDistance":10,"unitPerCol":10},
    
    {"Crossbowman":20, "Pikeman":20,"Knight":0,"startLine":50,"startCol":40,"armyDistance":10,"unitPerCol":10},
    {"Crossbowman":0, "Pikeman":20,"Knight":20,"startLine":50,"startCol":40,"armyDistance":10,"unitPerCol":10},
    {"Crossbowman":20, "Pikeman":0,"Knight":20,"startLine":50,"startCol":40,"armyDistance":10,"unitPerCol":10}, 
   
    {"Crossbowman":60, "Pikeman":20,"Knight":20,"startLine":50,"startCol":50,"armyDistance":40,"unitPerCol":10},
    
    {"Crossbowman":60, "Pikeman":60,"Knight":60,"startLine":40,"startCol":40,"armyDistance":15,"unitPerCol":20},
    
    {"Crossbowman":100, "Pikeman":100,"Knight":100,"startLine":40,"startCol":20,"armyDistance":20,"unitPerCol":30},
    
]


ELEVATION_JSON_FILEPATH = "Elevation.json"
STATS_FILEPATH = "Stats_Units.csv"
STATS_BONUS_FILEPATH = "model/Stats_Bonus.csv"
IMAGE_FILES = {
            "Knight_1": "../../img/Sprites/Knight/Red/right.png",
            "Knight_2": "../../img/Sprites/Knight/Blue/left.png",
            "Pikeman_1": "../../img/Sprites/Pikeman/Red/right.png",
            "Pikeman_2": "../../img/Sprites/Pikeman/Blue/left.png",
            "Crossbowman_1": "../../img/Sprites/Crossbowman/Red/right.png",
            "Crossbowman_2": "../../img/Sprites/Crossbowman/Blue/left.png"
}


BACKGROUND = "../../img/backgrounds/back.png"
SAVE_FOLDER = "../save/"
LOGS_FOLDER = "../save/logs/"
REPORTS_FOLDER = "../save/reports/"
PLOTS_FOLDER = "../save/plots/"
