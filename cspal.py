import json
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.align import Align
from rich.table import Table
from rich.text import Text
from rich import box

GAME_PORT = 3123
BOMB_DURATION = 40
DEFUSE_TIME_NO_KIT = 10
DEFUSE_TIME_KIT = 5

# Shared State
state = {
    "bomb_active": False,
    "bomb_planted_time": None,
    "round_phase": "warmup",
    "health": 100,
    "armor": 0,
    "weapon": "knife",
    "ammo": 0,
    "has_defuser": False,
    "last_updated": None,
    "map_name": "unknown",
    "steamid_provider": None,
    "steamid_player": None,
    "kills": 0,
    "assists": 0,
    "deaths": 0,
    "mvps": 0,
    "score": 0,
    "position": "0,0,0",
    "flashed": 0,
    "burning": 0,
    "ammo_reserve": 0
}

class CS2RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_POST(self):
        state['last_updated'] = time.time()
        length = int(self.headers['Content-Length'])
        data = json.loads(self.rfile.read(length))
        
        # 0. Provider & Map
        if 'provider' in data:
            state['steamid_provider'] = data['provider'].get('steamid')
            
        if 'map' in data:
            state['map_name'] = data['map'].get('name', 'unknown')

        # 1. Parse Round & Bomb
        if 'round' in data:
            rnd = data['round']
            state['round_phase'] = rnd.get('phase', '')
            bomb_status = rnd.get('bomb', '')

            if bomb_status == 'planted':
                if not state['bomb_active']:
                    state['bomb_active'] = True
                    state['bomb_planted_time'] = time.time()
            elif bomb_status in ['defused', 'exploded'] or state['round_phase'] == 'freezetime':
                state['bomb_active'] = False
                state['bomb_planted_time'] = None

        # 2. Parse Player State
        if 'player' in data:
            p = data['player']
            state['steamid_player'] = p.get('steamid')
            
            if 'state' in p:
                state['health'] = p['state'].get('health', 0)
                state['armor'] = p['state'].get('armor', 0)
                state['has_defuser'] = p['state'].get('defusekit', False)
                state['flashed'] = p['state'].get('flashed', 0)
                state['burning'] = p['state'].get('burning', 0)
                
            if 'match_stats' in p:
                ms = p['match_stats']
                state['kills'] = ms.get('kills', 0)
                state['assists'] = ms.get('assists', 0)
                state['deaths'] = ms.get('deaths', 0)
                state['mvps'] = ms.get('mvps', 0)
                state['score'] = ms.get('score', 0)
            
            state['position'] = p.get('position', "0,0,0")

            if 'weapons' in p:
                for w in p['weapons'].values():
                    if w.get('state') == 'active':
                        state['weapon'] = w.get('name', '').replace('weapon_', '')
                        state['ammo'] = w.get('ammo_clip', 0)
                        state['ammo_reserve'] = w.get('ammo_reserve', 0)
                        break
        
        self.send_response(200)
        self.end_headers()

