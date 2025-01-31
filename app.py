from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from infodestination import destinations_data
from culture import cultureheritages_data
from food import foodgastronomy_data
from mysql.connector import Error
from churchs import churches_data
from htls import hotels_data
from otrs import others_data
import mysql.connector
import bcrypt
from adm import adm
from estabadm import estabadm
from estab2adm import estab2adm
import os
from infodestination import search_destination
import bcrypt
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
app.secret_key = 'your_secret_key'

app.config['UPLOAD_FOLDER'] = 'static/assets/uploads'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def create_connection():
    try:
        connection = mysql.connector.connect(
            host='127.0.0.1',
            user='root',
            password='',  
            database='lipacitytourism'
        )
        if connection.is_connected():
            print("Successfully connected to the database")
        return connection
    except Error as e:
        print(f"Error: '{e}'")
        return None

def hash_and_update_password(connection, email, plain_password):
    try:
        hashed_password = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt())
        
        with connection.cursor() as cursor:
            cursor.execute("UPDATE login SET password = %s WHERE email = %s", (hashed_password.decode('utf-8'), email))
            connection.commit()
            print(f"Password for {email} has been updated and hashed.")
    
    except Error as e:
        print(f"Error: '{e}'")

db_connection = create_connection()

if db_connection:
    hash_and_update_password(db_connection, 'casadesegunda@gmail.com', 'CasadeSegunda_123')
    hash_and_update_password(db_connection, 'museodelipa@gmail.com', 'MuseodeLipa_123')
    
    db_connection.close()

def get_top_items(data_source):
    connection = create_connection()
    cursor = connection.cursor()

    query = """
    SELECT place, COUNT(*) as count 
    FROM ratings 
    WHERE star_rate = 5 
    GROUP BY place 
    ORDER BY count DESC 
    """
    cursor.execute(query)
    results = cursor.fetchall()
    connection.close()

    seen_items = set()
    top_items = []

    for row in results:
        item_name = row[0]
        if item_name not in seen_items:
            item = next((item for item in data_source if item['name'] == item_name), None)
            if item:
                top_items.append(item)
                seen_items.add(item_name)

    return top_items[:5]

def get_reviews(connection):
    query = """
    SELECT place, GROUP_CONCAT(comment SEPARATOR '<br>') AS comments, MAX(star_rate) AS highest_star_rate
    FROM ratings
    WHERE star_rate
    AND place IS NOT NULL
    GROUP BY place
    ORDER BY highest_star_rate DESC
    LIMIT 6
    """
    cursor = connection.cursor()
    cursor.execute(query)
    reviews = cursor.fetchall()
    cursor.close()

    # Limit comments to 5 per place
    result = []
    for row in reviews:
        comments = row[1].split('<br>')  # Split the concatenated comments
        limited_comments = '<br>'.join(comments[:5])  # Take only the first 5 comments
        result.append({'place': row[0], 'comment': limited_comments, 'star_rate': row[2]})
    return result

@app.route('/')
def home():
    connection = create_connection()
    
    # Fetch reviews using the connection
    reviews = get_reviews(connection)
    
    # Fetch top items
    top_heritages = get_top_items(cultureheritages_data)
    top_hotels = get_top_items(hotels_data)
    top_food_gastronomy = get_top_items(foodgastronomy_data)
    
    # Render template with reviews and other top items
    return render_template('home.html', 
                           top_heritages=top_heritages, 
                           top_hotels=top_hotels, 
                           top_food_gastronomy=top_food_gastronomy, 
                           reviews=reviews)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    if query:
        results = search_destination(query)
        return jsonify(results)
    return jsonify([])

for destination in destinations_data:
    if 'category' not in destination:
        print(f"Missing 'category' in destination: {destination['name']}")

@app.route('/destinations', methods=['GET', 'POST'])
def destinations_index():
    if request.method == 'POST':
        selected_interests = request.form.getlist('interest')  # Get selected interests from the form
        # Filter destinations based on selected interests
        filtered_destinations = [
            destination for destination in destinations_data
            if destination.get('category', '').lower() in (interest.lower() for interest in selected_interests)
        ]
        return render_template('destinations.html', destinations=filtered_destinations)
    
    # Render all destinations if no filter is applied
    return render_template('destinations.html', destinations=destinations_data)

