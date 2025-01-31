'''MUSEO DE LIPA'''

from flask import Flask, render_template, Blueprint, request
from mysql.connector import Error
import mysql.connector

app = Flask(__name__)
app.secret_key = 'your_secret_key'

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

estab2adm = Blueprint('estab2adm', __name__, template_folder='estab2admin')

@estab2adm.route('/dashboard')
def dashboard():
    conn = create_connection()
    cursor = conn.cursor()

    user_profile_query = "SELECT userID, adventurerID, gender, contact_number, address, age FROM userprofile"
    cursor.execute(user_profile_query)
    user_profiles = cursor.fetchall()

    # Count residents and visitors by address
    address_data = {'residents': 0, 'visitors': 0}
    for _, _, _, _, address, _ in user_profiles:
        if 'lipa' in address.lower():  
            address_data['residents'] += 1
        else:
            address_data['visitors'] += 1

    # Fetch gender data
    gender_query = """
    SELECT LOWER(gender) as gender, COUNT(*) 
    FROM userprofile 
    GROUP BY gender
    """
    cursor.execute(gender_query)
    gender_counts = cursor.fetchall()

    gender_data = {'male': 0, 'female': 0, 'others': 0, 'prefer not': 0}
    for gender, count in gender_counts:
        if gender in gender_data:
            gender_data[gender] = count
        else:
            gender_data['others'] += count

    # Fetch monthly visitor data
    feedback_query = """
        SELECT MONTH(created_at) AS month, COUNT(DISTINCT name) AS visitor_count
        FROM ratings
        WHERE place = 'Museo ng Lipa'
        GROUP BY month
        ORDER BY month;
    """
    cursor.execute(feedback_query)
    feedbacks = cursor.fetchall()

    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    monthly_visitors = [0] * 12  

    for feedback in feedbacks:
        month_index = feedback[0] - 1
        visitor_count = feedback[1]
        monthly_visitors[month_index] = visitor_count

    # Fetch total recommendations and comments
    recommendation_query = """
    SELECT COUNT(recommendation)
    FROM ratings
    WHERE recommendation IS NOT NULL
      AND recommendation != ''
      AND place = 'Museo ng Lipa'
    """
    cursor.execute(recommendation_query)
    total_recommendations = cursor.fetchone()[0]
  
    comment_query = """
    SELECT COUNT(comment)
    FROM ratings
    WHERE comment IS NOT NULL
      AND comment != ''
      AND place = 'Museo ng Lipa'
    """
    cursor.execute(comment_query)
    total_comments = cursor.fetchone()[0]

    # Fetch total logins
    login_query = "SELECT COUNT(*) FROM login"
    cursor.execute(login_query)
    total_logins = cursor.fetchone()[0]

    # Fetch star rating counts
    star_counts = {}
    for i in range(1, 6):
        cursor.execute(f"SELECT COUNT(*) FROM ratings WHERE star_rate = {i} AND place = 'Museo ng Lipa'")
        star_counts[f"{i}_star"] = cursor.fetchone()[0]

    # Fetch visit data for "Museo ng Lipa"
    place_query = """
    SELECT place, COUNT(*) as visit_count
    FROM ratings
    WHERE place = 'Museo ng Lipa'
    GROUP BY place;
    """
    cursor.execute(place_query)
    places = cursor.fetchall()

    rating_query = """
    SELECT place, 
           SUM(CASE WHEN star_rate = 1 THEN 1 ELSE 0 END) AS one_star,
           SUM(CASE WHEN star_rate = 2 THEN 1 ELSE 0 END) AS two_star,
           SUM(CASE WHEN star_rate = 3 THEN 1 ELSE 0 END) AS three_star,
           SUM(CASE WHEN star_rate = 4 THEN 1 ELSE 0 END) AS four_star,
           SUM(CASE WHEN star_rate = 5 THEN 1 ELSE 0 END) AS five_star
    FROM ratings
    WHERE place = 'Museo ng Lipa'
    GROUP BY place
    """
    cursor.execute(rating_query)
    ratings_per_place = cursor.fetchall()

    cursor.close()  

    place_names = ['Museo ng Lipa']  
    visit_counts = [places[0][1]]  

    conn.close() 

    return render_template(
        'museodashboard.html', 
        title='Dashboard', 
        user_profiles=user_profiles,
        total_recommendations=total_recommendations,
        total_comments=total_comments,
        total_logins=total_logins,
        star_counts=star_counts,
        place_names=place_names,
        visit_counts=visit_counts,
        gender_data=gender_data,
        address_data=address_data,
        monthly_visitors=monthly_visitors,
        ratings_per_place=ratings_per_place
    )
    '''reviews=reviews'''
    
@estab2adm.route('/feedback', methods=['GET'])
def feedback():
    conn = create_connection()  
    cursor = conn.cursor()
    
    selected_month = request.args.get('month', None)

    if selected_month:
        query = """
            SELECT id, name, created_at, place, comment, recommendation 
            FROM ratings 
            WHERE MONTH(created_at) = %s AND place = 'Museo ng Lipa'
        """
        cursor.execute(query, (selected_month,))
    else:
        query = """
            SELECT id, name, created_at, place, comment, recommendation 
            FROM ratings 
            WHERE place = 'Museo ng Lipa'
        """
        cursor.execute(query)

    feedbacks = cursor.fetchall()

    cursor.close()
    conn.close()
    
    return render_template('museofeedback.html', title='Feedback', feedbacks=feedbacks, selected_month=selected_month)

