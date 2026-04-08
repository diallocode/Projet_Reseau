from .General import General
from .Battlefield import Battlefield
import os
import datetime
import html
from typing import Dict, Any, List
from util.Functions import get_max_hp, save_report


# --------------------------------------------------------------------------
#                                   CSS
# --------------------------------------------------------------------------
CSS_SNAPSHOT = r"""
:root{
    --color-bg:#f4f6f8;
    --card:#ffffff;
    --border:#e2e8f0;
    --text:#0f172a;
    --accent:#2563eb;

    --attack-bg:#fdecea;
    --attack-border:#f5c7c7;
    --move-bg:#ecfdf5;
    --move-border:#cdeecf;
    --idle-bg:#f8fafc;
    --idle-border:#eceff3;
}

*{box-sizing:border-box}
body{
    margin:0;
    padding:22px;
    font-family:Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
    background:var(--color-bg);
    color:var(--text);
}

/* Header */
.header-box{
    background:var(--card);
    border:1px solid var(--border);
    padding:16px 18px;
    border-radius:8px;
    margin-bottom:20px;
}
.header-box h1{
    margin:0 0 6px 0;
    font-size:1.25rem;
    color:var(--accent);
    font-weight:700;
}
.header-info{display:flex;gap:10px;flex-wrap:wrap;margin-top:8px;}
.header-tag{background:#f8fafc;padding:6px 10px;border-radius:6px;border:1px solid var(--border);font-weight:600;}

/* Controls */
.controls{margin:14px 0;display:flex;gap:10px}
button{background:var(--accent);color:white;border:none;padding:8px 12px;border-radius:6px;cursor:pointer;font-weight:600}
button.secondary{background:#ffffff;color:var(--text);border:1px solid var(--border)}

/* Panels */
.panel{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:12px 14px;margin-bottom:18px}

/* Unit traits grid */
.traits-grid{display:flex;flex-wrap:wrap;gap:12px}
.trait-card{flex:1 1 260px;min-width:220px;background:var(--card);border:1px solid var(--border);border-radius:6px;padding:10px}
.trait-card h4{margin:0 0 8px 0;font-size:1.02rem;color:var(--accent);padding-bottom:6px;border-bottom:1px solid var(--border)}

/* General section */
.general-section{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:18px}
.general-title{font-weight:700;margin-bottom:10px}

/* Unit types horizontally distributed */
.unit-type-grid{display:flex;flex-wrap:wrap;gap:14px}
.unit-type-block{flex:1 1 calc(33.333% - 14px);min-width:260px;background:var(--card);border:1px solid var(--border);border-radius:6px;padding:10px}
@media(max-width:1200px){.unit-type-block{flex:1 1 calc(50% - 14px)}}
@media(max-width:800px){.unit-type-block{flex:1 1 100%}}

/* Sub-category block */
.sub-cat{border-radius:6px;padding:8px;border:1px solid var(--border);margin-bottom:10px}
.sub-cat-title{font-weight:700;margin-bottom:8px}

/* Category color helpers */
.attack-bg{background:var(--attack-bg);border-color:var(--attack-border)}
.move-bg{background:var(--move-bg);border-color:var(--move-border)}
.idle-bg{background:var(--idle-bg);border-color:var(--idle-border)}

/* Table alignment */
.unit-detail-table{width:100%;border-collapse:collapse;font-size:0.95rem}
.unit-detail-table th{background:#fbfdff;padding:8px;border-bottom:1px solid var(--border);text-align:left;color:var(--accent);font-weight:700}
.unit-detail-table td{padding:8px;border-bottom:1px solid var(--border);vertical-align:top}

/* Strong column widths for strict alignment */
.unit-detail-table th:nth-child(1),
.unit-detail-table td:nth-child(1){width:22%}
.unit-detail-table th:nth-child(2),
.unit-detail-table td:nth-child(2){width:14%;text-align:center}
.unit-detail-table th:nth-child(3),
.unit-detail-table td:nth-child(3){width:28%}
.unit-detail-table th:nth-child(4),
.unit-detail-table td:nth-child(4){width:36%}

/* COLLAPSIBLE style B: ▸ / ▾ */
details{border:1px solid var(--border);background:#ffffff;border-radius:6px;padding:8px;margin-bottom:10px}
details>summary{list-style:none;cursor:pointer;font-weight:700;display:flex;justify-content:space-between;align-items:center}
details>summary::-webkit-details-marker{display:none}
details>summary::before{content:"▸";display:inline-block;margin-right:8px;font-size:0.95rem;transform:rotate(0);transition:transform 0.12s}
details[open]>summary::before{content:"▾";transform:rotate(0)}
"""