@app.route('/destinations/<int:destination_id>')
def destination_details(destination_id):
    if destination_id < 0 or destination_id >= len(destinations_data):
        return "Destination not found", 404
    destination = destinations_data[destination_id]
    # Fetch ratings for the destination
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM ratings WHERE place = %s ORDER BY created_at DESC", (destination['name'],))
    ratings = cursor.fetchall()
    cursor.close()
    connection.close()
    
    if not ratings:  # If no ratings are found, you could also send a flag or handle in some other way
        ratings = None
    
    return render_template('desplaces.html', destination=destination, ratings=ratings)

@app.route('/submit-rating', methods=['POST'])
def submit_rating():
    if 'adventurerID' not in session:
        flash('You need to log in before accessing this destination.', 'warning')
        return redirect(url_for('login'))
    
    name = request.form.get('name')
    place = request.form.get('place')
    star_rate = request.form.get('star_rate')
    comment = request.form.get('comment')
    recommendation = request.form.get('recommendation')
    
    if not all([name, place, star_rate, comment, recommendation]):
        flash('Please fill out all fields.', 'warning')
        return redirect(url_for('destinations_index'))

    try:
        star_rate = int(star_rate)
        if star_rate < 1 or star_rate > 5:
            raise ValueError("Star rating must be between 1 and 5.")
    except ValueError:
        flash('Invalid star rating. Please select a value between 1 and 5.', 'warning')
        return redirect(url_for('destinations_index'))

    connection = create_connection()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO ratings (name, place, star_rate, comment, recommendation) VALUES (%s, %s, %s, %s, %s)",
        (name, place, star_rate, comment, recommendation)
    )
    connection.commit()
    cursor.close()
    connection.close()
    
    flash('Rating submitted successfully!', 'success')
    return redirect(url_for('destinations_index'))

@app.route('/destinations/churches')
def churches():
    return render_template('churches.html', churches=churches_data)

@app.route('/destinations/churches/<int:church_id>') 
def church_details(church_id):
    if church_id < 0 or church_id >= len(churches_data):
        return "Church not found", 404
    church = churches_data[church_id]
    # Fetch ratings for the church
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM ratings WHERE place = %s ORDER BY created_at DESC", (church['name'],))
    ratings = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('desplaces1.html', destination=church, ratings=ratings)

@app.route('/destinations/hotels')
def hotels():
    return render_template('hotels.html', hotels=hotels_data)

@app.route('/destinations/hotels/<int:hotel_id>') 
def hotel_details(hotel_id):
    if hotel_id < 0 or hotel_id >= len(hotels_data):
        return "Hotel not found", 404  
    hotel = hotels_data[hotel_id]
    # Fetch ratings for the hotel
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM ratings WHERE place = %s ORDER BY created_at DESC", (hotel['name'],))
    ratings = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('desplaces.html', destination=hotel, ratings=ratings)

@app.route('/destinations/foodgastronomy')
def foodgastronomy():
    return render_template('foodgastronomy.html', fdgstrmy=foodgastronomy_data)

@app.route('/destinations/foodgastronomy/<int:fdgstrmy_id>') 
def foodgastronomy_details(fdgstrmy_id):
    if fdgstrmy_id < 0 or fdgstrmy_id >= len(foodgastronomy_data):  
        return "Food Gastronomy not found", 404  
    foodgty = foodgastronomy_data[fdgstrmy_id]
    # Fetch ratings for the food item
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM ratings WHERE place = %s ORDER BY created_at DESC", (foodgty['name'],))
    ratings = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('desplaces1.html', destination=foodgty, ratings=ratings)

@app.route('/destinations/cultureheritages')
def cultureheritages():
    return render_template('cultureheritages.html', culher=cultureheritages_data)

@app.route('/destinations/cultureheritages/<int:culher_id>') 
def cultureheritages_details(culher_id):
    if culher_id < 0 or culher_id >= len(cultureheritages_data):  
        return "Culture Heritage not found", 404  
    culhrtages = cultureheritages_data[culher_id] 
    # Fetch ratings for the culture heritage
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM ratings WHERE place = %s ORDER BY created_at DESC", (culhrtages['name'],))
    ratings = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('desplaces1.html', destination=culhrtages, ratings=ratings)

@app.route('/destinations/others')
def others():
    return render_template('others.html', oths=others_data)

@app.route('/destinations/others/<int:other_id>') 
def other_details(other_id):
    if other_id < 0 or other_id >= len(others_data):
        return "Other not found", 404  
    other = others_data[other_id]
    # Fetch ratings for the other place
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM ratings WHERE place = %s ORDER BY created_at DESC", (other['name'],))
    ratings = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('desplaces.html', destination=other, ratings=ratings)

@app.route('/aboutus')
def aboutus():
    return render_template('aboutus.html')