@estab2adm.route('/review', methods=['GET'])
def review():
    conn = create_connection()
    cursor = conn.cursor()

    star_filter = request.args.get('star_filter', type=int)

    query = "SELECT id, name, created_at, place, star_rate FROM ratings WHERE place = %s"
    params = ['Museo ng Lipa']

    if star_filter:
        query += " AND star_rate = %s"
        params.append(star_filter)

    cursor.execute(query, tuple(params))
    reviews = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('museoreview.html', title='Review', reviews=reviews, star_filter=star_filter)

@estab2adm.route('/reports')
def reports():
    conn = create_connection()
    cursor = conn.cursor()

    try:
        # Rating Data
        rating_query = """
        SELECT place, 
               SUM(CASE WHEN star_rate = 1 THEN 1 ELSE 0 END) AS one_star,
               SUM(CASE WHEN star_rate = 2 THEN 1 ELSE 0 END) AS two_star,
               SUM(CASE WHEN star_rate = 3 THEN 1 ELSE 0 END) AS three_star,
               SUM(CASE WHEN star_rate = 4 THEN 1 ELSE 0 END) AS four_star,
               SUM(CASE WHEN star_rate = 5 THEN 1 ELSE 0 END) AS five_star
        FROM ratings
        WHERE place = 'Museo ng Lipa'
        GROUP BY place
        """
        cursor.execute(rating_query)
        ratings_per_place = cursor.fetchall()

        # User Profile Data
        user_profile_query = "SELECT userID, adventurerID, gender, contact_number, address, age FROM userprofile"
        cursor.execute(user_profile_query)
        user_profiles = cursor.fetchall()

        address_data = {'residents': 0, 'visitors': 0}
        for _, _, _, _, address, _ in user_profiles:
            if 'lipa' in address.lower():  
                address_data['residents'] += 1
            else:
                address_data['visitors'] += 1

        # Gender Data
        gender_query = """
        SELECT LOWER(gender) as gender, COUNT(*) 
        FROM userprofile 
        GROUP BY gender
        """
        cursor.execute(gender_query)
        gender_counts = cursor.fetchall()

        gender_data = {'male': 0, 'female': 0, 'others': 0, 'prefer not': 0}
        for gender, count in gender_counts:
            if gender in gender_data:
                gender_data[gender] = count
            else:
                gender_data['others'] += count

        # Monthly Visitors Data
        feedback_query = """
        SELECT MONTH(created_at) AS month, COUNT(name) AS visitor_count
        FROM ratings
        WHERE place = 'Museo ng Lipa'
        GROUP BY month
        ORDER BY month;
        """
        cursor.execute(feedback_query)
        feedbacks = cursor.fetchall()

        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        monthly_visitors = [0] * 12  

        for feedback in feedbacks:
            month_index = feedback[0] - 1
            visitor_count = feedback[1]
            monthly_visitors[month_index] = visitor_count

        # Star Counts Data
        star_counts = {}
        for i in range(1, 6):
            cursor.execute(f"SELECT COUNT(*) FROM ratings WHERE star_rate = {i} AND place = 'Museo ng Lipa'")
            star_counts[f"{i}_star"] = cursor.fetchone()[0]

        # Place Data
        place_query = """
        SELECT place, COUNT(*) as visit_count
        FROM ratings
        WHERE place = 'Museo ng Lipa'
        GROUP BY place
        ORDER BY visit_count DESC
        LIMIT 1;
        """
        cursor.execute(place_query)
        places = cursor.fetchall()

        place_names = [place[0] for place in places]
        visit_counts = [place[1] for place in places]

    finally:
        cursor.close()
        conn.close()

    return render_template(
        'museoreports.html', 
        title='Reports', 
        ratings_per_place=ratings_per_place,
        user_profiles=user_profiles,
        gender_data=gender_data,
        monthly_visitors=monthly_visitors,
        address_data=address_data,
        visit_counts=visit_counts,
        place_names=place_names,
        star_counts=star_counts
    )
    
@estab2adm.route('/attractions')
def attractions():
    connection = create_connection()

    sort_order = request.args.get('sort', 'desc')  
    print(f"Sort order: {sort_order}")

    order_by = 'ASC' if sort_order == 'asc' else 'DESC'
    
    query = f"""
    SELECT MIN(id) AS id, place, AVG(star_rate) AS average_rating
    FROM ratings
    GROUP BY place
    ORDER BY AVG(star_rate) {order_by};
    """
    
    cursor = connection.cursor(dictionary=True)
    cursor.execute(query)
    attractions_data = cursor.fetchall()
    
    cursor.close()
    connection.close()

    for index, attraction in enumerate(attractions_data):
        attraction['ranking'] = index + 1
        
        if attraction['place'] == 'museo ng lipa' or attraction['place'] == 'Museo ng Lipa':
            attraction['place'] = 'Museo ng Lipa'
        else:
            attraction['place'] = f'Attraction Place {index + 1}'
    
    return render_template('museoattractions.html', title='Attractions', attractions=attractions_data)