# --------------------------------------------------------------------------
# Main class
# --------------------------------------------------------------------------
class GameSnapshotReporter:

    def __init__(self, general1: General, general2: General, battlefield: Battlefield):
        self.general1 = general1
        self.general2 = general2
        self.battlefield = battlefield

    # ----------------------------------------------------------------------
    def generate_snapshot(self, current_time):
        data = self._collect_game_data(current_time)
        html = self._generate_html_report(data)
        return save_report(html)

    # ----------------------------------------------------------------------
    def _collect_game_data(self, current_time) -> Dict[str, Any]:
        """
        Collect data :
        - current_order safe (None -> 'idle')
        - position formatting: move -> 1 decimal, others -> 2 decimals
        - target position formatting -> 1 decimal
        - organizes per general -> per type -> categories (attack/move/idle)
        """
        data = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "current_time": current_time,
            "battlefield_size": (self.battlefield.width, self.battlefield.height),
            "generals": []
        }

        for general in [self.general1, self.general2]:
            gen_info = {
                "name": getattr(general, "name", "General"),
                "ai_state": getattr(general, "current_state", "N/A"),
                "army_size": 0,
                "types": {},    # type -> {"attack":[], "move":[], "idle":[]}
                "traits": {}    # per type
            }

            units_list = general.get_my_units(self.battlefield)
            if units_list is None:
                units_list = getattr(general, "army", [])

            for unit in units_list:
                # Defensive attribute access
                u_id = getattr(unit, "id", "?")
                u_name = getattr(unit, "name", "Unknown")
                cur_hp = getattr(unit, "hp", "?")
                max_hp = get_max_hp(unit.name) 

                # Order
                raw_order = getattr(unit, "current_order", None)
                try:
                    order = str(raw_order).lower() if raw_order is not None else "idle"
                except Exception:
                    order = "idle"

                # Position values 
                pos_val = getattr(unit, "position", None)
                pos_two = "(-,-)"
                pos_one = "(-,-)"
                if pos_val and isinstance(pos_val, (list, tuple)) and len(pos_val) >= 2:
                    try:
                        x, y = float(pos_val[0]), float(pos_val[1])
                        pos_two = f"({x:.2f}, {y:.2f})"
                        pos_one = f"({x:.1f}, {y:.1f})"
                    except Exception:
                        pos_two = str(pos_val)
                        pos_one = str(pos_val)

                # Target info
                if getattr(unit, "target_unit", None):
                    tgt = unit.target_unit
                    target_info = f"Unit {getattr(tgt, 'id', '?')} ({getattr(tgt, 'name', '?')})"
                elif getattr(unit, "target_pos", None):
                    tp = unit.target_pos
                    try:
                        tx, ty = float(tp[0]), float(tp[1])
                        target_info = f"({tx:.1f}, {ty:.1f})"
                    except Exception:
                        target_info = str(tp)
                else:
                    target_info = "—"

                # Choose position format based on order
                if "move" in order:
                    pos_fmt = pos_one
                else:
                    pos_fmt = pos_two

                # Prepare unit dict
                u = {
                    "id": u_id,
                    "type": u_name,
                    "hp": f"{cur_hp}/{max_hp}",
                    "position": pos_fmt,
                    "target_info": target_info,
                    "order": order
                }

                # Register type buckets
                if u_name not in gen_info["types"]:
                    gen_info["types"][u_name] = {"attack": [], "move": [], "idle": []}

                if "attack" in order:
                    gen_info["types"][u_name]["attack"].append(u)
                elif "move" in order:
                    gen_info["types"][u_name]["move"].append(u)
                else:
                    gen_info["types"][u_name]["idle"].append(u)

                # Register trait exemplar (first seen)
                if u_name not in gen_info["traits"]:
                    gen_info["traits"][u_name] = {
                        "attack": getattr(unit, "attack", "—"),
                        "armor": getattr(unit, "armor", "—"),
                        "pierce": getattr(unit, "pierce_armor", "—"),
                        "range": getattr(unit, "range", "—"),
                        "speed": (f"{getattr(unit, 'speed', '—'):.1f}"
                                  if isinstance(getattr(unit, 'speed', None), (int, float))
                                  else getattr(unit, 'speed', "—"))
                    }

            # Compute army size safely
            try:
                army_obj = getattr(general, "army", None)
                if army_obj is not None and hasattr(army_obj, "get_unit_alive_number"):
                    gen_info["army_size"] = army_obj.get_unit_alive_number()
                else:
                    gen_info["army_size"] = sum(
                        len(bucket[cat]) for bucket in gen_info["types"].values() for cat in bucket
                    )
            except Exception:
                gen_info["army_size"] = 0

            data["generals"].append(gen_info)

        return data

    # ----------------------------------------------------------------------
    def _row_html(self, u: Dict[str, Any]) -> str:
        return f"""
        <tr>
            <td>{html.escape(str(u['id']))} — {html.escape(u['type'])}</td>
            <td style="text-align:center">{html.escape(u['hp'])}</td>
            <td>{html.escape(u['position'])}</td>
            <td>{html.escape(u['target_info'])}</td>
        </tr>
        """

    # ----------------------------------------------------------------------
    def _section_html(self, title: str, units: List[Dict[str, Any]], css_class: str) -> str:
        if not units:
            return f"""
            <details class="{css_class}">
                <summary>{html.escape(title)} — 0 unités</summary>
                <div style="padding:8px 4px;color:var(--text)">Aucune unité</div>
            </details>
            """
        rows = "".join(self._row_html(u) for u in units)
        return f"""
        <details class="{css_class}" open>
            <summary>{html.escape(title)} — {len(units)} unités</summary>
            <div class="sub-cat {css_class}">
                <div class="sub-cat-title">{html.escape(title)} — {len(units)} unités</div>
                <table class="unit-detail-table">
                    <tr>
                        <th>ID — Type</th>
                        <th>HP</th>
                        <th>Position</th>
                        <th>Cible</th>
                    </tr>
                    {rows}
                </table>
            </div>
        </details>
        """

    # ----------------------------------------------------------------------
    def _generate_html_report(self, data: Dict[str, Any]) -> str:
        # merge traits across generals (first seen wins)
        merged_traits: Dict[str, Dict[str, Any]] = {}
        for g in data["generals"]:
            for t, stats in g.get("traits", {}).items():
                if t not in merged_traits:
                    merged_traits[t] = stats

        # start HTML
        html_out = f"""<!doctype html>
<html lang="fr">
<head><meta charset="utf-8"><title>Snapshot — {data['timestamp']}</title>
<style>{CSS_SNAPSHOT}</style>
</head><body>
<div class="header-box">
    <h1>Snapshot — Rapport</h1>
    <div class="header-info">
        <div class="header-tag">Généré : {data['timestamp']}</div>
        <div class="header-tag">Temps : {data['current_time']}</div>
        <div class="header-tag">Terrain : {data['battlefield_size'][0]} × {data['battlefield_size'][1]}</div>
    </div>
</div>

<div class="controls">
    <button onclick="document.querySelectorAll('details').forEach(d=>d.open=true)">Déplier tout</button>
    <button class="secondary" onclick="document.querySelectorAll('details').forEach(d=>d.open=false)">Replier tout</button>
</div>

<div class="panel">
    <h2 style="margin-top:0;margin-bottom:8px">Traits des unités (exemplaires)</h2>
    <div class="traits-grid">
"""

        for tname, tr in sorted(merged_traits.items()):
            html_out += f"""
        <div class="trait-card">
            <h4>{html.escape(tname)}</h4>
            <div><strong>Attaque:</strong> {html.escape(str(tr.get('attack','—')))}</div>
            <div><strong>Armure:</strong> {html.escape(str(tr.get('armor','—')))}</div>
            <div><strong>Armure perçante:</strong> {html.escape(str(tr.get('pierce','—')))}</div>
            <div><strong>Portée:</strong> {html.escape(str(tr.get('range','—')))}</div>
            <div><strong>Vitesse:</strong> {html.escape(str(tr.get('speed','—')))}</div>
        </div>
"""

        html_out += "</div></div>"

        # Per general
        for g in data["generals"]:
            html_out += f"""
<div class="general-section">
  <div class="general-title">{html.escape(g['name'])} — {g.get('army_size',0)} unités</div>
  <div class="unit-type-grid">
"""
            for utype, bucket in sorted(g.get("types", {}).items()):
                html_out += f"""
    <div class="unit-type-block">
      <details open>
        <summary>{html.escape(utype)}</summary>
        <!-- subcategories inside -->
        {self._section_html('Attaque', bucket.get('attack', []), 'attack-bg')}
        {self._section_html('Mouvement', bucket.get('move', []), 'move-bg')}
        {self._section_html('Idle / Divers', bucket.get('idle', []), 'idle-bg')}
      </details>
    </div>
"""
            html_out += "</div></div>"

        html_out += "</body></html>"
        return html_out