@app.route('/contactus', methods=['GET', 'POST'])
def contactus():
    if 'adventurerID' not in session: 
        flash('You need to log in before accessing the contact form.', 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        message = request.form['message']

        connection = create_connection()
        cursor = connection.cursor()

        sql = """INSERT INTO information (name, email, phoneNumber, message) 
                 VALUES (%s, %s, %s, %s)"""
        values = (name, email, phone, message)

        try:
            cursor.execute(sql, values)
            connection.commit()  
            flash('Message sent successfully!', 'success')  
        except mysql.connector.Error as err:
            flash(f"An error occurred: {err}", 'error')  
        finally:
            cursor.close()
            connection.close()

        return redirect(url_for('home'))
    
    return render_template('contactus.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if 'signup' in request.form:  # Signup form submitted
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']

            # Hash the password
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

            # Database connection
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                try:
                    cursor.execute(
                        "INSERT INTO login (name, email, password) VALUES (%s, %s, %s)",
                        (name, email, hashed_password.decode('utf-8'))
                    )
                    connection.commit()
                    flash("User signed up successfully. You can now log in.", "success")
                except Error as e:
                    print(f"Error during signup: {e}")
                    flash("An error occurred during signup.", "error")
                finally:
                    cursor.close()
                    connection.close()
            return redirect(url_for('login'))

        elif 'signin' in request.form:  
            email = request.form['email']
            password = request.form['password']

            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                cursor.execute("SELECT * FROM login WHERE email = %s", (email,))
                user = cursor.fetchone()

                print(f"User retrieved: {user}")

                if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                    session['adventurerID'] = user['adventurerID']
                    session['name'] = user['name']
                    session['email'] = email

                    admin_emails = ['admin@gmail.com', 'casadesegunda@gmail.com', 'museodelipa@gmail.com']
                    if email in admin_emails:
                        flash(f"Welcome Admin, {user['name']}!", "success")
                        if email == 'casadesegunda@gmail.com':
                            return redirect(url_for('estabadm.dashboard'))
                        elif email == 'museodelipa@gmail.com':
                            return redirect(url_for('estab2adm.dashboard'))
                        return redirect(url_for('adm.dashboard'))
                    
                    flash(f"Welcome, {user['name']}!", "success")
                    return redirect(url_for('home'))
                else:
                    flash("Invalid credentials", "error")
                cursor.close()
                connection.close()
            else:
                flash("Failed to connect to the database.", "error")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()  
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))

@app.route('/profile')
def profile():
    if 'adventurerID' in session:
        adventurerID = session['adventurerID']
        connection = create_connection()  
        if connection is not None:
            cur = connection.cursor()

            cur.execute("SELECT gender, contact_number, address, age FROM userprofile WHERE adventurerID = %s", (adventurerID,))
            profile_data = cur.fetchone()

            cur.close()
            connection.close()

            gender = profile_data[0] if profile_data else None
            contact_number = profile_data[1] if profile_data else None
            address = profile_data[2] if profile_data else None
            age = profile_data[3] if profile_data else None

            return render_template('profile.html', name=session['name'], email=session['email'],
                                   gender=gender, contact_number=contact_number, address=address, age=age)
        else:
            flash('Could not connect to the database.', 'error')
            return redirect(url_for('login'))
    else:
        flash('Please log in to access your profile.', 'error')
        return redirect(url_for('login'))

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'adventurerID' in session:
        adventurerID = session['adventurerID']
        
        gender = request.form.get('gender', None)
        contact_number = request.form.get('contact_number', None)
        address = request.form.get('address', None)
        age = request.form.get('age', None)

        connection = create_connection()
        if connection is not None:
            cur = connection.cursor()

            cur.execute("""
                INSERT INTO userprofile (adventurerID, gender, contact_number, address, age)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE gender=%s, contact_number=%s, address=%s, age=%s
            """, (adventurerID, gender, contact_number, address, age, gender, contact_number, address, age))

            connection.commit()
            cur.close()
            connection.close()

            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Could not connect to the database.', 'error')
            return redirect(url_for('profile'))
    else:
        flash('Please log in to update your profile.', 'error')
        return redirect(url_for('login'))
    
app.register_blueprint(adm, url_prefix='/admin')
app.register_blueprint(estabadm, url_prefix='/estabadmin')
app.register_blueprint(estab2adm, url_prefix='/estab2admin')

if __name__ == '__main__':
    #app.run(debug=True)
    app.run(host="0.0.0.0", port=8093)
