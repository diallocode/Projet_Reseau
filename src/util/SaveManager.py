import json
import os
from typing import Any, Dict, List, Optional, Callable

from Constant import SAVE_FOLDER, ROWS, COLS
from util.Functions import create_strategy
from model.General import General
from model.Battlefield import Battlefield
from util.UnitsFactory import UnitsFactory


class SaveManager:
    """
    JSON serializer/deserializer for an ongoing battle.

    * save_battle(battle, path) writes the current state.
    * load_battle(path, view_factory) recreates a Battle instance.
    """

    VERSION = 1
    QUICK_FILENAME = "quick_save.json"

    @classmethod
    def _quick_path(cls) -> str:
        return os.path.join(SAVE_FOLDER, cls.QUICK_FILENAME)

    @staticmethod
    def _ensure_save_dir():
        os.makedirs(SAVE_FOLDER, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @classmethod
    def save_battle(cls, battle, path: Optional[str] = None) -> str:
        """Serialize the running battle to JSON."""
        cls._ensure_save_dir()
        path = path or cls._quick_path()
        data = cls._serialize_battle(battle)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return os.path.abspath(path)

    @classmethod
    def save_battlepass(cls, battle, path: Optional[str] = None) -> str:
        """Backward-compatible quick save entrypoint."""
        return cls.save_battle(battle, path=path)

    @classmethod
    def load_battle(
        cls,
        path: Optional[str] = None,
        view_factory: Optional[Callable[[Battlefield], Any]] = None,
    ):
        """
        Load a battle from JSON and recreate a Battle instance.

        Args:
            path: json save path (defaults to QUICK_FILENAME).
            view_factory: optional callable that takes a Battlefield
                          and returns a view (e.g., lambda bf: GUI(bf)).
        """
        path = path or cls._quick_path()
        if path and not os.path.isabs(path) and not os.path.exists(path):
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            path = os.path.join(base_dir, path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls._deserialize_battle(data, view_factory=view_factory)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @classmethod
    def _serialize_battle(cls, battle) -> Dict[str, Any]:
        generals = []
        if hasattr(battle, "general1") and hasattr(battle, "general2"):
            generals = [battle.general1, battle.general2]
        elif hasattr(battle, "generals"):
            generals = list(battle.generals)

        camera_data = None
        view = getattr(battle, "view", None)
        if view and hasattr(view, "zoom_x") and hasattr(view, "zoom_y"):
            camera_data = {
                "zoom_x": getattr(view, "zoom_x", None),
                "zoom_y": getattr(view, "zoom_y", None),
                "zoom_factor": getattr(view, "zoom_factor", None),
            }

        generals_data: List[Dict[str, Any]] = []
        for g_idx, general in enumerate(generals):
            generals_data.append(
                {
                    "name": getattr(general, "name", f"General {g_idx+1}"),
                    "id": getattr(general, "id", g_idx + 1),
                    "strategy": general.strategy.__class__.__name__,
                }
            )

        units_data: List[Dict[str, Any]] = []
        battlefield = getattr(battle, "battlefield", None)
        if battlefield:
            for unit_id, unit in battlefield.troupes.items():
                target_unit = getattr(unit, "target_unit", None)
                target_id = target_unit.id if target_unit and target_unit.position else None
                units_data.append(
                    {
                        "id": unit_id,
                        "name": unit.name,
                        "hp": unit.hp,
                        "position": list(unit.position) if unit.position is not None else None,
                        "current_order": unit.current_order,
                        "target_pos": list(unit.target_pos) if unit.target_pos is not None else None,
                        "attack_delay": getattr(unit, "attack_delay", 0),
                        "reload_time": getattr(unit, "reload_time", 0),
                        "target_id": target_id,
                    }
                )

        battle_data = {
            "version": cls.VERSION,
            "battlefield": {
                "width": getattr(battlefield, "width", COLS),
                "height": getattr(battlefield, "height", ROWS),
            },
            "paused": getattr(battle, "paused", False),
            "winner": getattr(getattr(battle, "winner", None), "name", None),
            "generals": generals_data,
            "units": units_data,
            "camera": camera_data,
        }
        return battle_data

    @classmethod
    def _deserialize_battle(
        cls,
        data: Dict[str, Any],
        view_factory: Optional[Callable[[Battlefield], Any]] = None,
    ):
        from model.Battle import Battle  # Local import to avoid circular dependency

        bf_info = data.get("battlefield", {})
        factory = UnitsFactory()
        units_payload = data.get("units", [])
        unit_map: Dict[int, Any] = {}

        for u in units_payload:
            unit_id = u["id"]
            unit = factory.create_unit(unit_id, u["name"])
            unit.hp = u.get("hp", unit.hp)
            pos = u.get("position")
            unit.position = tuple(pos) if pos is not None else None
            unit.current_order = u.get("current_order")
            tgt_pos = u.get("target_pos")
            unit.target_pos = tuple(tgt_pos) if tgt_pos is not None else None
            unit.attack_delay = u.get("attack_delay", unit.attack_delay)
            unit.reload_time = u.get("reload_time", unit.reload_time)
            unit_map[unit_id] = unit

        battlefield = Battlefield(
            bf_info.get("width", COLS),
            bf_info.get("height", ROWS),
            unit_map,
        )

        generals: List[General] = []
        generals_payload = data.get("generals", [])
        for g_idx, gen_data in enumerate(generals_payload):
            strategy_name = gen_data.get("strategy")
            strategy = create_strategy(strategy_name) if strategy_name else create_strategy("Daft")
            general = General(
                gen_data.get("name", f"General {g_idx+1}"),
                gen_data.get("id", g_idx + 1),
                strategy,
            )
            generals.append(general)

        for u in units_payload:
            target_id = u.get("target_id")
            if target_id is None:
                continue
            unit = unit_map.get(u["id"])
            target_unit = unit_map.get(target_id)
            if unit and target_unit:
                unit.target_unit = target_unit

        if len(generals) < 2:
            raise ValueError("Save file must contain at least two generals.")

        camera_data = data.get("camera")
        view = cls._build_view(view_factory, battlefield, generals)
        if view and camera_data:
            cls._apply_camera_state(view, camera_data)
        battle = Battle(generals[0], generals[1], battlefield, view)
        battle.camera_state = camera_data
        battle.paused = data.get("paused", False)
        return battle

    @staticmethod
    def _apply_camera_state(view, camera_data: Dict[str, Any]):
        if not camera_data:
            return
        if "zoom_factor" in camera_data and hasattr(view, "zoom_factor"):
            view.zoom_factor = camera_data["zoom_factor"]
        if "zoom_x" in camera_data and hasattr(view, "zoom_x"):
            view.zoom_x = camera_data["zoom_x"]
        if "zoom_y" in camera_data and hasattr(view, "zoom_y"):
            view.zoom_y = camera_data["zoom_y"]
        if hasattr(view, "capture_x") and hasattr(view, "zoom_x"):
            view.capture_x = view.zoom_x
        if hasattr(view, "capture_y") and hasattr(view, "zoom_y"):
            view.capture_y = view.zoom_y

    @staticmethod
    def _build_view(
        view_factory: Optional[Callable[..., Any]],
        battlefield: Battlefield,
        generals: List[General],
    ):
        if not view_factory:
            return None
        try:
            return view_factory(battlefield, generals)
        except TypeError:
            try:
                return view_factory(battlefield)
            except TypeError:
                try:
                    from view.GUI import GUI
                except Exception:
                    return None
                try:
                    view_elevation = getattr(battlefield, "heightmap", None) is not None
                    return GUI(battlefield, generals, view_elevation)
                except Exception:
                    return None
