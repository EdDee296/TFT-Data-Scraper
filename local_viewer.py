#!/usr/bin/env python3
"""
Simple local web server to view TFT Stats data
Run this to see your collected statistics in a web browser
"""

import http.server
import socketserver
import json
import os
import webbrowser
import threading
import time
from datetime import datetime


class TFTStatsHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_stats_page()
        elif self.path == '/api/stats':
            self.send_json_data()
        elif self.path == '/api/database-info':
            self.send_database_info()
        else:
            super().do_GET()

    def send_stats_page(self):
        """Send the main statistics viewing page"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>TFT Stats - Local Viewer</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #1a1a1a; color: #fff; }
        .header { background: linear-gradient(45deg, #3c5aa6, #5a3c9a); padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .stats-container { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .stat-card { background: #2a2a2a; border: 1px solid #444; border-radius: 8px; padding: 15px; }
        .augment-name { font-weight: bold; color: #ffd700; }
        .stat-value { color: #4ade80; }
        .stage-stats { margin: 10px 0; }
        .stage-title { font-weight: bold; color: #60a5fa; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #444; }
        th { background-color: #333; }
        .loading { text-align: center; color: #888; }
        .error { color: #ef4444; }
        .info-box { background: #1e40af; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 TFT Stats - Local Viewer</h1>
        <p>Real-time augment performance statistics from your local data collection</p>
    </div>
    
    <div class="info-box">
        <h3>📊 Database Status</h3>
        <div id="database-info">Loading database information...</div>
    </div>
    
    <div id="content">
        <div class="loading">Loading TFT Stats data...</div>
    </div>

    <script>
        async function loadDatabaseInfo() {
            try {
                const response = await fetch('/api/database-info');
                const info = await response.json();
                document.getElementById('database-info').innerHTML = `
                    <p><strong>Database:</strong> ${info.database_file}</p>
                    <p><strong>Tables:</strong> ${info.tables.join(', ') || 'No tables found'}</p>
                    <p><strong>Total Records:</strong> ${info.total_records}</p>
                    <p><strong>Last Updated:</strong> ${info.last_updated || 'Unknown'}</p>
                `;
            } catch (error) {
                document.getElementById('database-info').innerHTML = `
                    <p class="error">❌ Could not load database info: ${error.message}</p>
                `;
            }
        }

        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                if (data.length === 0) {
                    document.getElementById('content').innerHTML = `
                        <div class="info-box">
                            <h3>📝 No Data Yet</h3>
                            <p>No augment statistics have been collected yet.</p>
                            <p>Make sure the TFT Stats program is running and processing games.</p>
                        </div>
                    `;
                    return;
                }
                
                // Sort by average placement (lower is better)
                data.sort((a, b) => a.avg - b.avg);
                
                let html = `
                    <h2>📈 Augment Performance Statistics (${data.length} augments tracked)</h2>
                    <div class="stats-container">
                `;
                
                data.forEach(augment => {
                    const placement = augment.avg ? augment.avg.toFixed(2) : 'N/A';
                    const games = augment.games || 0;
                    
                    html += `
                        <div class="stat-card">
                            <div class="augment-name">${augment.name}</div>
                            <div style="margin: 10px 0;">
                                <div>Average Placement: <span class="stat-value">${placement}</span></div>
                                <div>Games Played: <span class="stat-value">${games}</span></div>
                            </div>
                            
                            <div class="stage-stats">
                                <div class="stage-title">Stage 2-1:</div>
                                <div>Avg: ${augment.avg2_1 && augment.avg2_1[0] ? augment.avg2_1[0].toFixed(2) : 'N/A'} 
                                     (${augment.avg2_1 && augment.avg2_1[1] ? augment.avg2_1[1] : 0} games)</div>
                                
                                <div class="stage-title">Stage 3-2:</div>
                                <div>Avg: ${augment.avg3_2 && augment.avg3_2[0] ? augment.avg3_2[0].toFixed(2) : 'N/A'} 
                                     (${augment.avg3_2 && augment.avg3_2[1] ? augment.avg3_2[1] : 0} games)</div>
                                
                                <div class="stage-title">Stage 4-2:</div>
                                <div>Avg: ${augment.avg4_2 && augment.avg4_2[0] ? augment.avg4_2[0].toFixed(2) : 'N/A'} 
                                     (${augment.avg4_2 && augment.avg4_2[1] ? augment.avg4_2[1] : 0} games)</div>
                            </div>
                        </div>
                    `;
                });
                
                html += '</div>';
                document.getElementById('content').innerHTML = html;
                
            } catch (error) {
                document.getElementById('content').innerHTML = `
                    <div class="error">
                        <h3>❌ Error Loading Data</h3>
                        <p>Could not load TFT stats: ${error.message}</p>
                        <p>Make sure data.json exists and the TFT Stats program has processed some games.</p>
                    </div>
                `;
            }
        }
        
        // Load data on page load
        loadDatabaseInfo();
        loadStats();
        
        // Refresh data every 30 seconds
        setInterval(() => {
            loadDatabaseInfo();
            loadStats();
        }, 30000);
    </script>
</body>
</html>
        """

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())

    def send_json_data(self):
        """Send the current JSON data"""
        try:
            if os.path.exists('data.json'):
                with open('data.json', 'r') as f:
                    data = json.load(f)
            else:
                data = []

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def send_database_info(self):
        """Send database information"""
        try:
            import sqlite3

            info = {
                'database_file': 'tft.db',
                'tables': [],
                'total_records': 0,
                'last_updated': None
            }

            if os.path.exists('tft.db'):
                conn = sqlite3.connect('tft.db')
                cursor = conn.cursor()

                # Get table names
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in cursor.fetchall()]
                info['tables'] = tables

                # Count total records
                total = 0
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    total += count
                info['total_records'] = total

                # Get last modification time
                stat = os.stat('tft.db')
                info['last_updated'] = datetime.fromtimestamp(
                    stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')

                conn.close()

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(info).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())


def start_server(port=8000):
    """Start the local web server"""
    try:
        with socketserver.TCPServer(("", port), TFTStatsHandler) as httpd:
            print(f"🌐 TFT Stats Local Viewer running at:")
            print(f"   http://localhost:{port}")
            print(f"   http://127.0.0.1:{port}")
            print()
            print("📊 Open the URL in your browser to view statistics")
            print("🔄 Data refreshes automatically every 30 seconds")
            print("⏹️  Press Ctrl+C to stop the server")
            print()

            # Auto-open browser after a short delay
            def open_browser():
                time.sleep(2)
                webbrowser.open(f'http://localhost:{port}')

            browser_thread = threading.Thread(target=open_browser)
            browser_thread.daemon = True
            browser_thread.start()

            httpd.serve_forever()

    except KeyboardInterrupt:
        print("\n⏹️ Server stopped by user")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {port} is already in use. Try a different port:")
            print(f"   python local_viewer.py --port {port + 1}")
        else:
            print(f"❌ Error starting server: {e}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='TFT Stats Local Viewer')
    parser.add_argument('--port', type=int, default=8000,
                        help='Port to run the server on (default: 8000)')
    args = parser.parse_args()

    print("=== TFT Stats Local Viewer ===")
    print()

    # Check if data files exist
    if not os.path.exists('data.json') and not os.path.exists('tft.db'):
        print("⚠️  Warning: No data files found (data.json or tft.db)")
        print("   Make sure the TFT Stats program has run and collected some data")
        print()

    start_server(args.port)


if __name__ == "__main__":
    main()
