from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# Simple dictionary to store the latest chunk for each player
player_positions = {}

# HTML template for the live map page
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Live Minecraft Chunk Tracker</title>
    <style>
        body {
            font-family: 'Minecraft', Arial, sans-serif;
            background-color: #1a1a1a;
            color: #ffffff;
            margin: 0;
            padding: 20px;
            text-align: center;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: #2d2d2d;
            border: 4px solid #4a4a4a;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 0 20px rgba(0,0,0,0.5);
        }
        
        h1 {
            color: #44ff44;
            text-shadow: 2px 2px #008800;
            font-size: 32px;
            margin-top: 0;
        }
        
        .players-container {
            margin: 20px 0;
        }
        
        .player-card {
            background-color: #3d3d3d;
            border: 2px solid #555;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            transition: all 0.3s ease;
        }
        
        .player-card:hover {
            border-color: #44ff44;
            transform: scale(1.02);
        }
        
        .player-name {
            color: #ffff55;
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        
        .chunk-info {
            display: flex;
            justify-content: center;
            gap: 40px;
            font-size: 18px;
        }
        
        .chunk-x, .chunk-z {
            background-color: #2d2d2d;
            padding: 8px 20px;
            border-radius: 20px;
            border: 1px solid #666;
        }
        
        .chunk-value {
            color: #55ff55;
            font-weight: bold;
            font-size: 24px;
            margin-left: 10px;
        }
        
        .chunk-grid {
            display: grid;
            grid-template-columns: repeat(9, 1fr);
            gap: 4px;
            max-width: 400px;
            margin: 30px auto;
            background-color: #222;
            padding: 10px;
            border-radius: 8px;
        }
        
        .chunk-cell {
            aspect-ratio: 1;
            background-color: #3d3d3d;
            border: 1px solid #555;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            color: #888;
            position: relative;
        }
        
        .chunk-cell.player-here {
            background-color: #44ff44;
            border-color: #ffff55;
            color: #000;
            font-weight: bold;
        }
        
        .chunk-cell.player-here::after {
            content: "👤";
            position: absolute;
            font-size: 16px;
        }
        
        .stats {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin: 20px 0;
            color: #aaa;
        }
        
        .update-time {
            color: #ffaa00;
            font-size: 14px;
            margin-top: 20px;
        }
        
        .no-players {
            color: #ff5555;
            font-size: 18px;
            padding: 40px;
            background-color: #3d3d3d;
            border-radius: 8px;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .waiting {
            animation: pulse 2s infinite;
            color: #ffaa00;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🗺️ Minecraft Chunk Tracker</h1>
        
        <div class="stats">
            <div>Players Online: <span id="player-count">0</span></div>
            <div>Last Update: <span id="last-update">Never</span></div>
        </div>
        
        <div id="players-list" class="players-container">
            <div class="waiting">Waiting for player data...</div>
        </div>
        
        <div id="chunk-visualization" style="display: none;">
            <h3>Chunk Grid View (Centered on first player)</h3>
            <div id="chunk-grid" class="chunk-grid"></div>
        </div>
        
        <div class="update-time">
            Auto-refreshes every 2 seconds | 
            <a href="/get-status" target="_blank" style="color: #55ffff;">View Raw Data</a>
        </div>
    </div>

    <script>
        function updateDisplay() {
            fetch('/get-status')
                .then(response => response.json())
                .then(data => {
                    const playersList = document.getElementById('players-list');
                    const playerCount = document.getElementById('player-count');
                    const lastUpdate = document.getElementById('last-update');
                    const chunkViz = document.getElementById('chunk-visualization');
                    
                    // Update timestamp
                    const now = new Date();
                    lastUpdate.textContent = now.toLocaleTimeString();
                    
                    // Update player count
                    const playerNames = Object.keys(data);
                    playerCount.textContent = playerNames.length;
                    
                    if (playerNames.length === 0) {
                        playersList.innerHTML = '<div class="no-players">No players currently being tracked</div>';
                        chunkViz.style.display = 'none';
                        return;
                    }
                    
                    chunkViz.style.display = 'block';
                    
                    // Build players list
                    let playersHtml = '';
                    let firstPlayer = null;
                    
                    playerNames.forEach(player => {
                        const pos = data[player];
                        if (!firstPlayer) firstPlayer = {name: player, ...pos};
                        
                        playersHtml += `
                            <div class="player-card">
                                <div class="player-name">👤 ${player}</div>
                                <div class="chunk-info">
                                    <div class="chunk-x">Chunk X: <span class="chunk-value">${pos.chunkX}</span></div>
                                    <div class="chunk-z">Chunk Z: <span class="chunk-value">${pos.chunkZ}</span></div>
                                </div>
                            </div>
                        `;
                    });
                    
                    playersList.innerHTML = playersHtml;
                    
                    // Create chunk grid visualization (centered on first player)
                    if (firstPlayer) {
                        createChunkGrid(firstPlayer.chunkX, firstPlayer.chunkZ, data);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    document.getElementById('players-list').innerHTML = 
                        '<div class="no-players">Error connecting to server. Make sure Flask is running.</div>';
                });
        }
        
        function createChunkGrid(centerX, centerZ, players) {
            const grid = document.getElementById('chunk-grid');
            grid.innerHTML = '';
            
            // Create a 9x9 grid centered on the first player
            for (let z = -4; z <= 4; z++) {
                for (let x = -4; x <= 4; x++) {
                    const cell = document.createElement('div');
                    cell.className = 'chunk-cell';
                    
                    const chunkX = centerX + x;
                    const chunkZ = centerZ + z;
                    
                    // Check if any player is in this chunk
                    let playerInChunk = false;
                    Object.keys(players).forEach(player => {
                        const pos = players[player];
                        if (pos.chunkX === chunkX && pos.chunkZ === chunkZ) {
                            playerInChunk = true;
                        }
                    });
                    
                    if (playerInChunk) {
                        cell.classList.add('player-here');
                    }
                    
                    // Show coordinates for the center area
                    if (Math.abs(x) <= 1 && Math.abs(z) <= 1) {
                        cell.textContent = `${chunkX},${chunkZ}`;
                    }
                    
                    grid.appendChild(cell);
                }
            }
        }
        
        // Update immediately and then every 2 seconds
        updateDisplay();
        setInterval(updateDisplay, 2000);
    </script>
</body>
</html>
"""

@app.route('/chunk-update', methods=['POST'])
def chunk_update():
    data = request.json
    player_name = data.get("player", "Unknown Player")
    cx = data.get("chunkX")
    cz = data.get("chunkZ")

    # Store the latest data
    player_positions[player_name] = {"chunkX": cx, "chunkZ": cz}

    print(f"DEBUG: {player_name} is now in Chunk ({cx}, {cz})")

    return jsonify({"status": "received"}), 200

@app.route('/get-status', methods=['GET'])
def get_status():
    # Visit http://your-ip:5000/get-status to see all players
    return jsonify(player_positions)

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)
import os

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