def generate_ui():
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="upper", size=12),
        Layout(name="lower"),
        Layout(name="footer", size=3)
    )

    # --- HEADER ---
    map_text = f"[bold blue]{state['map_name']}[/]"
    
    # Check Spectator Mode
    is_spectating = False
    if state['steamid_provider'] and state['steamid_player']:
        if state['steamid_provider'] != state['steamid_player']:
            is_spectating = True

    if is_spectating:
        spec_text = "[bold magenta]SPECTATING[/]"
    else:
        spec_text = "[bold green]PLAYING[/]"

    header_grid = Table.grid(expand=True)
    header_grid.add_column(justify="left")
    header_grid.add_column(justify="right")
    header_grid.add_row(f"Map: {map_text}", spec_text)

    layout["header"].update(Panel(header_grid, border_style="blue"))

    # --- BOMB LOGIC ---
    if state['bomb_active'] and state['bomb_planted_time']:
        elapsed = time.time() - state['bomb_planted_time']
        remaining = BOMB_DURATION - elapsed
        
        # Determine Defuse Status
        required_time = DEFUSE_TIME_KIT if state['has_defuser'] else DEFUSE_TIME_NO_KIT
        
        if remaining <= 0:
            status_text = Text("BOOM", style="bold white on red")
            defuse_msg = Text("TOO LATE", style="bold red")
            border_col = "red"
        elif remaining > required_time:
            status_text = Text(f"{remaining:.2f} s", style="bold white on red")
            defuse_msg = Text("DEFUSE POSSIBLE", style="bold green")
            border_col = "red"
        elif remaining > 5 and not state['has_defuser']:
            # Case: between 5s and 10s, but no kit
            status_text = Text(f"{remaining:.2f} s", style="bold white on red")
            defuse_msg = Text("NEED KIT TO DEFUSE", style="bold yellow blink")
            border_col = "yellow"
        else:
            status_text = Text(f"{remaining:.2f} s", style="bold white on red")
            defuse_msg = Text("RUN / SAVE", style="bold white on red blink")
            border_col = "red"

        # Combine into a grid for the panel
        grid = Table.grid(expand=True)
        grid.add_column(justify="center")
        grid.add_row(status_text)
        grid.add_row(Text(" ")) # spacer
        grid.add_row(defuse_msg)

        status_panel = Panel(
            grid,
            title="[bold red]BOMB ACTIVE[/]",
            border_style=border_col
        )
    else:
        status_panel = Panel(
            Align.center("[green]SAFE[/]", vertical="middle"),
            title="BOMB STATUS",
            border_style="green"
        )

    layout["upper"].update(status_panel)

    # --- STATS LOGIC ---
    # Create two columns: Vitals and Match Stats
    stats_grid = Table.grid(expand=True, padding=(0, 2))
    stats_grid.add_column(ratio=1)
    stats_grid.add_column(ratio=1)

    # Vitals Table
    vitals_table = Table(box=box.SIMPLE, title="Vitals", expand=True)
    vitals_table.add_column("Stat")
    vitals_table.add_column("Value", justify="right")

    hp_style = "green" if state['health'] > 50 else "red blinking"
    vitals_table.add_row("Health", f"[{hp_style}]{state['health']}[/]")
    vitals_table.add_row("Armor", str(state['armor']))
    vitals_table.add_row("Kit", "[blue]YES[/]" if state['has_defuser'] else "[dim]NO[/]")
    
    # Weapon & Ammo
    ammo_str = f"{state['ammo']} / {state['ammo_reserve']}"
    vitals_table.add_row("Weapon", state['weapon'].upper())
    vitals_table.add_row("Ammo", ammo_str)

    # Environmental Effects
    if state['flashed'] > 200:
        vitals_table.add_row("Status", "[bold white on black] BLINDED [/]")
    elif state['burning'] > 0:
        vitals_table.add_row("Status", "[bold white on red] BURNING [/]")
    else:
        vitals_table.add_row("Status", "[dim]Normal[/]")

    # Match Stats Table
    match_table = Table(box=box.SIMPLE, title="Match Stats", expand=True)
    match_table.add_column("Stat")
    match_table.add_column("Value", justify="right")

    match_table.add_row("K / A / D", f"{state['kills']} / {state['assists']} / {state['deaths']}")
    match_table.add_row("MVPs", str(state['mvps']))
    match_table.add_row("Score", str(state['score']))
    match_table.add_row("Pos", state['position'])

    stats_grid.add_row(Panel(vitals_table), Panel(match_table))

    layout["lower"].update(Panel(stats_grid, title="Player Information"))

    # --- FOOTER / CONNECTION STATUS ---
    now = time.time()
    last = state.get('last_updated')
    
    if last is None:
        footer_text = "[red]WAITING FOR GAME DATA...[/]"
        border_style = "red"
    else:
        diff = now - last
        if diff < 5:
            footer_text = f"[green]CONNECTED[/]"
            border_style = "green"
        else:
            footer_text = f"[yellow]STALE[/]  Last Update: {diff:.1f}s ago"
            border_style = "yellow"

    layout["footer"].update(
        Panel(Align.center(footer_text), border_style=border_style)
    )

    return layout

def run_server():
    server = HTTPServer(('127.0.0.1', GAME_PORT), CS2RequestHandler)
    server.serve_forever()

if __name__ == "__main__":
    t = threading.Thread(target=run_server, daemon=True)
    t.start()

    with Live(generate_ui(), refresh_per_second=10, screen=True) as live:
        try:
            while True:
                live.update(generate_ui())
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass