import argparse
import json
import time
import urllib.request
import random

SERVER_URL = "http://127.0.0.1:3123"

def send_payload(payload):
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(SERVER_URL, data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as response:
            pass
    except Exception as e:
        print(f"Error sending payload: {e}")

def create_payload(phase="live", bomb_status=None, health=100, armor=100, has_kit=False, weapon="AK-47", ammo=30, ammo_reserve=90, 
                   flashed=0, burning=0, kills=0, assists=0, deaths=0, mvps=0, score=0, position="0, 0, 0", steamid_provider="76561198000000000", steamid_player="76561198000000000"):
    payload = {
        "provider": {
            "name": "Counter-Strike 2",
            "appid": 730,
            "version": 13982,
            "steamid": steamid_provider,
            "timestamp": int(time.time())
        },
        "map": {
            "name": "de_mirage",
            "mode": "competitive"
        },
        "round": {
            "phase": phase
        },
        "player": {
            "steamid": steamid_player,
            "state": {
                "health": health,
                "armor": armor,
                "defusekit": has_kit,
                "flashed": flashed,
                "burning": burning
            },
            "match_stats": {
                "kills": kills,
                "assists": assists,
                "deaths": deaths,
                "mvps": mvps,
                "score": score
            },
            "weapons": {
                "weapon_0": {
                    "name": f"weapon_{weapon.lower().replace('-', '')}",
                    "state": "active",
                    "ammo_clip": ammo,
                    "ammo_reserve": ammo_reserve
                }
            },
            "position": position
        }
    }
    
    if bomb_status:
        payload["round"]["bomb"] = bomb_status
        
    return payload

def run_simulation():
    print(f"Starting CS2 GSI Simulation sending to {SERVER_URL}...")
    
    # Initial State
    health = 100
    ammo = 30
    ammo_reserve = 90
    has_kit = False
    
    kills = 12
    assists = 4
    deaths = 5
    mvps = 2
    score = 34
    
    pos_x, pos_y, pos_z = 0.0, 0.0, 0.0
    
    # Toggle spectator mode simulation every other round maybe? 
    # Let's just keep it simple: playing mostly, maybe switch to spectating mid-run?
    is_spectating = False
    my_steamid = "76561198000000000"
    other_steamid = "76561198000000001"

    while True:
        # 1. Freezetime (5 seconds)
        print("--- Round Start (Freezetime) ---")
        health = 100
        ammo = 30
        ammo_reserve = 90
        has_kit = random.choice([True, False])
        flashed = 0
        burning = 0
        
        # Randomly decide if we are spectating this round
        if random.random() < 0.3:
            current_player_id = other_steamid
            print(" -> Spectating this round")
        else:
            current_player_id = my_steamid
            print(" -> Playing this round")
        
        for _ in range(50): # 5 seconds at 10Hz
            send_payload(create_payload(
                phase="freezetime", 
                health=health, armor=100, has_kit=has_kit, ammo=ammo, ammo_reserve=ammo_reserve,
                kills=kills, assists=assists, deaths=deaths, mvps=mvps, score=score,
                position=f"{pos_x:.2f}, {pos_y:.2f}, {pos_z:.2f}",
                steamid_provider=my_steamid, steamid_player=current_player_id
            ))
            time.sleep(0.1)
            
        # 2. Live Round (10 seconds before bomb)
        print(f"--- Live Round (Kit: {has_kit}) ---")
        for _ in range(100): # 10 seconds
            # Update Position
            pos_x += random.uniform(-5, 5)
            pos_y += random.uniform(-5, 5)

            # Random events
            if random.random() < 0.05: # Shoot
                ammo = max(0, ammo - random.randint(1, 3))
            if random.random() < 0.02: # Take Damage
                health = max(0, health - random.randint(5, 20))
            if random.random() < 0.01: # Get kill
                kills += 1
                score += 2
            if random.random() < 0.05: # Flash / Burn decay
                flashed = max(0, flashed - 10)
                burning = max(0, burning - 10)
            
            # Random Flashbang
            if random.random() < 0.005:
                flashed = 255
            
            # Random Fire
            if random.random() < 0.005:
                burning = 255

            send_payload(create_payload(
                phase="live", 
                health=health, armor=100, has_kit=has_kit, ammo=ammo, ammo_reserve=ammo_reserve,
                flashed=flashed, burning=burning,
                kills=kills, assists=assists, deaths=deaths, mvps=mvps, score=score,
                position=f"{pos_x:.2f}, {pos_y:.2f}, {pos_z:.2f}",
                steamid_provider=my_steamid, steamid_player=current_player_id
            ))
            time.sleep(0.1)
            
        # 3. Bomb Planted (Simulate just a bit)
        print("--- Bomb Planted ---")
        for i in range(50): 
            send_payload(create_payload(
                phase="live", bomb_status="planted",
                health=health, armor=100, has_kit=has_kit, ammo=ammo, ammo_reserve=ammo_reserve,
                flashed=flashed, burning=burning,
                kills=kills, assists=assists, deaths=deaths, mvps=mvps, score=score,
                position=f"{pos_x:.2f}, {pos_y:.2f}, {pos_z:.2f}",
                steamid_provider=my_steamid, steamid_player=current_player_id
            ))
            time.sleep(0.1)
            
        # 4. Round Over
        print("--- Round Over ---")
        for _ in range(50):
             send_payload(create_payload(phase="over", bomb_status="exploded", health=health, armor=100, has_kit=has_kit, ammo=ammo))
             time.sleep(0.1)

if __name__ == "__main__":
    try:
        run_simulation()
    except KeyboardInterrupt:
        print("\nSimulation stopped.")
