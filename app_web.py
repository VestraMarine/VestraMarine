from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
import sqlite3
import webbrowser
import io
import csv
from threading import Timer

app = Flask(__name__)
app.secret_key = "vestramarine_secure_key_2032"
DB_NAME = "vestramarine_web.db"

# --- SYSTEM INIT: DATABASE ENGINES ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # 🧬 Marine Records Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS marine_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT NOT NULL,
            water_temp REAL,
            salinity REAL,
            species TEXT,
            notes TEXT
        )
    ''')
    # 👥 NEW: User Accounts Credentials Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # Pre-populate our signature admin gate account if it doesn't exist
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("admin", "ocean123"))
        conn.commit()
    except sqlite3.IntegrityError:
        pass # Already exists
        
    conn.close()

init_db()

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000")

# --- ROUTE: LOGIN GATEWAY ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid Credentials! Click Sign Up below if you are new.")
            
    return '''
        <body style="background-color: #0B2F2F; color: white; font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; padding: 20px; box-sizing: border-box;">
            <div style="background-color: #0D3B3B; padding: 30px; border-radius: 8px; border: 2px solid #004D40; text-align: center; width: 100%; max-width: 320px; box-sizing: border-box;">
                <h1 style="color: #4DB6AC; margin-bottom: 5px; letter-spacing: 2px; font-size: 24px;">VESTRAMARINE</h1>
                <p style="color: #80CBC4; font-size: 12px; margin-bottom: 25px; font-style: italic;">Oceanic Database Portal</p>
                
                <form method="POST">
                    <input type="text" name="username" placeholder="Scientist ID / Username" required style="width: 100%; padding: 12px; margin-bottom: 15px; border-radius: 4px; border: none; background: #0B2F2F; color: white; box-sizing: border-box; font-size: 16px;"><br>
                    <input type="password" name="password" placeholder="Access Code / Password" required style="width: 100%; padding: 12px; margin-bottom: 20px; border-radius: 4px; border: none; background: #0B2F2F; color: white; box-sizing: border-box; font-size: 16px;"><br>
                    <button type="submit" style="background-color: #004D40; color: white; border: none; width: 100%; padding: 12px; font-weight: bold; border-radius: 4px; cursor: pointer; font-size: 16px; width: 100%;">Initialize Session</button>
                </form>
                
                <p style="margin-top: 20px; font-size: 14px; color: #80CBC4;">New to the fleet? <a href="/signup" style="color: #4DB6AC; font-weight: bold; text-decoration: none;">Create Account</a></p>
            </div>
        </body>
    '''

# --- NEW ROUTE: ACCOUNT CREATION SIGN UP ---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            flash("Account created successfully! Please log in.")
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            flash("That Username is already claimed by another scientist!")
            
    return '''
        <body style="background-color: #0B2F2F; color: white; font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; padding: 20px; box-sizing: border-box;">
            <div style="background-color: #0D3B3B; padding: 30px; border-radius: 8px; border: 2px solid #004D40; text-align: center; width: 100%; max-width: 320px; box-sizing: border-box;">
                <h1 style="color: #4DB6AC; margin-bottom: 5px; letter-spacing: 2px; font-size: 24px;">FLEET REGISTRATION</h1>
                <p style="color: #80CBC4; font-size: 12px; margin-bottom: 25px; font-style: italic;">Create Your Scientist Access Profile</p>
                
                <form method="POST">
                    <input type="text" name="username" placeholder="Choose Scientist ID" required style="width: 100%; padding: 12px; margin-bottom: 15px; border-radius: 4px; border: none; background: #0B2F2F; color: white; box-sizing: border-box; font-size: 16px;"><br>
                    <input type="password" name="password" placeholder="Create Access Password" required style="width: 100%; padding: 12px; margin-bottom: 20px; border-radius: 4px; border: none; background: #0B2F2F; color: white; box-sizing: border-box; font-size: 16px;"><br>
                    <button type="submit" style="background-color: #00796B; color: white; border: none; width: 100%; padding: 12px; font-weight: bold; border-radius: 4px; cursor: pointer; font-size: 16px; width: 100%;">Register Profile</button>
                </form>
                
                <p style="margin-top: 20px; font-size: 14px; color: #80CBC4;">Already registered? <a href="/" style="color: #4DB6AC; font-weight: bold; text-decoration: none;">Log In here</a></p>
            </div>
        </body>
    '''

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if request.method == 'POST' and 'add_entry' in request.form:
        loc = request.form.get('location')
        temp = request.form.get('water_temp')
        sal = request.form.get('salinity')
        spec = request.form.get('species')
        note = request.form.get('notes')
        
        cursor.execute("INSERT INTO marine_data (location, water_temp, salinity, species, notes) VALUES (?, ?, ?, ?, ?)", 
                       (loc, float(temp or 0.0), float(sal or 0.0), spec, note))
        conn.commit()

    if request.method == 'POST' and 'delete_id' in request.form:
        del_id = request.form.get('delete_id')
        cursor.execute("DELETE FROM marine_data WHERE id = ?", (del_id,))
        conn.commit()

    search_query = request.args.get('search', '')
    if search_query:
        cursor.execute("SELECT id, location, water_temp, salinity, species, notes FROM marine_data WHERE location LIKE ? OR species LIKE ? ORDER BY id DESC", 
                       ('%'+search_query+'%', '%'+search_query+'%'))
    else:
        cursor.execute("SELECT id, location, water_temp, salinity, species, notes FROM marine_data ORDER BY id DESC")
        
    raw_rows = cursor.fetchall()
    
    formatted_rows = []
    for row_id, loc, temp, sal, spec, note in raw_rows:
        formatted_rows.append({
            'id': row_id,
            'location': loc,
            'temp': temp,
            'salinity': sal,
            'species': spec,
            'notes': note
        })
    
    cursor.execute("SELECT COUNT(*), AVG(water_temp) FROM marine_data")
    count, avg_temp = cursor.fetchone()
    avg_temp = round(avg_temp, 2) if avg_temp else 0.0
    
    conn.close()
    return render_template('dashboard.html', rows=formatted_rows, count=count, avg_temp=avg_temp, search_query=search_query)

@app.route('/export')
def export_csv():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT location, water_temp, salinity, species, notes FROM marine_data ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Location / Region', 'Water Temperature (C)', 'Salinity (PSU)', 'Tracked Species', 'Scientist Notes'])
    writer.writerows(rows)
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=vestramarine_telemetry_report.csv"}
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    Timer(1, open_browser).start()
    app.run(host='127.0.0.1', port=5000, debug=True, use_reloader=False)
