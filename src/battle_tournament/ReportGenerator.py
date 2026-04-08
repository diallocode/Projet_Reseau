import os
import datetime
import html
from math import isfinite
from Constant import REPORTS_FOLDER

# --- Blocs CSS/JS are defined like constants in the module ---
# This guarantees they are defined only one time and facilitates their access.


# --- Classe ReportGenerator 

class ReportGenerator:
    """
    Generate a complete HTML report with tournament results.
    The useful functions of calculation and SVG are statics methods now
    """

    @staticmethod
    def _pct_num(wins, matches):
        """
        Safely calculates the win percentage.
        
        Args:
            wins (int): Number of victories.
            matches (int): Total number of matches played.
            
        Returns:
            float: The win rate percentage (0.0 to 100.0).
        """
        try:
            return (wins / matches * 100) if matches > 0 else 0.0
        except Exception:
            return 0.0

    @staticmethod
    def _bar_svg(percentage, width=160, height=12):
        """
        Generates a dynamic SVG progress bar based on performance.
        
        The bar's color is calculated using a custom RGB gradient logic:
        - Red-to-Orange for low performance (< 50%).
        - Orange-to-Green for high performance (> 50%).
        
        Args:
            percentage (float): The value to represent (0 to 100).
            width (int): Total width of the SVG container in pixels.
            height (int): Height of the bar in pixels.
            
        Returns:
            str: A string containing the inline SVG HTML tags.
        """
        p = max(0.0, min(100.0, percentage))
        if p < 50:
            r = int(255)
            g = int( (p / 50) * 165 )
            b = 0
        else:
            r = int(255 - ((p - 50) / 50) * 155)
            g = int(165 + ((p - 50) / 50) * 90)
            b = 0
        color = f"rgb({r}, {g}, {b})"
        filled_width = int(width * p / 100)
        svg = (f"<svg width='{width}' height='{height}' viewBox='0 0 {width} {height}' "
               f"xmlns='http://www.w3.org/2000/svg' role='img' aria-label='{p:.1f}%'>"
               f"<rect x='0' y='0' width='{width}' height='{height}' rx='3' fill='#e9eef2' />"
               f"<rect x='0' y='0' width='{filled_width}' height='{height}' rx='3' fill='{color}' />"
               f"</svg>")
        return svg

    def generate(self, results, generals):
        """
        Generate and save the HTML report. (Body of ancient function write_report)
        """
        out_dir = os.path.join(os.getcwd(), REPORTS_FOLDER)
        os.makedirs(out_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = os.path.join(out_dir, f"tourney_{ts}.html")

        # ... (Recompute aggregates Logic - use self._pct_num) ...

        per_scenario = results.get("per_scenario", [])
        overall_vs = {g: {h: {"wins": 0, "losses": 0, "draws": 0, "matches": 0} for h in generals} for g in generals}
        per_general_total = {g: {"wins": 0, "losses": 0, "draws": 0, "matches": 0} for g in generals}
        gen_vs_scenario = []

        for scen_entry in per_scenario:
            matrix = scen_entry.get("matrix", {})
            per_gen = {g: {"wins": 0, "losses": 0, "draws": 0, "matches": 0} for g in generals}
            for g in generals:
                for h in generals:
                    cell = matrix.get(g, {}).get(h, {"wins": 0, "losses": 0, "draws": 0, "matches": 0})
                    ov = overall_vs[g][h]
                    ov["wins"] += cell.get("wins", 0)
                    ov["losses"] += cell.get("losses", 0)
                    ov["draws"] += cell.get("draws", 0)
                    ov["matches"] += cell.get("matches", 0)
                    per_gen[g]["wins"] += cell.get("wins", 0)
                    per_gen[g]["losses"] += cell.get("losses", 0)
                    per_gen[g]["draws"] += cell.get("draws", 0)
                    per_gen[g]["matches"] += cell.get("matches", 0)
                    per_general_total[g]["wins"] += cell.get("wins", 0)
                    per_general_total[g]["losses"] += cell.get("losses", 0)
                    per_general_total[g]["draws"] += cell.get("draws", 0)
                    per_general_total[g]["matches"] += cell.get("matches", 0)
            gen_vs_scenario.append({"scenario": scen_entry.get("scenario"), "per_general": per_gen})

        def win_rate_of(g):
            t = per_general_total.get(g, {"wins": 0, "matches": 0})
            return ReportGenerator._pct_num(t["wins"], t["matches"])
        ranked_generals = sorted(generals, key=win_rate_of, reverse=True)

        # HTML generation
        with open(out_file, "w", encoding="utf-8") as f:
            f.write("<!doctype html>\n<html lang='fr'>\n<head>\n<meta charset='utf-8'>\n")
            f.write(f"<title>Tournament report - {ts}</title>\n")
            # favicon (inline SVG) for a polished touch
            f.write("<link rel='icon' href='data:image/svg+xml;utf8, <svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 100 100\"><rect fill=\"%2306b6d4\" width=\"100\" height=\"100\" rx=\"18\"/><text x=\"50\" y=\"60\" font-size=\"40\" text-anchor=\"middle\" font-family=\"sans-serif\" fill=\"white\">AoE</text></svg>' />\n")
            # CSS (responsive cards, table styles, small animations)
            f.write("<style>\n"
                    ":root{--bg:#0f1720;--card:#0b1220;--muted:#94a3b8;--accent:#06b6d4;--panel:#0b1220}\n"
                    "body{font-family:Inter, Segoe UI, Roboto, Arial, Helvetica, sans-serif;background:linear-gradient(180deg, #f6fbff, #eef6ff);color:#0b1220;margin:0;padding:24px}\n"
                    ".wrap{max-width:1200px;margin:0 auto}\n"
                    "header{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px}\n"
                    "h1{font-size:1.4rem;margin:0;color:#0b5}\n"
                    #/* increased contrast for secondary text on light background */
                    ".meta{color:#334155;font-size:0.95rem}\n"
                    ".grid{display:grid;grid-template-columns:repeat(auto-fit, minmax(260px, 1fr));gap:12px;margin:16px 0}\n"
                    ".card{background:#fff;border-radius:10px;padding:12px;box-shadow:0 6px 24px rgba(11, 17, 34, 0.04);border:1px solid #e6eef6}\n"
                    ".rank{display:flex;align-items:center;gap:12px}\n"
                    ".rank .name{font-weight:700}\n"
                    ".muted{color:#334155}\n"
                    ".small{font-size:0.85rem;color:#475569}\n"
                    "table{width:100%;border-collapse:collapse;margin-top:8px}\n"
                    "th, td{padding:8px;border-bottom:1px solid #eef2f7;text-align:center;font-size:0.95rem}\n"
                    "th{background:#f8fafc;color:#0b1220;position:sticky;top:0}\n"
                    ".chip{display:inline-block;padding:4px 8px;border-radius:999px;font-weight:700;font-size:0.85rem;margin:0 4px}\n"
                    ".win{background:#e6ffef;color:#056a33}\n"
                    ".lose{background:#ffecec;color:#7a0b0b}\n"
                    ".draw{background:#f3f4f6;color:#374151}\n"
                    ".toggle{cursor:pointer;color:var(--accent);text-decoration:underline}\n"
                    ".scenario-card{margin:12px 0;padding:12px;border-radius:8px;background:linear-gradient(180deg, #ffffff, #fbfdff);border:1px solid #e6eef6}\n"
                    ".heatcell{padding:6px;border-radius:6px}\n"
                    #/* button & brand styles */
                    ".btn{background:#06b6d4;color:#fff;border:none;padding:8px 10px;border-radius:8px;cursor:pointer;margin-left:8px}\n"
                    ".btn:active{transform:translateY(1px)}\n"
                    ".brand{display:flex;align-items:center;gap:12px}\n"
                    ".brand svg{width:36px;height:36px}\n"
                    "th.sortable{cursor:pointer}\n"
                    "th.sortable:after{content:' \\25B2';opacity:0.25;margin-left:6px}\n"
                    "th.sortable.desc:after{content:' \\25BC'}\n"
                    "</style>\n")

            # JS for collapsing scenarios, sorting and export (CSV/PDF)
            f.write("<script>\n"
                    "function toggle(id){const e=document.getElementById(id);e.style.display=(e.style.display==='none')?'block':'none'}\n"
                    "function sortTable(tableId, colIndex){const tbl=document.getElementById(tableId);const tbody=tbl.tBodies[0];Array.from(tbl.tHead.querySelectorAll('th')).forEach(th=>th.classList.remove('desc'));\n"
                    "let rows=Array.from(tbody.rows);let asc=tbl.getAttribute('data-sort-col')!=colIndex || tbl.getAttribute('data-sort-dir')!='asc';\n"
                    "rows.sort((a, b)=>{let A=a.cells[colIndex].getAttribute('data-sort')||a.cells[colIndex].innerText;let B=b.cells[colIndex].getAttribute('data-sort')||b.cells[colIndex].innerText;A=parseFloat(A);B=parseFloat(B);if(isFinite(A)&&isFinite(B))return asc?B-A:A-B;return asc?String(B).localeCompare(String(A)):String(A).localeCompare(String(B));});\n"
                    "rows.forEach(r=>tbody.appendChild(r));tbl.setAttribute('data-sort-col', colIndex);tbl.setAttribute('data-sort-dir', asc?'asc':'desc');tbl.tHead.rows[0].cells[colIndex].classList.toggle('desc', asc);\n"
                    "}\n"
                    "// download helper and CSV exporter\n"
                    "function download(filename, text, mime='text/csv'){const a=document.createElement('a');const blob=new Blob([text], {type:mime});a.href=URL.createObjectURL(blob);a.download=filename;document.body.appendChild(a);a.click();a.remove();}\n"
                    "function tableToCSV(table){let rows=[];for(let r of table.rows){let cols=Array.from(r.cells).map(c=>'\"'+c.innerText.replace(/\"/g, '\"\"')+'\"');rows.push(cols.join(', '));}return rows.join('\\n');}\n"
                    "function exportCSV(){let parts=[];let ts=new Date().toISOString().replace(/[:\\.]/g, '-');var sections=[{id:'rank-table', name:'Ranking'}, {id:'h2h-table', name:'Head-to-head'}];sections.forEach(s=>{let t=document.getElementById(s.id);if(t){parts.push(s.name);parts.push(tableToCSV(t));parts.push('');}});\n"
                    "let i=0;while(true){let tid='scen_table_'+i;let t=document.getElementById(tid);if(!t)break;parts.push('Scenario #'+(i+1));parts.push(tableToCSV(t));parts.push('');i++;}\n"
                    "download('tournament_report_'+ts+'.csv', parts.join('\\n'))}\n"
                    "function exportPDF(){window.print();}\n"
                    "</script>\n")

            # Header
            f.write("</head>\n<body>\n<div class='wrap'>\n<header>\n  <div>\n    <div class='brand'><svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect fill='#06b6d4' width='100' height='100' rx='14'/></svg><h1>Rapport du tournoi</h1></div>\n    <div class='meta'>Généré: " + html.escape(ts) + "</div>\n  </div>\n  <div style='text-align:right'>\n    <div class='meta'>Généraux: " + ", ".join(html.escape(str(g[1])) for g in generals) + "</div>\n    <div style='margin-top:8px'><button class='btn' onclick=\"exportCSV()\">Exporter CSV</button><button class='btn' onclick=\"exportPDF()\">Exporter PDF</button></div>\n  </div>\n</header>\n")

            # Top cards: summary stats & ranking
            f.write("<div class='grid'>\n")
            # Card 1: Global ranking
            f.write("<div class='card'>\n<h3>Classement global</h3>\n<div class='small muted'>Trié par taux de victoire global</div>\n<table id='rank-table'><thead><tr><th>Rank</th><th>Général</th><th>Win %</th><th>Matches</th></tr></thead><tbody>\n")
            for i, g in enumerate(ranked_generals, start=1):
                 t = per_general_total.get(g, {"wins": 0, "matches": 0})
                 pct = ReportGenerator._pct_num(t["wins"], t["matches"]) # Appel statique
                 f.write("<tr>")
                 f.write(f"<td data-sort='{i}'>{i}</td>")
                 f.write(f"<td class='name'>{html.escape(str(g[1]))}</td>")
                 f.write(f"<td data-sort='{pct:.3f}'>{ReportGenerator._bar_svg(pct)}<div style='display:inline-block;vertical-align:middle;margin-left:8px'>{pct:.1f}%</div></td>") # Appel statique
                 f.write(f"<td data-sort='{t['matches']}'>{t['matches']}</td>")
                 f.write("</tr>\n")
            f.write("</tbody></table>\n</div>\n")

            #  Quick stats summary
            total_matches = sum(per_general_total[g]["matches"] for g in generals)
            total_completed = sum(per_general_total[g]["wins"] + per_general_total[g]["losses"] + per_general_total[g]["draws"] for g in generals) // max(1, len(generals))
            f.write("<div class='card'>\n<h3>Résumé rapide</h3>\n")
            f.write(f"<div class='small'>Généraux: <strong>{len(generals)}</strong></div>\n")
            f.write(f"<div class='small'>Scénarios: <strong>{len(per_scenario)}</strong></div>\n")
            f.write(f"<div class='small'>Total matches (sum perspectives): <strong>{total_matches}</strong></div>\n")
            f.write("<hr />\n")
            f.write("<div class='small'>Conseil: cliquez sur un titre de colonne pour trier la table correspondante.</div>\n")
            f.write("</div>\n")

            # Head-to-head heatmap preview 
            f.write("<div class='card'>\n<h3>Head-to-head </h3>\n<table><thead><tr><th></th>")
            for col in generals:
               f.write(f"<th>{html.escape(col[1])}</th>")
            f.write("</tr></thead><tbody>")
            for row in generals:
                 f.write(f"<tr><th style='text-align:left'>{html.escape(row[1])}</th>")
                 for col in generals:
                     c = overall_vs[row][col]
                     matches = c.get("matches", 0)
                     pct = ReportGenerator._pct_num(c.get("wins", 0), matches) if matches>0 else 0.0
                     bg = f"background:linear-gradient(90deg, rgba(6, 182, 212, {pct/200+0.02}), rgba(6, 182, 212, 0.02));"
                     cell_html = (f"<div class='heatcell' style='padding:6px;border-radius:6px;{bg}'>"
                                  f"<div style='font-weight:700'>{c.get('wins', 0)}-{c.get('losses', 0)}</div>"
                                  f"<div class='small'>{matches} matchs</div>"
                                  f"<div class='small'>{pct:.1f}%</div>"
                                  f"</div>")
                     f.write(f"<td>{cell_html}</td>")
                 f.write("</tr>")
            f.write("</tbody></table>\n</div>\n")  # end card

            f.write("</div>")  # end grid

            # Detailed head-to-head table (sortable)
            f.write("<div class='card' style='margin-top:14px'>\n<h3>Head-to-head détaillé (agrégé)</h3>\n")
            f.write("<table id='h2h-table' data-sort-col='2'><thead><tr>")
            f.write("<th>#</th><th>Général</th>")
            for col in generals:
                 f.write(f"<th>{html.escape(col[1])}</th>")
            f.write("<th>Win %</th></tr></thead><tbody>\n")
            for i, row in enumerate(generals, start=1):
                 f.write("<tr>")
                 f.write(f"<td>{i}</td>")
                 f.write(f"<td style='text-align:left'>{html.escape(row[1])}</td>")
                 row_total_matches = 0
                 row_wins = 0
                 for col in generals:
                     c = overall_vs[row][col]
                     row_total_matches += c.get("matches", 0)
                     row_wins += c.get("wins", 0)
                     cell_html = (f"<span class='chip win'>{c.get('wins', 0)} W</span>"
                                  f"<span class='chip lose'>{c.get('losses', 0)} L</span>"
                                  f"<div class='small'>{c.get('matches', 0)} m</div>")
                     f.write(f"<td>{cell_html}</td>")
                 pct = ReportGenerator._pct_num(row_wins, row_total_matches)
                 f.write(f"<td data-sort='{pct:.3f}'>{pct:.1f}%</td>")
                 f.write("</tr>\n")
            f.write("</tbody></table>\n</div>\n")

            # Per-scenario detailed cards (collapsible)
            f.write("<div style='margin-top:14px'>\n<h2>Détails par scénario</h2>\n")
            if not per_scenario:
                 f.write("<div class='muted'>Aucun scénario enregistré.</div>\n")
            for sidx, scen_entry in enumerate(per_scenario):
                 scen_id = f"scen_{sidx}"
                 scen_repr = html.escape(str(scen_entry.get("scenario")))
                 f.write(f"<div class='scenario-card card'>\n<h3 style='display:flex;justify-content:space-between;align-items:center'>"
                         f"Scénario #{sidx+1} <span class='small muted'>{scen_repr}</span>"
                         f"<button onclick=\"toggle('{scen_id}')\" class='toggle'>Afficher / Masquer</button></h3>\n")
                 # Matrix
                 # add an id on each scenario table to support CSV export
                 f.write(f"<div id='{scen_id}' style='display:block'>\n<table id='scen_table_{sidx}'><thead><tr><th></th>")
                 matrix = scen_entry.get("matrix", {})
                 for col in generals:
                     f.write(f"<th>{html.escape(col[1])}</th>")
                 f.write("</tr></thead><tbody>\n")
                 for row in generals:
                     f.write(f"<tr><th style='text-align:left'>{html.escape(row[1])}</th>")
                     for col in generals:
                         cell = matrix.get(row, {}).get(col, {"wins":0, "losses":0, "draws":0, "matches":0})
                         matches = cell.get("matches", 0)
                         pct = ReportGenerator._pct_num(cell.get("wins", 0), matches) if matches>0 else 0.0
                         cell_html = (f"<div style='display:flex;flex-direction:column;align-items:center'>"
                                      f"{ReportGenerator._bar_svg(pct, width=100, height=10)}"
                                      f"<div class='small' style='margin-top:6px'>{cell.get('wins', 0)}W {cell.get('losses', 0)}L {cell.get('draws', 0)}D</div>"
                                      f"<div class='small'>{matches} m — {pct:.1f}%</div>"
                                      f"</div>")
                         f.write(f"<td>{cell_html}</td>")
                     f.write("</tr>\n")
                 f.write("</tbody></table>\n")
                 # Per-general aggregated for this scenario
                 per_gen = gen_vs_scenario[sidx]["per_general"]
                 f.write("<h4 style='margin-top:10px'>Performance par général (agrégé)</h4>\n")
                 f.write("<table><thead><tr><th>Général</th><th>Wins</th><th>Losses</th><th>Draws</th><th>Matches</th><th>Win %</th></tr></thead><tbody>\n")
                 for g in generals:
                     t = per_gen[g]
                     pct = ReportGenerator._pct_num(t["wins"], t["matches"])
                     f.write(f"<tr><td style='text-align:left'>{html.escape(g[1])}</td><td>{t['wins']}</td><td>{t['losses']}</td><td>{t['draws']}</td><td>{t['matches']}</td><td>{pct:.1f}%</td></tr>\n")
                 f.write("</tbody></table>\n")
                 f.write("</div>\n</div>\n")  # close scenario div 

            # General vs Scenarios 
            f.write("<div style='margin-top:18px' class='card'>\n<h3>Général vs Scénarios (agrégé contre tous adversaires)</h3>\n")
            # header
            f.write("<table><thead><tr><th>Général</th>")
            for sidx, scen_entry in enumerate(per_scenario):
                 f.write(f"<th>Scénario #{sidx+1}</th>")
            f.write("<th>Global Win %</th></tr></thead><tbody>\n")
            # rows
            for g in generals:
                 f.write(f"<tr><th style='text-align:left'>{html.escape(g[1])}</th>")
                 for sidx, scen_entry in enumerate(per_scenario):
                     per_gen = gen_vs_scenario[sidx]["per_general"]
                     t = per_gen.get(g, {"wins":0, "losses":0, "draws":0, "matches":0})
                     pct = ReportGenerator._pct_num(t["wins"], t["matches"])
                     cell_html = (f"<div style='display:flex;flex-direction:column;align-items:center'>"
                                  f"<div style='font-weight:700'>{t['wins']}W / {t['matches']}m</div>"
                                  f"<div class='small'>{pct:.1f}%</div>"
                                  f"</div>")
                     f.write(f"<td>{cell_html}</td>")
                 gt = per_general_total[g]
                 f.write(f"<td>{ReportGenerator._pct_num(gt['wins'], gt['matches']):.1f}%</td></tr>\n")
            f.write("</tbody></table>\n</div>\n")
           
            # Footer
            f.write(f"<div class='muted small' style='margin-top:20px'>Fichier sauvegardé: {html.escape(out_file)}</div>\n")
            f.write("</div>")  # wrap
            f.write("</body></html>\n")

        return out_file
